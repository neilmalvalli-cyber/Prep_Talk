from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import re
import sqlite3
import tarfile
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import docker
from docker.errors import APIError, DockerException, ImageNotFound
from fastapi import Depends, FastAPI, Header, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field


SOURCE_LIMIT = 64 * 1024
CASE_LIMIT = 64 * 1024
OUTPUT_LIMIT = 64 * 1024
RUN_TIMEOUT = 2.0
COMPILE_TIMEOUT = 15.0
SUITE_TIMEOUT = 30.0
CPU_LIMIT_NANOS = 1_000_000_000
MEMORY_BYTES = 256 * 1024 * 1024
COMPILE_MEMORY_BYTES = 1024 * 1024 * 1024
PIDS_LIMIT = 64
TMPFS_BYTES = 64 * 1024 * 1024
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class JobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    language: Literal["python", "cpp"]
    source: str = Field(min_length=1, max_length=SOURCE_LIMIT)
    problem_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_]+$")
    content_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    mode: Literal["run", "submit"]


class JobStatus(BaseModel):
    id: str
    status: Literal["queued", "running", "complete", "cancelled", "infrastructure_error"]
    result: dict | None = None


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


class Runner:
    def __init__(self) -> None:
        self.token = _env("RUNNER_BEARER_TOKEN")
        self.db_path = Path(_env("RUNNER_DATABASE", "./data/jobs.sqlite3"))
        self.content_root = Path(_env("RUNNER_CONTENT_ROOT", "../../content")).resolve()
        self.compile_images = {
            "python": _env("RUNNER_PYTHON_IMAGE", "fieldnote-runner-python:3.11-v1"),
            "cpp": _env("RUNNER_CPP_COMPILE_IMAGE", "fieldnote-runner-cpp-compiler:20-v1"),
        }
        self.runtime_images = {
            "python": _env("RUNNER_PYTHON_IMAGE", "fieldnote-runner-python:3.11-v1"),
            "cpp": _env("RUNNER_CPP_RUNTIME_IMAGE", "fieldnote-runner-cpp-runtime:20-v1"),
        }
        self.available = False
        self.unavailable_reason = "runner has not completed its gVisor preflight"
        self.client: docker.DockerClient | None = None
        self.lock = threading.Lock()
        self.cancel_events: dict[str, threading.Event] = {}
        self.worker_active = threading.Event()
        self.active_container = None
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, status TEXT NOT NULL, request_json TEXT NOT NULL, result_json TEXT, created REAL NOT NULL, updated REAL NOT NULL)")
            db.execute("UPDATE jobs SET status='infrastructure_error', result_json=?, updated=? WHERE status IN ('queued','running')", (json.dumps({"kind":"infrastructure_error","error":"runner restarted before job completion"}), time.time()))

    def initialize(self) -> None:
        if not self.token or len(self.token.encode()) < 32:
            self.unavailable_reason = "RUNNER_BEARER_TOKEN must contain at least 32 bytes"
            return
        try:
            self.client = docker.from_env(timeout=3)
            info = self.client.info()
            runtimes = info.get("Runtimes", {})
            if "runsc" not in runtimes:
                self.unavailable_reason = "Docker daemon does not advertise the runsc runtime"
                return
            # This executes only a fixed trusted preflight command in the configured fixed image.
            for image in sorted(set([*self.compile_images.values(), *self.runtime_images.values()])):
                canary = self.client.containers.create(
                    image, command=["-c", "printf runsc-ready"], entrypoint="/bin/sh",
                    runtime="runsc", network_disabled=True, read_only=True,
                    mem_limit="64m", nano_cpus=CPU_LIMIT_NANOS, pids_limit=8,
                    cap_drop=["ALL"], security_opt=["no-new-privileges"],
                    tmpfs={"/tmp": "rw,nosuid,nodev,size=8m,mode=1777"},
                )
                try:
                    canary.start()
                    waited = canary.wait(timeout=10)
                    if waited.get("StatusCode") != 0 or canary.logs(stdout=True, stderr=True) != b"runsc-ready":
                        self.unavailable_reason = f"runsc preflight failed for fixed image {image}"
                        return
                finally:
                    try: canary.remove(force=True, v=True)
                    except Exception: pass
            self.available = True
            self.unavailable_reason = ""
        except Exception as exc:
            self.unavailable_reason = f"gVisor preflight unavailable: {type(exc).__name__}"

    def authorized(self, authorization: str | None) -> None:
        if not self.token or len(self.token.encode()) < 32:
            raise HTTPException(503, "runner authentication is not configured")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "bearer token required", headers={"WWW-Authenticate": "Bearer"})
        candidate = authorization[7:]
        if not hmac.compare_digest(candidate.encode(), self.token.encode()):
            raise HTTPException(401, "invalid bearer token", headers={"WWW-Authenticate": "Bearer"})

    def _db_update(self, job_id: str, status: str, result: dict | None = None) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE jobs SET status=?, result_json=?, updated=? WHERE id=?", (status, json.dumps(result) if result is not None else None, time.time(), job_id))

    def _load_tests(self, problem_id: str, mode: str, content_digest: str) -> tuple[dict, list[dict], int]:
        public_path = self.content_root / "coding" / f"{problem_id}.json"
        if not public_path.is_file():
            raise HTTPException(404, "unknown authored problem")
        try:
            problem = json.loads(public_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise HTTPException(503, "authored problem content is unavailable")
        public_tests = problem.get("public_tests")
        if not isinstance(public_tests, list) or not public_tests:
            raise HTTPException(503, "authored public tests are invalid")
        hidden_name = problem.get("hidden_test_set")
        if not isinstance(hidden_name, str) or not re.fullmatch(r"[a-z0-9_]+_hidden_v[0-9]+", hidden_name):
            raise HTTPException(503, "authored hidden test reference is invalid")
        hidden_path = self.content_root / "coding-private" / f"{hidden_name}.json"
        try:
            hidden = json.loads(hidden_path.read_text(encoding="utf-8"))
            tests = hidden["tests"]
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            raise HTTPException(503, "authored hidden tests are unavailable")
        if not isinstance(tests, list) or not tests:
            raise HTTPException(503, "authored hidden tests are invalid")
        digest = hashlib.sha256(json.dumps({"problem": problem, "hidden": hidden}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if not hmac.compare_digest(digest, content_digest):
            raise HTTPException(409, "authored execution content differs from the session snapshot")
        if mode == "run":
            return problem, public_tests, len(public_tests)
        return problem, public_tests + tests, len(public_tests)

    @staticmethod
    def _archive(name: str, data: bytes) -> bytes:
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as archive:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o400
            info.uid = info.gid = 65534
            info.uname = info.gname = "runner"
            archive.addfile(info, io.BytesIO(data))
        return stream.getvalue()

    def _container(self, language: str, compile_phase: bool = False):
        assert self.client is not None
        memory = COMPILE_MEMORY_BYTES if compile_phase else MEMORY_BYTES
        images = self.compile_images if compile_phase else self.runtime_images
        container = self.client.containers.create(
            images[language], runtime="runsc", command=["sleep", "infinity"],
            network_disabled=True, read_only=True, user="65534:65534",
            mem_limit=memory, nano_cpus=CPU_LIMIT_NANOS, pids_limit=PIDS_LIMIT,
            cap_drop=["ALL"], security_opt=["no-new-privileges"],
            tmpfs={"/tmp": f"rw,nosuid,nodev,size={TMPFS_BYTES},mode=1777"},
            stdin_open=False, tty=False, detach=True,
        )
        self.active_container = container
        return container

    @staticmethod
    def _exec_bounded(container, command: list[str], timeout: float) -> tuple[int | None, bytes, bytes, str | None]:
        """Collect output in a helper thread; kill the whole container on deadline or overflow."""
        output = {"code": None, "out": bytearray(), "err": bytearray(), "error": None}
        exceeded = threading.Event()
        done = threading.Event()

        def collect() -> None:
            try:
                api = container.client.api
                exec_id = api.exec_create(container.id, command, stdout=True, stderr=True, tty=False, user="65534:65534")["Id"]
                for out_part, err_part in api.exec_start(exec_id, stream=True, demux=True):
                    for key, part in (("out", out_part), ("err", err_part)):
                        if not part:
                            continue
                        room = OUTPUT_LIMIT - len(output["out"]) - len(output["err"])
                        output[key].extend(part[:max(0, room)])
                        if len(part) > room:
                            exceeded.set()
                            return
                output["code"] = api.exec_inspect(exec_id).get("ExitCode")
            except Exception as exc:  # the caller reports this as infrastructure failure
                output["error"] = type(exc).__name__
            finally:
                done.set()

        thread = threading.Thread(target=collect, daemon=True)
        thread.start()
        deadline = time.monotonic() + timeout
        while not done.wait(0.02):
            if exceeded.is_set():
                try: container.kill()
                except Exception: pass
                return None, bytes(output["out"][:OUTPUT_LIMIT]), bytes(output["err"][:OUTPUT_LIMIT]), "output_limit"
            if time.monotonic() >= deadline:
                try: container.kill()
                except Exception: pass
                return None, bytes(output["out"][:OUTPUT_LIMIT]), bytes(output["err"][:OUTPUT_LIMIT]), "timeout"
        if exceeded.is_set():
            try: container.kill()
            except Exception: pass
            return None, bytes(output["out"]), bytes(output["err"]), "output_limit"
        return output["code"], bytes(output["out"]), bytes(output["err"]), output["error"]

    def _execute(self, request: JobRequest, cancelled: threading.Event) -> dict:
        if not self.available or self.client is None:
            raise RuntimeError(self.unavailable_reason or "runsc unavailable")
        problem, tests, public_count = self._load_tests(request.problem_id, request.mode, request.content_digest)
        if request.language not in ("python", "cpp"):
            raise HTTPException(422, "unsupported language")
        suffix = "py" if request.language == "python" else "cpp"
        source_bytes = request.source.encode("utf-8")
        if len(source_bytes) > SOURCE_LIMIT:
            raise HTTPException(413, "source exceeds 64 KiB")
        if any(not isinstance(t.get("stdin"), str) or not isinstance(t.get("stdout"), str) for t in tests):
            raise RuntimeError("invalid authored tests")
        if any(len(t["stdin"].encode()) > CASE_LIMIT or len(t["stdout"].encode()) > CASE_LIMIT for t in tests):
            raise RuntimeError("authored test exceeds the configured bound")

        compiler = self._container(request.language, compile_phase=request.language == "cpp")
        artifact_tar: bytes | None = None
        try:
            compiler.start()
            compiler.put_archive("/tmp", self._archive(f"candidate.{suffix}", source_bytes))
            if request.language == "python":
                artifact_tar = self._archive("candidate.py", source_bytes)
            else:
                code, stdout, stderr, failure = self._exec_bounded(
                    compiler,
                    ["/usr/bin/g++", "-std=c++20", "-O2", "-pipe", "-o", "/tmp/candidate", "/tmp/candidate.cpp"],
                    COMPILE_TIMEOUT,
                )
                if cancelled.is_set():
                    return {"kind": "cancelled", "public": [], "hidden": {"passed": 0, "total": 0}}
                if failure:
                    return {"kind": "timeout" if failure == "timeout" else "output_limit" if failure == "output_limit" else "infrastructure_error", "compile": {"exit_code": code, "stdout": stdout.decode("utf-8", "replace"), "stderr": stderr.decode("utf-8", "replace")}}
                if code != 0:
                    return {"kind": "compile_error", "compile": {"exit_code": code, "stdout": stdout.decode("utf-8", "replace"), "stderr": stderr.decode("utf-8", "replace")}}
                bits, stat = compiler.get_archive("/tmp/candidate")
                if not stat or int(stat.get("size", 0)) > SOURCE_LIMIT * 32:
                    return {"kind": "infrastructure_error", "message": "compiled artifact exceeded transfer bound"}
                artifact_tar = b"".join(bits)
        finally:
            try: compiler.remove(force=True, v=True)
            except Exception: pass
            self.active_container = None

        results: list[dict] = []
        suite_started = time.monotonic()
        for index, test in enumerate(tests):
            if cancelled.is_set():
                return {"kind": "cancelled", "public": results[:public_count], "hidden": {"passed": 0, "total": 0}}
            if time.monotonic() - suite_started >= SUITE_TIMEOUT:
                results.append({"kind": "timeout"})
                break
            case = self._container(request.language)
            try:
                case.start()
                assert artifact_tar is not None
                case.put_archive("/tmp", artifact_tar)
                case.put_archive("/tmp", self._archive("input", test["stdin"].encode("utf-8")))
                command = ["/bin/sh", "-c", "exec /usr/local/bin/python3 -I /tmp/candidate.py < /tmp/input"] if request.language == "python" else ["/bin/sh", "-c", "exec /tmp/candidate < /tmp/input"]
                remaining = max(0.01, min(RUN_TIMEOUT, SUITE_TIMEOUT - (time.monotonic() - suite_started)))
                code, stdout, stderr, failure = self._exec_bounded(case, command, remaining)
                if cancelled.is_set():
                    return {"kind": "cancelled", "public": results[:public_count], "hidden": {"passed": 0, "total": 0}}
                if failure == "timeout":
                    result = {"kind": "timeout"}
                elif failure == "output_limit":
                    result = {"kind": "output_limit"}
                elif failure:
                    result = {"kind": "infrastructure_error"}
                elif code != 0:
                    result = {"kind": "runtime_error", "exit_code": code, "stderr": stderr.decode("utf-8", "replace")[:OUTPUT_LIMIT]}
                else:
                    actual = stdout.decode("utf-8", "replace")
                    result = {"kind": "passed" if actual == test["stdout"] else "wrong_answer"}
                if index < public_count:
                    result.update({"stdout": stdout.decode("utf-8", "replace")[:OUTPUT_LIMIT], "expected_stdout": test["stdout"], "stderr": stderr.decode("utf-8", "replace")[:OUTPUT_LIMIT]})
                results.append(result)
            except (DockerException, APIError, OSError):
                raise RuntimeError("isolated case execution failed")
            finally:
                try: case.remove(force=True, v=True)
                except Exception: pass
                self.active_container = None
            if results[-1]["kind"] == "infrastructure_error":
                raise RuntimeError("isolated case execution failed")
            if results[-1]["kind"] in {"timeout", "output_limit"}:
                # The bounded exec killed this case's whole container. Do not
                # launch further candidate containers after a job budget breach.
                break

        public = results[:public_count]
        hidden_results = results[public_count:]
        public_passed = sum(r["kind"] == "passed" for r in public)
        hidden_passed = sum(r["kind"] == "passed" for r in hidden_results)
        kinds = {r["kind"] for r in results}
        overall = "passed" if len(results) == len(tests) and len(kinds) == 1 and "passed" in kinds else next((k for k in ("timeout", "output_limit", "compile_error", "runtime_error", "wrong_answer") if k in kinds), "infrastructure_error")
        return {"kind": overall, "public": public, "public_summary": {"passed": public_passed, "total": len(public)}, "hidden": {"passed": hidden_passed, "total": len(hidden_results)}}

    def enqueue(self, request: JobRequest) -> None:
        if not self.available:
            raise HTTPException(503, f"isolated runner unavailable: {self.unavailable_reason}")
        with self.lock:
            request_record = {
                "id": request.id,
                "language": request.language,
                "problem_id": request.problem_id,
                "content_digest": request.content_digest,
                "mode": request.mode,
                "source_sha256": hashlib.sha256(request.source.encode("utf-8")).hexdigest(),
            }
            request_fingerprint = json.dumps(request_record, sort_keys=True, separators=(",", ":"))
            with sqlite3.connect(self.db_path) as db:
                row = db.execute("SELECT status FROM jobs WHERE id=?", (request.id,)).fetchone()
                if row:
                    existing = db.execute("SELECT request_json FROM jobs WHERE id=?", (request.id,)).fetchone()[0]
                    if existing != request_fingerprint:
                        raise HTTPException(409, "job id already belongs to a different immutable request")
                    return
                if self.worker_active.is_set():
                    raise HTTPException(429, "runner is busy; retry after the active job completes")
                db.execute("INSERT INTO jobs(id,status,request_json,created,updated) VALUES(?,?,?,?,?)", (request.id, "queued", request_fingerprint, time.time(), time.time()))
            event = threading.Event()
            self.cancel_events[request.id] = event
            self.worker_active.set()
        threading.Thread(target=self._work, args=(request, event), daemon=True).start()

    def _work(self, request: JobRequest, cancelled: threading.Event) -> None:
        self._db_update(request.id, "running")
        try:
            result = self._execute(request, cancelled)
            status = "cancelled" if result.get("kind") == "cancelled" else "infrastructure_error" if result.get("kind") == "infrastructure_error" else "complete"
        except Exception as exc:
            result = {"kind": "infrastructure_error", "error": type(exc).__name__}
            status = "infrastructure_error"
        self._db_update(request.id, status, result)
        with self.lock:
            self.cancel_events.pop(request.id, None)
            self.worker_active.clear()

    def get(self, job_id: str) -> dict:
        with sqlite3.connect(self.db_path) as db:
            row = db.execute("SELECT status,result_json FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise HTTPException(404, "job not found")
        return {"id": job_id, "status": row[0], "result": json.loads(row[1]) if row[1] else None}

    def cancel(self, job_id: str) -> None:
        with self.lock:
            with sqlite3.connect(self.db_path) as db:
                exists = db.execute("SELECT 1 FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not exists:
                raise HTTPException(404, "job not found")
            event = self.cancel_events.get(job_id)
            if event:
                event.set()
                if self.active_container is not None:
                    try: self.active_container.kill()
                    except Exception: pass
            # Delete first so a late worker completion cannot recreate stored output.
            with sqlite3.connect(self.db_path) as db:
                db.execute("DELETE FROM jobs WHERE id=?", (job_id,))
            self.cancel_events.pop(job_id, None)


runner = Runner()


@asynccontextmanager
async def lifespan(app: FastAPI):
    runner.initialize()
    yield


app = FastAPI(title="Fieldnote isolated runner", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)


def require_auth(authorization: str | None = Header(default=None)) -> None:
    runner.authorized(authorization)


@app.get("/health")
def health(_: None = Depends(require_auth)):
    return {"status": "ready" if runner.available else "unavailable", "isolation": "runsc" if runner.available else None, "reason": runner.unavailable_reason or None}


@app.post("/jobs", status_code=202, response_model=JobStatus)
def create_job(job: JobRequest, _: None = Depends(require_auth)):
    runner.enqueue(job)
    return runner.get(job.id)


@app.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str, _: None = Depends(require_auth)):
    if not ID_RE.fullmatch(job_id):
        raise HTTPException(404, "job not found")
    return runner.get(job_id)


@app.delete("/jobs/{job_id}", status_code=204)
def cancel_job(job_id: str, _: None = Depends(require_auth)):
    if not ID_RE.fullmatch(job_id):
        raise HTTPException(404, "job not found")
    runner.cancel(job_id)
    return Response(status_code=204)
