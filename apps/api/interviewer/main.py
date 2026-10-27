from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import time
import jwt as jwt_lib
from contextvars import ContextVar
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .providers import PROVIDERS, BASE_URLS, ProviderConfig, ProviderFailure, Providers, Settings
from .sessions import Action, Answer, CreateSession, Mutation, ROOT, Sessions, records, role_record, scenario_record, repeatable_question, dialogue_request_kind, turns_with_delivery, conversation_progress, session_coding, session_reference
from .store import Conflict, Store, encode, uid
from .assessment import statement_observation, reviewed_observations, criterion_coverage
from . import responses as public
from .body_limit import BodyLimit
from .resume import experience_claims
from . import practice_review
from .dialogue_memory import POLICY_VERSION, Coverage, current_memory, memory_context, memory_input, memory_messages, transcript_signature, validate_coverage

load_dotenv(ROOT / ".env")
DATA = Path(os.getenv("FIELDNOTE_DATA", str(ROOT / "data")))
store = Store(DATA / "interviews.sqlite3")
sessions = Sessions(store)
providers = Providers()
generations: dict[str, asyncio.Task] = {}
memory_tasks: dict[str, asyncio.Task] = {}
subscribers: dict[str, set[asyncio.Queue]] = {}
session_owners: dict[str, str] = {}
runner_tasks: dict[str, asyncio.Task] = {}
voice = None
resume_parser_slots = asyncio.Semaphore(1)


async def parse_pdf(raw):
    try:
        await asyncio.wait_for(resume_parser_slots.acquire(), 1)
    except asyncio.TimeoutError as exc:
        raise HTTPException(503, "Another resume is being parsed. Retry shortly or paste text.") from exc
    process = None
    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable, str(Path(__file__).with_name("extract.py")), stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        try:
            out, _ = await asyncio.wait_for(process.communicate(raw), 10)
        except asyncio.TimeoutError as exc:
            raise ValueError("PDF parsing exceeded 10 seconds. Paste text instead.") from exc
        try:
            result = json.loads(out)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("PDF parser failed. Export a new text PDF or paste text.") from exc
        if result.get("error"):
            raise ValueError(result["error"])
        return result["pages"]
    finally:
        if process is not None and process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            await process.wait()
        resume_parser_slots.release()


LEGACY_OWNER = "local-owner"
_active_owner: ContextVar[str] = ContextVar("fieldnote_owner", default=LEGACY_OWNER)
def owner():
    return _active_owner.get()


def owner_for(sid):
    return session_owners.get(sid, owner())

AUTH_URL = os.getenv("FIELDNOTE_AUTH_URL", "http://127.0.0.1:8001").rstrip("/")
AUTH_ORIGIN = os.getenv("FIELDNOTE_ORIGIN", "http://localhost:5173")
auth_http = httpx.AsyncClient(timeout=15)
_jwks = None
_jwks_expires = 0.0
_jwks_lock = asyncio.Lock()
_legacy_claimed = False


async def auth_keys():
    global _jwks, _jwks_expires
    if _jwks is not None and time.monotonic() < _jwks_expires:
        return _jwks
    async with _jwks_lock:
        if _jwks is not None and time.monotonic() < _jwks_expires:
            return _jwks
        try:
            response = await auth_http.get(f"{AUTH_URL}/api/auth/jwks")
            response.raise_for_status()
            _jwks = jwt_lib.PyJWKSet.from_dict(response.json())
            _jwks_expires = time.monotonic() + 300
            return _jwks
        except (httpx.HTTPError, ValueError, jwt_lib.PyJWTError):
            _jwks = None
            raise HTTPException(503, "Account service is unavailable. Retry shortly.") from None


async def verify_owner(request: Request):
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token or len(token) > 8192:
        raise HTTPException(401, "Sign in to continue.")
    try:
        header = jwt_lib.get_unverified_header(token)
        if header.get("alg") != "EdDSA" or not isinstance(header.get("kid"), str):
            raise jwt_lib.InvalidTokenError("Unexpected signing key")
        keys = await auth_keys()
        key = next(key for key in keys.keys if key.key_id == header["kid"] and key.algorithm_name == "EdDSA")
        claims = jwt_lib.decode(token, key.key, algorithms=["EdDSA"], issuer=AUTH_ORIGIN,
                                audience=AUTH_ORIGIN, options={"require": ["exp", "iat", "sub", "iss", "aud"]})
        if not isinstance(claims.get("sub"), str) or not claims["sub"]:
            raise jwt_lib.InvalidTokenError("Missing account id")
        return claims["sub"]
    except StopIteration:
        raise HTTPException(401, "Sign in again to continue.") from None
    except jwt_lib.PyJWTError:
        raise HTTPException(401, "Sign in again to continue.") from None


def claim_legacy_data(account_id):
    global _legacy_claimed
    if _legacy_claimed:
        return
    with store.transaction() as db:
        db.execute("CREATE TABLE IF NOT EXISTS legacy_owner_claim(id INTEGER PRIMARY KEY CHECK(id=1), owner TEXT NOT NULL)")
        row = db.execute("SELECT owner FROM legacy_owner_claim WHERE id=1").fetchone()
        if row is None:
            db.execute("INSERT INTO legacy_owner_claim VALUES(1,?)", (account_id,))
            db.execute("UPDATE sessions SET owner=? WHERE owner=?", (account_id, LEGACY_OWNER))
            db.execute("UPDATE resumes SET owner=? WHERE owner=?", (account_id, LEGACY_OWNER))
    _legacy_claimed = True


async def cancel_generation(sid, *, interrupt_voice=True):
    memory_task = memory_tasks.pop(sid, None)
    if memory_task:
        memory_task.cancel()
        await asyncio.gather(memory_task, return_exceptions=True)
    task = generations.pop(sid, None)
    if task and task is not asyncio.current_task():
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    if voice and interrupt_voice:
        await voice.interrupt(sid)


async def pause_disconnected_session(sid, account_id):
    """Disconnect invalidates the authoritative generation even after text finished."""
    with store.transaction() as db:
        try:
            session = store.get(sid, account_id, db)
        except KeyError:
            return
        if session["stage"] == "COMPLETED" or session["paused"]:
            return
        session["paused"] = True
        session["generation_id"] = uid()
        session["revision"] += 1
        for turn in session["turns"]:
            if turn.get("delivery") == "generating":
                turn["delivery"] = "interrupted"
        store.event(db, session, "disconnect", {"reason": "Connection closed. Resume explicitly; buffered audio is invalid."})
        store.save(db, session, account_id)
    await cancel_generation(sid)


async def notify(sid, event):
    try:
        event = public.StreamEvent.model_validate(event).model_dump(exclude_unset=True)
    except ValidationError:
        raise RuntimeError("Application notification could not be validated") from None
    if event["session_id"] != sid:
        raise RuntimeError("Application notification belongs to another session")
    if voice and voice.is_connected(sid) and event.get("type") in {"state", "complete", "resync", "execution", "voice_error"}:
        try:
            await voice.send_event(sid, event)
        except (RuntimeError, OSError, KeyError):
            # Persisted state and SSE remain available if the audio transport fails.
            pass
    for queue in tuple(subscribers.get(sid, set())):
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            # A slow client must reload persisted state instead of growing memory.
            subscribers[sid].discard(queue)
            while not queue.empty():
                queue.get_nowait()
            queue.put_nowait({"type": "resync", "session_id": sid})


async def record_voice_event(sid, kind, payload):
    """Append unscored delivery diagnostics without changing action revisions."""
    if kind != "voice_delivery" or payload.get("status") not in {"buffering", "playing", "estimated_complete", "interrupted", "closed", "unavailable"}:
        return
    try:
        with store.transaction() as db:
            state = store.get(sid, owner_for(sid), db)
            gid = payload.get("generation_id")
            turn = next((t for t in state["turns"] if t["role"] == "assistant" and t.get("generation_id") == gid), None)
            if not turn:
                return
            if gid != state["generation_id"] and payload["status"] in {"buffering", "playing", "estimated_complete"}:
                return
            clean = {k: payload[k] for k in ("generation_id", "status", "delivery_note")}
            for key in ("generated_text_chars", "displayed_text_chars", "generated_audio_ms", "estimated_played_ms", "peak_pending_audio_ms"):
                value = payload.get(key)
                if type(value) not in {int, float} or not 0 <= value < 2**53:
                    return
                clean[key] = value
            clean["generated_text_chars"] = min(int(clean["generated_text_chars"]), len(turn["text"]))
            clean["displayed_text_chars"] = min(int(clean["displayed_text_chars"]), clean["generated_text_chars"])
            clean["estimated_played_ms"] = min(clean["estimated_played_ms"], clean["generated_audio_ms"])
            allowed = {"first_tts_clause_server", "first_tts_chunk_server", "first_audio_admitted_server",
                       "first_text_received_client_ms", "first_text_displayed_client_ms", "first_playback_client_ms",
                       "first_text_received_receipt_server", "first_text_displayed_receipt_server", "first_playback_receipt_server"}
            clean["timing"] = {k: v for k, v in payload.get("timing", {}).items() if k in allowed
                               and type(v) in {int, float} and 0 < v < 2**53}
            clean["turn_id"] = turn["id"]
            store.event(db, state, "voice_delivery", clean)
    except KeyError:
        # Deleted/expired sessions cannot be recreated by late audio callbacks.
        return


async def cleanup_loop():
    while True:
        await cleanup_pass()
        await asyncio.sleep(60)


async def cleanup_pass():
    store.expire()
    with store.connect() as db:
        retired = [row[0] for row in db.execute("SELECT id FROM tombstones")]
        saved_jobs = {row[0] for row in db.execute("SELECT id FROM submissions")}
    orphaned = [runner_tasks.pop(job_id) for job_id in tuple(runner_tasks) if job_id not in saved_jobs]
    for task in orphaned:
        task.cancel()
    if orphaned:
        await asyncio.gather(*orphaned, return_exceptions=True)
    for sid in retired:
        await cleanup_local_session(sid)
    await cleanup_runner_records()


async def cleanup_local_session(sid):
    await cancel_generation(sid, interrupt_voice=False)
    if voice:
        try:
            await voice.close(sid)
        except Exception:
            # The tombstone remains durable and the next pass retries closure.
            # Never let one failed connection stop retention for other sessions.
            return False
    session_owners.pop(sid, None)
    return remove_session_files(sid)


def remove_session_files(sid):
    if not isinstance(sid, str) or not re.fullmatch(r"[a-f0-9]{32}", sid):
        return False
    try:
        root = (DATA / "sessions").resolve()
        candidate = root / sid
        target = candidate.resolve()
        if target != candidate or target.parent != root:
            return False
        if target.exists():
            shutil.rmtree(target)
        return True
    except (OSError, RuntimeError):
        return False


async def cleanup_runner_records():
    with store.connect() as db:
        rows = db.execute("SELECT job_id FROM runner_cleanup").fetchall()
    for row in rows:
        job_id = row[0]
        task = runner_tasks.pop(job_id, None)
        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        if not os.getenv("RUNNER_URL") or not os.getenv("RUNNER_BEARER_TOKEN"):
            continue
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.delete(os.environ["RUNNER_URL"].rstrip("/")+"/jobs/"+job_id, headers={"Authorization": "Bearer "+os.environ["RUNNER_BEARER_TOKEN"]})
            if response.is_success or response.status_code == 404:
                with store.transaction() as db:
                    db.execute("DELETE FROM runner_cleanup WHERE job_id=?", (job_id,))
        except httpx.HTTPError:
            pass


@asynccontextmanager
async def lifespan(app):
    global voice
    store.recover()
    try:
        from .voice import VoiceManager
        voice = VoiceManager(model_dir=Path(os.getenv("VOICE_MODEL_DIR", str(DATA / "models"))), data_dir=DATA, on_event=record_voice_event)
    except (ImportError, RuntimeError):
        voice = None
    # Load shared speech models before the first interview, without delaying HTTP startup.
    speech_warmup = asyncio.create_task(voice.warmup()) if voice else None
    await cleanup_pass()
    cleaner = asyncio.create_task(cleanup_loop())
    yield
    cleaner.cancel()
    await asyncio.gather(cleaner, return_exceptions=True)
    for sid in set(generations) | set(memory_tasks):
        await cancel_generation(sid)
    if voice:
        await voice.close_all()
    if speech_warmup:
        await asyncio.gather(speech_warmup, return_exceptions=True)
    for task in runner_tasks.values():
        task.cancel()
    await asyncio.gather(*runner_tasks.values(), return_exceptions=True)
    await providers.client.aclose()
    await auth_http.aclose()


app = FastAPI(title="Fieldnote interview API", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(BodyLimit)


@app.middleware("http")
async def security(request: Request, call_next):
    path = request.url.path
    response = None
    configured_origin = os.getenv("FIELDNOTE_ORIGIN", "http://localhost:5173")
    try:
        configured_host = urlsplit(configured_origin).hostname
        host = request.url.hostname
    except ValueError:
        host = configured_host = None
    if not host or host not in {"localhost", "127.0.0.1", "::1", configured_host}:
        response = JSONResponse(public.Error(detail="Host rejected").model_dump(exclude_unset=True), status_code=400)
    if response is None and path.startswith("/api"):
        try:
            length = int(request.headers.get("content-length", "0"))
            if length < 0:
                raise ValueError()
        except ValueError:
            response = JSONResponse(public.Error(detail="Invalid Content-Length").model_dump(exclude_unset=True), status_code=400)
        else:
            if length > 11*1024*1024:
                response = JSONResponse(public.Error(detail="Request exceeds upload limit").model_dump(exclude_unset=True), status_code=413)
        if response is None and request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            expected = configured_origin
            if origin and origin != expected:
                response = JSONResponse(public.Error(detail="Origin rejected").model_dump(exclude_unset=True), status_code=403)
        if response is None and not (path == "/api/health" or path == "/api/auth" or path.startswith("/api/auth/")):
            try:
                account_id = await verify_owner(request)
                claim_legacy_data(account_id)
                context_token = _active_owner.set(account_id)
                request.state.owner_id = account_id
            except HTTPException as exc:
                response = JSONResponse(public.Error(detail=exc.detail).model_dump(exclude_unset=True), status_code=exc.status_code)
    else:
        context_token = None
    if response is None:
        try:
            response = await call_next(request)
        finally:
            if 'context_token' in locals() and context_token is not None:
                _active_owner.reset(context_token)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store" if path.startswith("/api") else "no-cache"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(self)"
    return response


@app.api_route("/api/auth", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
@app.api_route("/api/auth/{auth_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def better_auth_proxy(request: Request, auth_path: str = "") -> Any:
    suffix = f"/{auth_path}" if auth_path else ""
    target = f"{AUTH_URL}/api/auth{suffix}"
    if request.url.query:
        target += f"?{request.url.query}"
    headers = {key: value for key, value in request.headers.items()
               if key.lower() in {"accept", "content-type", "cookie", "origin", "referer", "user-agent", "authorization"}}
    try:
        upstream = await auth_http.request(request.method, target, content=await request.body(), headers=headers)
    except httpx.HTTPError:
        raise HTTPException(503, "Account service is unavailable. Retry shortly.") from None
    response = Response(upstream.content, status_code=upstream.status_code)
    copied = {key.lower() for key, _ in upstream.headers.multi_items()
              if key.lower() in {"content-type", "set-cookie", "location", "www-authenticate"}}
    response.raw_headers = [(key, value) for key, value in response.raw_headers if key.decode().lower() not in copied]
    for key, value in upstream.headers.multi_items():
        if key.lower() in copied:
            response.raw_headers.append((key.lower().encode(), value.encode()))
    return response


@app.exception_handler(Conflict)
async def conflict_handler(request, exc):
    return JSONResponse(public.Error(detail=str(exc)).model_dump(exclude_unset=True), status_code=409)


@app.exception_handler(KeyError)
async def missing_handler(request, exc):
    return JSONResponse(public.Error(detail="Record not found").model_dump(exclude_unset=True), status_code=404)


@app.exception_handler(ValueError)
async def value_handler(request, exc):
    return JSONResponse(public.Error(detail=str(exc)).model_dump(exclude_unset=True), status_code=422)


@app.exception_handler(ProviderFailure)
async def provider_handler(request, exc):
    return JSONResponse(public.Error(detail=exc.message, error=exc.public()).model_dump(exclude_unset=True), status_code=503)


@app.exception_handler(RequestValidationError)
async def invalid_request_handler(request, exc):
    # Default validation diagnostics echo input values, including pasted context
    # or a credential accidentally entered in the wrong field.
    issues = [{"loc": list(issue["loc"]), "msg": issue["msg"], "type": issue["type"]} for issue in exc.errors()]
    return JSONResponse(public.Error(detail=issues).model_dump(exclude_unset=True), status_code=422)


@app.exception_handler(ResponseValidationError)
async def invalid_response_handler(request, exc):
    # Validation diagnostics can contain the complete stored/provider value.
    # Never echo or log them as part of a public error response.
    return JSONResponse(public.Error(detail="Response could not be validated. No unvalidated data was returned.").model_dump(exclude_unset=True), status_code=500)


@app.get("/api/health", response_model=public.Health, response_model_exclude_unset=True)
async def health():
    return {"status": "ok"}


@app.get("/api/readiness", response_model=public.Readiness, response_model_exclude_unset=True)
async def readiness():
    ready = voice.readiness() if voice else {"ready": False, "detail": "Local speech runtime or models are not provisioned. Typed interviews remain available."}
    if asyncio.iscoroutine(ready):
        ready = await ready
    return {"voice": ready, "providers": {p: {"status": "configured" if providers.key(p) else "missing", "validated": p in providers.validations} for p in PROVIDERS}, "runner": {"configured": bool(os.getenv("RUNNER_URL") and os.getenv("RUNNER_BEARER_TOKEN"))}, "assessment": {"automatic_ratings": False, "reason": "Independent human calibration unavailable; factual reference review only."}}


@app.get("/api/roles", response_model=public.Roles, response_model_exclude_unset=True)
async def roles():
    return {"roles": records("roles")}


@app.post("/api/voice/warmup", response_model=public.VoiceReadiness, response_model_exclude_unset=True)
async def warm_voice():
    if voice is None:
        return {"ready": False, "status": "unavailable", "detail": "Local speech runtime is not provisioned. Continue by typing."}
    return await voice.warmup()


@app.get("/api/settings", response_model=public.Settings, response_model_exclude_unset=True)
async def settings_get():
    return store.settings()


@app.patch("/api/settings", response_model=public.Settings, response_model_exclude_unset=True)
async def settings_patch(body: Settings):
    if not {"groq", "openrouter"}.issubset(body.providers) or not set(body.providers).issubset(PROVIDERS):
        raise ValueError("Keep separate settings for Groq, OpenRouter, and Codex")
    data = body.model_dump()
    data["providers"].setdefault("codex", store.settings()["providers"]["codex"])
    # A saved missing credential/model is permitted; starting still requires preflight.
    for provider, config in data["providers"].items():
        if config["live_model"] and providers.key(provider):
            await providers.catalog(provider)
            available = providers.catalogs[provider][1]
            if any(config[k] and config[k] not in available for k in ("live_model", "assessment_model")):
                raise ValueError("Selected model is not available in the provider catalog")
    with store.transaction() as db:
        current = json.loads(db.execute("SELECT body FROM settings WHERE id=1").fetchone()[0])
        if data["revision"] != current["revision"]:
            raise Conflict("Settings changed. Reload before saving.")
        data["revision"] += 1
        db.execute("UPDATE settings SET body=? WHERE id=1", (encode(data),))
    providers.validations.clear()
    return data


@app.get("/api/providers/{provider}/models", response_model=public.Catalog, response_model_exclude_unset=True)
async def models(provider: str):
    if provider not in PROVIDERS:
        raise HTTPException(404)
    return await providers.catalog(provider)


@app.get("/api/providers/openrouter/models/{model:path}/endpoints", response_model=public.Endpoints, response_model_exclude_unset=True)
async def endpoints(model: str):
    return await providers.endpoints(model)


@app.post("/api/providers/{provider}/test", response_model=public.ProviderTest, response_model_exclude_unset=True)
async def test_provider(provider: str, body: ProviderConfig):
    if provider not in PROVIDERS:
        raise HTTPException(404)
    config = await providers.validate(provider, body.model_dump())
    snapshot = {"provider": provider, "config": config}
    output = ""
    async for chunk in providers.stream(snapshot, [{"role": "user", "content": "Synthetic connection test. Reply with the single word Ready."}]):
        output += chunk["text"]
    schema = {"type": "object", "properties": {"ready": {"type": "boolean"}}, "required": ["ready"], "additionalProperties": False}
    result = await providers.structured(snapshot, [{"role": "user", "content": "Synthetic schema test. Return ready true."}], schema)
    if result != {"ready": True} or not output.strip():
        raise ProviderFailure("malformed_output", "Provider connection test did not return valid live and structured outputs")
    providers.validations[provider] = {"config": config, "validated_at": time.time()}
    return {"status": "validated", "provider": provider, "validated_at": time.time(), "live": True, "structured_assessment": True}


def redact(text):
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email removed]", text)
    text = re.sub(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)", "[phone removed]", text)
    return "\n".join(line for line in text.splitlines() if not re.match(r"\s*(address|date of birth|dob|nationality|marital status)\s*:", line, re.I))


@app.post("/api/resumes", response_model=public.Resume, response_model_exclude_unset=True)
async def upload_resume(request: Request):
    ctype = request.headers.get("content-type", "")
    if "application/json" in ctype:
        value = await request.json()
        if not isinstance(value, dict):
            raise ValueError("Paste resume text as a JSON object with a text field")
        text = value.get("text", "")
        if not isinstance(text, str) or not 0 < len(text) <= 50000:
            raise ValueError("Paste between 1 and 50,000 characters")
        pages = [{"page": None, "text": text}]
    else:
        form = await request.form(max_files=1, max_fields=2, max_part_size=10*1024*1024)
        file = form.get("file")
        if not file or not hasattr(file, "read"):
            raise ValueError("Choose a text PDF or plain text resume")
        raw = await file.read(10*1024*1024+1)
        if len(raw) > 10*1024*1024:
            raise HTTPException(413, "Resume exceeds 10 MiB")
        name = (file.filename or "").lower()
        if name.endswith(".txt"):
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise ValueError("Save plain text as UTF-8 or paste it") from exc
            pages = [{"page": None, "text": text}]
        elif name.endswith(".pdf") and raw.startswith(b"%PDF-"):
            pages = await parse_pdf(raw)
        else:
            raise ValueError("Unsupported resume. Use a text-based PDF, UTF-8 .txt, or pasted text.")
    text = "\n".join(p["text"] for p in pages)
    if not text.strip() or len(text) > 50000:
        raise ValueError("Resume needs readable text within 50,000 characters")
    claims = experience_claims(pages, redact)
    result = {"id": uid(), "text": text, "context": redact(text), "pages": pages, "claims": claims[:50], "redaction_note": "Common email, phone and labeled personal details removed from proposed context. Review manually; redaction is not comprehensive anonymization.", "created": time.time()}
    with store.transaction() as db:
        db.execute("INSERT INTO resumes VALUES(?,?,?,?)", (result["id"], owner(), encode(result), result["created"]))
    return result


@app.delete("/api/resumes/{rid}", response_model=public.RemovedResume, response_model_exclude_unset=True)
async def delete_resume(rid: str):
    with store.transaction() as db:
        if not db.execute("DELETE FROM resumes WHERE id=? AND owner=?", (rid, owner())).rowcount:
            raise HTTPException(404)
    return {"deleted": True}

async def generate(sid, *, repeated_text=None):
    s = store.get(sid, owner())
    gid = s["generation_id"]
    assistant_id = uid()
    started = time.monotonic()
    request_started_at = time.time()
    opening = bool(s.get("_opening_version") and not any(t["role"] == "user" or t.get("delivery") == "complete" for t in s["turns"]))
    local_opening = opening and s["snapshot"]["provider"] == "codex" and repeated_text is None
    with store.transaction() as db:
        current = store.get(sid, owner(), db)
        if current["generation_id"] != gid or current["paused"]:
            return
        current["turns"].append({"id": assistant_id, "role": "assistant", "text": "", "version": 1, "stage": current["stage"], "delivery": "generating", "created": time.time(), "generation_id": gid,
            "interview_opening": opening,
            "timing": {"clock": "server_unix_seconds", "request_started": request_started_at,
                       "request_kind": "local_repeat" if repeated_text is not None else "local_opening" if local_opening else "cloud"}})
        store.save(db, current, owner_for(sid))
    await notify(sid, {"type": "state", "state": "processing", "session_id": sid, "turn_id": assistant_id, "generation_id": gid})
    final = "complete"
    failure = None
    usage = None
    route = None
    text = ""
    first_content = None
    first_content_at = None
    try:
        async def content():
            if repeated_text is not None:
                yield {"text": repeated_text, "usage": None, "route": "local-repeat"}
            elif local_opening:
                yield {"text": "Hi, welcome to your practice interview. Could you tell me a little about yourself and the work you’d like to focus on?", "usage": None, "route": "local-opening"}
            else:
                async for item in providers.stream(s["snapshot"], sessions.prompt(s)):
                    yield item
        async for chunk in content():
            delta = chunk["text"]
            text += delta
            if first_content is None and delta:
                first_content = time.monotonic()-started
                first_content_at = time.time()
            usage = chunk.get("usage") or usage
            route = chunk.get("route") or route
            if not delta:
                continue
            # A Windows-mounted SQLite commit can take tens of milliseconds.
            # Keep it durable-before-publish without blocking voice processing,
            # browser receipt acknowledgments or cancellation on the event loop.
            accepted = await asyncio.to_thread(sessions.update_generation_text,
                sid, owner(), gid, assistant_id, text)
            if not accepted:
                final = "interrupted"
                break
            await notify(sid, {"type": "delta", "text": delta, "text_so_far": text, "session_id": sid, "turn_id": assistant_id, "generation_id": gid})
            if voice and voice.is_connected(sid):
                try:
                    await voice.send_text(sid, text, gid)
                except (RuntimeError, OSError):
                    await notify(sid, {"type": "voice_error", "session_id": sid, "generation_id": gid, "message": "Speech playback unavailable. Continue using the displayed text."})
        if final == "complete" and voice and voice.is_connected(sid):
            await voice.finish_text(sid, gid)
    except asyncio.CancelledError:
        final = "interrupted"
    except ProviderFailure as exc:
        final = "incomplete"
        failure = exc.public()
    except KeyError:
        return
    finally:
        try:
            with store.transaction() as db:
                current = store.get(sid, owner(), db)
                turn = next((t for t in current["turns"] if t["id"] == assistant_id), None)
                if turn:
                    turn["delivery"] = final
                    turn["timing"]["first_usable_content"] = first_content_at
                if current["generation_id"] == gid:
                    current["last_error"] = failure
                    if failure:
                        current["revision"] += 1
                        current["paused"] = True
                        current["generation_id"] = uid()
                        store.event(db, current, "provider_paused", {"code": failure["code"], "interrupted_generation_id": gid})
                store.event(db, current, "generation_finished", {"generation_id": gid, "turn_id": assistant_id, "delivery": final, "provider": s["snapshot"]["provider"], "model": s["snapshot"]["config"]["live_model"], "route": route, "usage": usage, "first_content_seconds": first_content, "request_seconds": time.monotonic()-started})
                store.save(db, current, owner_for(sid))
            if failure and voice and voice.is_connected(sid):
                await voice.interrupt(sid)
            await notify(sid, {"type": "error" if failure else "complete", "error": failure, "session_id": sid, "turn_id": assistant_id, "generation_id": gid, "revision": current["revision"]})
            if final == "complete" and not failure and repeated_text is None:
                schedule_dialogue_memory(sid)
        except KeyError:
            pass


async def refresh_dialogue_memory(sid, captured, inputs, answer_count):
    started = time.monotonic()
    signature = transcript_signature(captured["turns"])
    status = "available"
    coverage = None
    try:
        value = await providers.structured(captured["snapshot"], memory_messages(inputs), Coverage.model_json_schema())
        coverage = validate_coverage(value, inputs)
    except (ProviderFailure, ValueError):
        # Memory is optional; unavailable/invalid output cannot pause live
        # dialogue or become a finding. Exact recent transcript remains usable.
        status = "unavailable"
    try:
        with store.transaction() as db:
            current = store.get(sid, owner(), db)
            if (current["paused"] or current["stage"] == "COMPLETED"
                    or current["generation_id"] != captured["generation_id"]
                    or transcript_signature(current["turns"]) != signature):
                return
            if coverage is not None:
                current["_dialogue_memory"] = {"signature": signature, "through_turn_id": captured["turns"][-1]["id"],
                    "policy_version": POLICY_VERSION, "answer_count": answer_count, "coverage": coverage}
            store.event(db, current, "dialogue_memory_finished", {"status": status,
                "version": POLICY_VERSION,
                "provider": captured["snapshot"]["provider"], "model": captured["snapshot"]["config"]["assessment_model"],
                "request_seconds": time.monotonic()-started})
            store.save(db, current, owner_for(sid))
    except KeyError:
        # Tombstoned sessions cannot be recreated by an obsolete cloud result.
        return


def schedule_dialogue_memory(sid):
    captured = store.get(sid, owner())
    if captured["snapshot"]["provider"] == "codex" or not captured["cloud_consent"] or captured["paused"] or captured["stage"] == "COMPLETED":
        return
    answer_count = sum(t["role"] == "user" and dialogue_request_kind(t["text"]) is None for t in captured["turns"])
    prior = current_memory(captured)
    if answer_count-(prior["answer_count"] if prior else 0) < 2:
        return
    if providers.cooldowns.get(captured["snapshot"]["provider"], 0) > time.time():
        return
    task = memory_tasks.get(sid)
    if task and not task.done():
        return
    inputs = memory_input(captured, store.events(sid), dialogue_request_kind)
    task = asyncio.create_task(refresh_dialogue_memory(sid, captured, inputs, answer_count))
    memory_tasks[sid] = task
    def release(completed):
        if memory_tasks.get(sid) is completed:
            memory_tasks.pop(sid, None)
        if not completed.cancelled():
            completed.exception()  # Consume background errors without logging transcript payloads.
    task.add_done_callback(release)


def start_generation(sid, *, repeated_text=None):
    session_owners.setdefault(sid, owner())
    memory_task = memory_tasks.get(sid)
    if memory_task:
        memory_task.cancel()
    prior = generations.get(sid)
    if prior and not prior.done():
        prior.cancel()
    generations[sid] = asyncio.create_task(generate(sid, repeated_text=repeated_text))


def start_answer_generation(session):
    latest = next(turn for turn in reversed(session["turns"]) if turn["role"] == "user")
    if dialogue_request_kind(latest["text"]) == "repeat":
        start_generation(session["id"], repeated_text=repeatable_question(session))
    else:
        start_generation(session["id"])


@app.post("/api/sessions", response_model=public.Session, response_model_exclude_unset=True)
async def create_session(body: CreateSession):
    if not body.cloud_consent:
        raise ValueError("Consent to selected text and code processing before starting")
    settings = store.settings()
    provider = settings["provider"]
    config = await providers.validate(provider, settings["providers"][provider])
    validation = providers.validations.get(provider)
    if not validation or validation["config"] != config or time.time()-validation["validated_at"] > 3600:
        raise Conflict("Run a successful provider connection test in Settings before starting. Tests use synthetic input and may incur cost.")
    snapshot = {"provider": provider, "config": config, "consent_version": "2026-10-20", "settings_revision": settings["revision"], "captured_at": time.time()}
    s = sessions.create(body, owner(), snapshot)
    session_owners[s["id"]] = owner()
    if not s["turns"]:
        start_generation(s["id"])
    return sessions.view(s)


@app.get("/api/sessions", response_model=public.History, response_model_exclude_unset=True)
async def history():
    with store.connect() as db:
        rows = [json.loads(r[0]) for r in db.execute("SELECT body FROM sessions WHERE owner=? ORDER BY rowid DESC", (owner(),))]
    return {"sessions": [{k: s[k] for k in ("id", "role", "experience", "stage", "created", "expires", "revision", "paused")} | {"provider": s["snapshot"]["provider"]} for s in rows]}


@app.get("/api/sessions/{sid}", response_model=public.Session, response_model_exclude_unset=True)
async def get_session(sid: str):
    return sessions.view(store.get(sid, owner()))


@app.get("/api/sessions/{sid}/stream")
async def stream_session(sid: str, request: Request):
    s = store.get(sid, owner())
    account_id = owner()
    session_owners[sid] = account_id
    queue = asyncio.Queue(maxsize=64)
    subscribers.setdefault(sid, set()).add(queue)

    async def events():
        try:
            yield "data: "+encode({"type": "connected", "session_id": sid, "generation_id": s["generation_id"], "turn_id": s["turn_id"], "revision": s["revision"]})+"\n\n"
            while not await request.is_disconnected():
                try:
                    item = await asyncio.wait_for(queue.get(), 15)
                    yield "data: "+encode(item)+"\n\n"
                    if item["type"] == "resync" and queue not in subscribers.get(sid, set()):
                        break
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            subscribers.get(sid, set()).discard(queue)
            # A browser reload cannot leave generation/audio running unattended.
            if not subscribers.get(sid):
                await pause_disconnected_session(sid, account_id)
    return StreamingResponse(events(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})


@app.post("/api/sessions/{sid}/answers", response_model=public.Session, response_model_exclude_unset=True)
async def answer(sid: str, body: Answer):
    s, generate_next = sessions.answer(sid, owner(), body)
    if generate_next:
        await cancel_generation(sid)
        start_answer_generation(s)
    return sessions.view(s)


@app.post("/api/sessions/{sid}/actions", response_model=public.Session | public.Delete, response_model_exclude_unset=True)
async def action(sid: str, body: Action):
    s, generate_next = sessions.action(sid, owner(), body)
    if s["stage"] == "COMPLETED" and s["retention"] == "delete_on_close":
        return await delete_session(sid)
    if body.action == "disconnect" or s["stage"] == "COMPLETED":
        await cancel_generation(sid, interrupt_voice=False)
        if voice:
            try:
                await voice.close(sid)
            except (RuntimeError, OSError, asyncio.TimeoutError):
                raise HTTPException(503, "Interview state saved. Local voice cleanup is pending; reload before reconnecting.") from None
    elif body.action in {"pause", "stop", "keep_thinking", "end", "advance", "skip", "retry", "repeat"}:
        await cancel_generation(sid)
    if generate_next:
        if body.action == "repeat":
            previous = repeatable_question(s)
            start_generation(sid, repeated_text=previous)
        else:
            start_generation(sid)
    return sessions.view(s)


class Correction(Mutation):
    text: str = Field(min_length=1, max_length=12000)


@app.patch("/api/sessions/{sid}/utterances/{utterance_id}", response_model=public.Session, response_model_exclude_unset=True)
async def correct(sid: str, utterance_id: str, body: Correction):
    def operation(db, s):
        turn = next((t for t in s["turns"] if t["id"] == utterance_id and t["role"] == "user"), None)
        if not turn:
            raise KeyError(utterance_id)
        turn["version"] += 1
        turn["text"] = body.text
        turn["versions"].append({"version": turn["version"], "text": body.text, "kind": "candidate_correction"})
        s["assessment_version"] += 1
        s["generation_id"] = uid()
        for finding in s["findings"]:
            if finding.get("utterance_id") == utterance_id:
                finding["status"] = "stale"
        event = store.event(db, s, "transcript_correction", {"utterance_id": utterance_id, "version": turn["version"], "text": body.text, "correction_kind": "candidate_correction"})
        s["findings"].append(statement_observation(s, turn, event))
        return False
    s, _ = sessions.mutate(sid, owner(), body, operation, allow_completed=True)
    await cancel_generation(sid)
    return sessions.view(s)


class Dispute(Mutation):
    text: str = Field(min_length=1, max_length=5000)


@app.post("/api/sessions/{sid}/findings/{finding_id}/disputes", response_model=public.Session, response_model_exclude_unset=True)
async def dispute(sid: str, finding_id: str, body: Dispute):
    def operation(db, s):
        validated, _ = reviewed_observations(s, store.events(sid))
        finding = next((f for f in validated if f["id"] == finding_id), None)
        if not finding:
            raise KeyError(finding_id)
        s["findings"] = [f for f in s["findings"] if f["id"] != finding_id] + [finding]
        finding["status"] = "disputed"
        finding.setdefault("disputes", []).append({"id": uid(), "text": body.text, "created": time.time()})
        s["assessment_version"] += 1
        store.event(db, s, "finding_dispute", {"finding_id": finding_id, "text": body.text})
        return False
    s, _ = sessions.mutate(sid, owner(), body, operation, allow_completed=True)
    return sessions.view(s)


@app.post("/api/sessions/{sid}/practice-review", response_model=public.Session, response_model_exclude_unset=True)
async def generate_practice_review(sid: str, body: Mutation):
    captured = store.get(sid, owner())
    # Replay successful requests before spending another subscription turn.
    fingerprint = hashlib.sha256(encode(body.model_dump()).encode()).hexdigest()
    with store.connect() as db:
        prior = db.execute("SELECT fingerprint,response FROM requests WHERE session_id=? AND key=?", (sid, body.idempotency_key)).fetchone()
        submissions = [json.loads(r[0]) for r in db.execute("SELECT body FROM submissions WHERE session_id=?", (sid,))]
    if prior:
        if prior[0] != fingerprint:
            raise Conflict("Idempotency key was already used for a different request")
        return sessions.view(json.loads(prior[1]))
    if captured["revision"] != body.expected_revision:
        raise Conflict("Session changed. Reload before requesting a practice review.")
    if any(t.get("delivery") == "generating" for t in captured["turns"]):
        raise Conflict("Wait for the interviewer to finish or stop it before generating a practice review.")
    prompts, expected = practice_review.messages(captured, store.events(sid), submissions)
    result = await providers.structured(captured["snapshot"], prompts, practice_review.ReviewOutput.model_json_schema())
    try:
        reviewed = practice_review.validate(result, expected, captured, submissions)
    except ValueError as exc:
        raise ProviderFailure("malformed_output", "Practice review failed evidence validation. No score saved; retry explicitly.") from exc
    def operation(db, current):
        attempts = [json.loads(r[0]) for r in db.execute("SELECT body FROM submissions WHERE session_id=?", (sid,))]
        if practice_review.signature(current, attempts) != practice_review.signature(captured, submissions):
            raise Conflict("Interview evidence changed during review. Generate a fresh review.")
        current["_practice_review"] = reviewed
        return False
    current, _ = sessions.mutate(sid, owner(), body, operation, allow_completed=True)
    return sessions.view(current)


@app.get("/api/sessions/{sid}/report", response_model=public.Report, response_model_exclude_unset=True)
async def report(sid: str):
    s = store.get(sid, owner())
    events = store.events(sid)
    findings, excluded_findings = reviewed_observations(s, events)
    with store.connect() as db:
        submissions = [json.loads(r[0]) for r in db.execute("SELECT body FROM submissions WHERE session_id=?", (sid,))]
    references = []
    coding_done = any(e["kind"] in {"advance", "skip"} and e.get("from_stage") == "CODING" for e in events)
    baseline_done = any(e["kind"] in {"advance", "skip"} and e.get("from_stage") == "BASELINE_INCIDENT" for e in events)
    fresh_done = any(e["kind"] in {"advance", "skip"} and e.get("from_stage") == "TRANSFER" for e in events)
    if coding_done and baseline_done:
        reference = session_reference(s, "BASELINE_INCIDENT")
        if reference:
            references.append(reference)
    if fresh_done:
        reference = session_reference(s, "TRANSFER")
        if reference:
            references.append(reference)
    review = s.get("_practice_review")
    if review:
        review = {**review, "status": "current" if review.get("_signature") == practice_review.signature(s, submissions) else "stale"}
    return {
        "practice_review": review,
        "session_id": sid, "revision": s["revision"], "assessment_version": s["assessment_version"],
        "status": "partial", "mode": "authored_reference_review", "automatic_ratings_enabled": False,
        "calibration_limitation": "This AI-generated review is for practice. Scores may be imperfect and should not be used for hiring decisions. Example solutions relate to the exercises, not your overall ability.",
        "claims": s["claims"], "topics_tested": list(dict.fromkeys(e["stage"] for e in events
            if e["kind"] in {"answer", "hypothesis", "conclusion", "evidence", "submission"})),
        "timeline": [event for event in events if event["kind"] != "voice_delivery"],
        "turns": turns_with_delivery(s["turns"], events), "findings": findings,
        "criterion_coverage": criterion_coverage(s, findings, events), "excluded_findings": excluded_findings,
        "technical_assessment_status": "unavailable", "code_review_status": "unavailable",
        "reference_review": references, "coding_outcomes": submissions,
        "support_levels": {"baseline": "independent", "coached": "coached", "fresh": "independent"},
        "conversation_progress": conversation_progress(s["turns"], events),
        "conversation_memory": memory_context(s),
        "unresolved_questions": [point["question"] for point in conversation_progress(s["turns"], events)
                                 if point["status"] not in {"reply_recorded", "skipped"} and "?" in point["question"]],
        "next_practice_action": s["practice_objective"] or "Choose one diagnostic and explain which alternative outcome would change your conclusion.",
        "snapshot": s["snapshot"],
    }


class Submission(Mutation):
    language: str = Field(pattern="^(python|cpp)$")
    source: str = Field(min_length=1, max_length=65536)
    mode: str = Field(default="run", pattern="^(run|submit)$")


async def run_submission(submission):
    runner_url = os.getenv("RUNNER_URL", "").rstrip("/")
    token = os.getenv("RUNNER_BEARER_TOKEN", "")
    sid, job_id = submission["session_id"], submission["id"]
    try:
        if not runner_url or not token:
            submission.update(status="infrastructure_failure", detail="Dedicated Ubuntu runner is not configured. Code was saved; no code executed locally.")
        else:
            with store.transaction() as db:
                store.get(sid, owner(), db)
                saved = db.execute("SELECT body FROM submissions WHERE id=? AND session_id=?", (job_id, sid)).fetchone()
                if not saved or json.loads(saved[0])["status"] not in {"queued", "running"}:
                    return
                # Commit dispatch intent before the first network await. Even a
                # lost POST response must lead to conservative remote cleanup.
                submission["remote_attempted"] = True
                db.execute("UPDATE submissions SET body=? WHERE id=?", (encode(submission), job_id))
            async with httpx.AsyncClient(timeout=8) as client:
                headers = {"Authorization": "Bearer "+token}
                response = await client.post(runner_url+"/jobs", headers=headers, json={k: submission.get(k) for k in ("id", "language", "source", "problem_id", "mode", "content_digest")})
                response.raise_for_status()
                result = runner_response(response, job_id)
                deadline = time.monotonic()+65
                while result.get("status") in {"queued", "running"} and time.monotonic() < deadline:
                    await asyncio.sleep(.5)
                    store.get(sid, owner())
                    response = await client.get(runner_url+"/jobs/"+job_id, headers=headers)
                    response.raise_for_status()
                    result = runner_response(response, job_id)
                if result.get("status") in {"queued", "running"}:
                    await client.delete(runner_url+"/jobs/"+job_id, headers=headers)
                    raise TimeoutError()
                submission.update(status=result.get("status", "infrastructure_failure"), execution=result)
    except (httpx.HTTPError, TimeoutError, ValueError, TypeError):
        submission.update(status="infrastructure_failure", detail="Dedicated runner unavailable or timed out. This is not a candidate failure.")
        if runner_url:
            # A failed POST or poll can leave accepted work running remotely.
            # Persist cancellation before allowing another application job.
            with store.transaction() as db:
                store.queue_runner_cleanup(db, submission)
    except (KeyError, asyncio.CancelledError):
        return
    with store.transaction() as db:
        if db.execute("SELECT 1 FROM tombstones WHERE id=?", (sid,)).fetchone():
            return
        saved = db.execute("SELECT body FROM submissions WHERE id=? AND session_id=?", (job_id, sid)).fetchone()
        if not saved or json.loads(saved[0])["status"] not in {"queued", "running"}:
            return
        db.execute("UPDATE submissions SET body=? WHERE id=?", (encode(submission), job_id))
    await notify(sid, {"type": "execution", "session_id": sid, "submission_id": job_id, "status": submission["status"]})


def runner_response(response, job_id):
    result = response.json()
    validated = public.Execution.model_validate(result)
    if validated.id != job_id:
        raise ValueError("Dedicated runner returned an invalid or mismatched job")
    outcome = validated.result
    if validated.status in {"queued", "running"} and outcome is not None:
        raise ValueError("Active runner job already contains an outcome")
    if validated.status == "complete":
        if outcome is None or outcome.kind in {"cancelled", "infrastructure_error"}:
            raise ValueError("Completed runner job has no valid candidate outcome")
        if outcome.kind == "compile_error":
            if outcome.compile is None or outcome.compile.exit_code in {None, 0}:
                raise ValueError("Compile failure lacks a failing compiler exit")
        elif outcome.compile is not None:
            if outcome.kind not in {"timeout", "output_limit"} or outcome.public:
                raise ValueError("Compiler budget outcome is inconsistent")
        else:
            summary = outcome.public_summary
            if (not outcome.public or summary is None or summary.total != len(outcome.public)
                    or summary.passed != sum(case.kind == "passed" for case in outcome.public)):
                raise ValueError("Runner public outcome counts are inconsistent")
            if outcome.kind == "passed" and (summary.passed != summary.total
                    or outcome.hidden is not None and outcome.hidden.passed != outcome.hidden.total):
                raise ValueError("Passing outcome contains failed test counts")
    if validated.status == "infrastructure_error" and outcome is not None and outcome.kind != "infrastructure_error":
        raise ValueError("Infrastructure status contains a candidate outcome")
    if validated.status == "cancelled" and outcome is not None and outcome.kind != "cancelled":
        raise ValueError("Cancelled status contains a candidate outcome")
    return validated.model_dump(exclude_unset=True)


@app.post("/api/sessions/{sid}/submissions", response_model=public.SubmissionMutation, response_model_exclude_unset=True)
async def submit(sid: str, body: Submission):
    if len(body.source.encode("utf-8")) > 65536:
        raise ValueError("Source exceeds 64 KiB")
    job = None
    def operation(db, s):
        nonlocal job
        if s["stage"] != "CODING" or s["paused"]:
            raise Conflict("Coding is available only in the active coding stage")
        if db.execute("SELECT 1 FROM runner_cleanup LIMIT 1").fetchone():
            raise Conflict("Remote runner cleanup is pending. Restore its connection and wait for cancellation before starting another job.")
        active = db.execute("SELECT body FROM submissions").fetchall()
        if any(json.loads(row[0])["status"] in {"queued", "running"} for row in active):
            raise Conflict("One runner job is already active")
        problem_id = session_coding(s)["problem_id"]
        content_digest = s.get("_content_snapshot", {}).get("execution_digest")
        if not content_digest:
            raise Conflict("This session has no pinned execution content. Start a new interview before running code.")
        job = {"id": uid(), "session_id": sid, "problem_id": problem_id, "language": body.language, "source": body.source, "mode": body.mode, "status": "queued", "created": time.time(), "request_key": body.idempotency_key}
        job["content_digest"] = content_digest
        job["remote_attempted"] = False
        db.execute("INSERT INTO submissions VALUES(?,?,?)", (job["id"], sid, encode(job)))
        store.event(db, s, "submission", {"submission_id": job["id"], "language": body.language, "mode": body.mode})
        return False
    s, _ = sessions.mutate(sid, owner(), body, operation)
    if job:
        runner_tasks[job["id"]] = asyncio.create_task(run_submission(job))
    else:
        with store.connect() as db:
            job = next(json.loads(r[0]) for r in db.execute("SELECT body FROM submissions WHERE session_id=?", (sid,)) if json.loads(r[0]).get("request_key") == body.idempotency_key)
    return {"session": sessions.view(s), "submission": job}


@app.get("/api/submissions/{job_id}", response_model=public.Submission, response_model_exclude_unset=True)
async def get_submission(job_id: str):
    with store.connect() as db:
        row = db.execute("SELECT body FROM submissions WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise KeyError(job_id)
    result = json.loads(row[0])
    store.get(result["session_id"], owner())
    return result


@app.post("/api/sessions/{sid}/submissions/{job_id}/cancel", response_model=public.SubmissionMutation, response_model_exclude_unset=True)
async def cancel_submission(sid: str, job_id: str, body: Mutation):
    def operation(db, session):
        row = db.execute("SELECT body FROM submissions WHERE id=? AND session_id=?", (job_id, sid)).fetchone()
        if not row:
            raise KeyError(job_id)
        job = json.loads(row[0])
        if job["status"] not in {"queued", "running"}:
            raise Conflict("This attempt is already finished")
        job.update(status="cancelled", detail="Cancelled by the candidate. Remote cleanup may still be pending; this is not a candidate failure.")
        db.execute("UPDATE submissions SET body=? WHERE id=?", (encode(job), job_id))
        store.queue_runner_cleanup(db, job)
        store.event(db, session, "submission_cancelled", {"submission_id": job_id})
        return False
    session, _ = sessions.mutate(sid, owner(), body, operation)
    task = runner_tasks.pop(job_id, None)
    if task:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    await cleanup_runner_records()
    return {"session": sessions.view(session), "submission": await get_submission(job_id)}


@app.delete("/api/sessions/{sid}", response_model=public.Delete, response_model_exclude_unset=True)
async def delete_session(sid: str):
    store.get(sid, owner())
    # Remove authority before the first await: callbacks arriving during cleanup
    # must see a tombstone rather than a still-writable session.
    with store.transaction() as db:
        jobs = [json.loads(r[0]) for r in db.execute("SELECT body FROM submissions WHERE session_id=?", (sid,))]
        for job in jobs:
            store.queue_runner_cleanup(db, job)
        db.execute("INSERT OR IGNORE INTO tombstones VALUES(?,?)", (sid, time.time()))
        db.execute("DELETE FROM sessions WHERE id=? AND owner=?", (sid, owner()))
    cancelled = []
    for job in jobs:
        task = runner_tasks.pop(job["id"], None)
        if task:
            task.cancel()
            cancelled.append(task)
    if cancelled:
        await asyncio.gather(*cancelled, return_exceptions=True)
    files_removed, _ = await asyncio.gather(cleanup_local_session(sid), cleanup_runner_records())
    with store.connect() as db:
        pending = not files_removed or bool(db.execute("SELECT 1 FROM runner_cleanup WHERE session_id=?", (sid,)).fetchone())
    await notify(sid, {"type": "deleted", "session_id": sid})
    return {"deleted": not pending, "cleanup_pending": pending, "session_id": sid, "cloud_deletion": False, "note": "Application records removed. Remote runner cleanup retries while pending. Provider retention is separate; no forensic-erasure guarantee."}


class Offer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    session_id: str
    sdp: str = Field(max_length=100000)
    type: str = Field(pattern="^offer$")


@app.post("/api/offer", response_model=public.AnswerOffer, response_model_exclude_unset=True)
async def offer(body: Offer):
    s = store.get(body.session_id, owner())
    session_owners[body.session_id] = owner()
    if s["paused"]:
        raise Conflict("Resume an active session before enabling voice")
    if s["stage"] == "COMPLETED":
        with store.connect() as db:
            attempts = [json.loads(row[0]) for row in db.execute("SELECT body FROM submissions WHERE session_id=?", (body.session_id,))]
        review = s.get("_practice_review")
        if not review or review.get("_signature") != practice_review.signature(s, attempts):
            raise Conflict("Generate a current practice review before reading it aloud.")
    if voice is None:
        raise HTTPException(503, "Local speech runtime is not provisioned. Continue by typing.")
    async def on_answer(sid, text, metadata):
        if store.get(sid, owner_for(sid))["stage"] == "COMPLETED":
            return
        await cancel_generation(sid)
        current = store.get(sid, owner_for(sid))
        if current["stage"] == "COMPLETED" or not text.strip():
            return
        answer_body = Answer(text=text, expected_revision=current["revision"], idempotency_key="voice-"+uid())
        updated, generate_next = sessions.answer(sid, owner_for(sid), answer_body, speech_metadata=metadata)
        await notify(sid, {"type": "resync", "session_id": sid, "revision": updated["revision"]})
        if generate_next:
            start_answer_generation(updated)
    async def on_control(sid, command, payload):
        try:
            current = store.get(sid, owner_for(sid))
        except KeyError:
            return
        if command == "ready":
            if current["stage"] == "COMPLETED":
                with store.connect() as db:
                    attempts = [json.loads(row[0]) for row in db.execute("SELECT body FROM submissions WHERE session_id=?", (sid,))]
                review = current.get("_practice_review")
                if review and review.get("_signature") == practice_review.signature(current, attempts):
                    await voice.speak_saved_text(sid, practice_review.spoken_feedback(review), current["generation_id"])
            elif not current["paused"]:
                turn = next((turn for turn in reversed(current["turns"]) if turn["role"] == "assistant"
                             and turn.get("generation_id") == current["generation_id"]
                             and turn.get("delivery") in {"complete", "generating"}), None)
                if turn and turn["text"]:
                    await voice.speak_saved_text(sid, turn["text"], current["generation_id"], finished=turn["delivery"] == "complete")
            return
        if current["stage"] == "COMPLETED":
            return
        if command == "disconnect":
            await pause_disconnected_session(sid, owner_for(sid))
            try:
                current = store.get(sid, owner_for(sid))
            except KeyError:
                return
            await notify(sid, {"type": "resync", "session_id": sid, "revision": current["revision"]})
            return
        current = store.get(sid, owner_for(sid))
        name = "pause" if command == "input_limit" else "stop" if command == "interrupt" else command
        if name not in {"stop", "pause", "keep_thinking"}:
            return
        updated, _ = sessions.action(sid, owner_for(sid), Action(action=name, text=payload.get("draft_text", "")[:12000] if command == "input_limit" else "", expected_revision=current["revision"], idempotency_key="voice-control-"+uid()),
            pause_error={"code": "voice_input_limit", "message": payload.get("message", "Local speech input is unavailable. Review the saved draft or type your answer.")} if command == "input_limit" else None)
        await cancel_generation(sid, interrupt_voice=False)
        await notify(sid, {"type": "resync", "session_id": sid, "revision": updated["revision"]})
    try:
        return await voice.offer(body.session_id, body.sdp, body.type, on_answer, lambda sid: store.get(sid, owner_for(sid)), on_control)
    except (RuntimeError, OSError):
        raise HTTPException(503, "Local voice connection could not be initialized or cleaned up. Reload state and retry voice, or continue by typing.") from None


WEB_DIST = ROOT / "apps" / "web" / "dist"
if WEB_DIST.exists():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")

