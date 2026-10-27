from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from .assessment import statement_observation, statement_sources, reviewed_observations
from .responses import Session as PublicSession
from .dialogue_memory import memory_context

from .store import Conflict, encode, uid

ROOT = Path(__file__).resolve().parents[3]
CONTENT = ROOT / "content"
STAGES = ["RESUME_ROLE_DIALOGUE", "BASELINE_INCIDENT", "CODING", "REVIEW", "COACHED_RETRY", "TRANSFER", "REPORT", "COMPLETED"]


class Mutation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int = Field(ge=0)
    idempotency_key: str = Field(min_length=8, max_length=128)


class Answer(Mutation):
    text: str = Field(min_length=1, max_length=12000)


class Action(Mutation):
    action: Literal["pause", "disconnect", "resume", "stop", "keep_thinking", "repeat", "retry", "advance", "skip", "end", "evidence", "hypothesis", "conclusion", "hint", "practice_objective", "extend"]
    card_id: str | None = None
    text: str = Field(default="", max_length=12000)


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source_bullet: str = Field(max_length=5000)
    page: int | None = Field(default=None, ge=1, le=20)
    offset: int = Field(default=0, ge=0, le=50000)
    project: str = Field(default="", max_length=500)
    contribution: str = Field(default="", max_length=5000)
    technology: str = Field(default="", max_length=1000)
    result: str = Field(default="", max_length=2000)
    measurement: str = Field(default="", max_length=2000)
    confidentiality: str = Field(default="", max_length=2000)


class CreateSession(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    resume_id: str | None = None
    context: str = Field(min_length=1, max_length=50000)
    claims: list[Claim] = Field(min_length=1, max_length=50)
    role: Literal["backend", "frontend", "fullstack"]
    experience: Literal["junior", "intermediate"]
    language: Literal["python", "cpp"] = "python"
    duration_minutes: int = Field(default=25, ge=5, le=120)
    cloud_consent: bool
    record_audio: bool = False
    retention: Literal["30_days", "delete_on_close"] = "30_days"
    job_text: str = Field(default="", max_length=12000)
    idempotency_key: str = Field(min_length=8, max_length=128)


def records(folder):
    return [json.loads(path.read_text(encoding="utf-8-sig")) for path in sorted((CONTENT/folder).glob("*.json"))]


def role_record(role):
    for row in records("roles"):
        if row["role_id"] in {role, role+"_engineer"}:
            return row
    raise ValueError("Unknown role")


def scenario_record(family, stage):
    suffix = {"BASELINE_INCIDENT": "baseline", "COACHED_RETRY": "coached", "TRANSFER": "fresh"}.get(stage)
    if not suffix:
        return None
    for row in records("scenarios"):
        expected_family = "cache_price" if family == "caching" else "frontend_ordering"
        if row.get("family") == expected_family and row.get("attempt") in {suffix, suffix+"_uncoached"}:
            return row
    raise ValueError(f"Missing authored scenario: {family}/{suffix}")


def public_scenario(row, revealed):
    if row is None:
        return None
    return {key: row[key] for key in ("scenario_id", "schema_version", "title", "initial_facts") if key in row} | {
        "available_cards": [{"card_id": card["card_id"], "title": card.get("title", card.get("source", card["card_id"]))} for card in row["public_evidence"]],
        "revealed_cards": [card for card in row["public_evidence"] if card["card_id"] in revealed],
        "general_role_exercise": True,
        "coaching": row.get("coaching"),
    }


def public_coding_problem(role, experience):
    problem_id = role["levels"][experience]["coding_problem"]
    problem = next((row for row in records("coding") if row["problem_id"] == problem_id), None)
    if problem is None:
        raise ValueError("The selected role has no authored coding problem")
    return {key: problem[key] for key in ("schema_version", "problem_id", "title", "statement", "contract", "public_tests")}


def capture_content(role, experience, family):
    problem_id = role["levels"][experience]["coding_problem"]
    problem = next(row for row in records("coding") if row["problem_id"] == problem_id)
    hidden = json.loads((CONTENT/"coding-private"/(problem["hidden_test_set"]+".json")).read_text(encoding="utf-8-sig"))
    execution_digest = hashlib.sha256(json.dumps({"problem": problem, "hidden": hidden}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    scenarios = {stage: scenario_record(family, stage) for stage in ("BASELINE_INCIDENT", "COACHED_RETRY", "TRANSFER")}
    references = {stage: json.loads((CONTENT/"scenario-private"/(row["private_reference_id"]+".json")).read_text(encoding="utf-8-sig"))
                  for stage, row in scenarios.items()}
    content = {"role": role, "coding_problem": public_coding_problem(role, experience), "execution_digest": execution_digest,
        "scenarios": scenarios, "references": references,
        "rubric": json.loads((CONTENT/"rubrics/criteria.json").read_text(encoding="utf-8-sig")),
        "prompts": {name: (ROOT/"prompts"/name).read_text(encoding="utf-8-sig")
                    for name in ("live_interviewer_v1.md", "coach_v1.md")}}
    content["digest"] = hashlib.sha256(encode(content).encode()).hexdigest()
    return content


def session_role(session):
    return session.get("_content_snapshot", {}).get("role") or role_record(session["role"])


def session_scenario(session, stage=None):
    stage = stage or session["stage"]
    if "_content_snapshot" in session:
        return session["_content_snapshot"]["scenarios"].get(stage)
    return scenario_record(session["family"], stage)


def session_coding(session):
    if "_content_snapshot" in session:
        return session["_content_snapshot"]["coding_problem"]
    return public_coding_problem(session_role(session), session["experience"])


def session_reference(session, stage):
    if "_content_snapshot" in session:
        return session["_content_snapshot"]["references"].get(stage)
    row = session_scenario(session, stage)
    path = CONTENT/"scenario-private"/(row["private_reference_id"]+".json")
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else None


def session_prompt(session, name):
    if "_content_snapshot" in session:
        return session["_content_snapshot"]["prompts"][name]
    return (ROOT/"prompts"/name).read_text(encoding="utf-8-sig")


def repeatable_question(session):
    return next((turn["text"] for turn in reversed(session["turns"])
                 if turn["role"] == "assistant" and turn.get("delivery") == "complete"
                 and turn.get("stage") == session["stage"]
                 and turn["text"].strip()), None)


def dialogue_request_kind(text):
    normalized = " ".join(text.casefold().replace("’", "'").strip().rstrip(".?!").split())
    normalized = re.sub(r"^please[, ]+|,? please$", "", normalized)
    if normalized in {"repeat", "repeat the question", "can you repeat the question", "could you repeat the question",
                      "repeat that", "can you repeat that", "could you repeat that", "say that again",
                      "can you say that again", "could you say that again", "i didn't catch that"}:
        return "repeat"
    if normalized in {"rephrase", "can you rephrase", "could you rephrase", "rephrase the question",
                      "can you rephrase the question", "could you rephrase the question", "can you explain the question",
                      "could you explain the question", "i don't understand the question", "i do not understand the question",
                      "what do you mean", "can you clarify", "could you clarify", "can you clarify the question"}:
        return "clarification"
    if normalized in {"i don't know", "i do not know", "i'm not sure", "i am not sure", "not sure", "i don't remember", "i do not remember"}:
        return "uncertainty"
    if normalized in {"skip", "skip this question", "skip this one", "next question", "can we skip this question",
                      "can we skip this one", "could we skip this question", "i'd like to skip this one",
                      "i would like to skip this question", "let's skip this question", "let's skip this one"}:
        return "skip_question"
    return None


def dialogue_topic_position(answers):
    position = 0
    for answer in answers:
        kind = dialogue_request_kind(answer["text"])
        if kind == "skip_question":
            position = (position//2+1)*2
        elif kind is None:
            position += 1
    return position


def interview_plan(session):
    """Schedule bounded resume exploration, then role fundamentals, then coding.

    Scheduling is application-owned; the model chooses a grounded question and
    follow-up, never decides that a reply proves competence or ends the session.
    """
    turns = session["turns"]
    answers = [t for t in turns if t["role"] == "user" and t["stage"] == "RESUME_ROLE_DIALOGUE"]
    opening = next((t for t in turns if t.get("interview_opening") and t.get("delivery") == "complete"), None)
    introduction = next((t for t in answers if opening and turns.index(t) > turns.index(opening) and not dialogue_request_kind(t["text"])), None)
    answers = [t for t in answers if t is not introduction]
    position = dialogue_topic_position(answers)
    resume_topics = min(2, len(session["claims"]))
    role = session_role(session)
    objectives = role["levels"][session["experience"]]["question_objectives"]
    if position < resume_topics*2:
        claim = session["claims"][position//2]
        objective = "Explore the candidate's own contribution to this confirmed experience. Start with what they did, then follow their answer into one concrete decision, challenge, or verification. Do not assume it was a software project if the source describes another activity."
        phase = "resume_experience"
    else:
        claim = None
        objective = ("Ask a general practical role question, independent of the resume, about: "
                     + objectives[min((position-resume_topics*2)//2, len(objectives)-1)]
                     + ". Use an explicitly hypothetical example when discussing a design decision; do not assume that decision occurred in the candidate's past work.")
        phase = "role_fundamentals"
    return {"phase": phase, "objective": objective, "claim": claim,
            "action": "transition" if position and position%2 == 0 else "adaptive_follow_up" if position else "open_current_objective",
            "ready_for_coding": position >= (resume_topics+len(objectives))*2}


def turns_with_delivery(turns, events):
    snapshots = {event.get("generation_id"): event for event in events if event["kind"] == "voice_delivery"}
    return [{**turn, **({"speech_delivery": snapshots[turn["generation_id"]]}
                       if turn.get("generation_id") in snapshots else {})} for turn in turns]


def conversation_progress(turns, events):
    """Track recorded replies, never infer correctness or actual audio hearing."""
    sources = statement_sources(events)
    questions = {}
    latest = {}
    for turn in turns:
        stage = turn["stage"]
        if turn["role"] == "assistant":
            if turn.get("delivery") != "complete" or not turn["text"].strip():
                latest.pop(stage, None)
                continue
            # Repeat uses the same wording and is the same conversational point.
            key = (stage, " ".join(turn["text"].split()).casefold())
            question = questions.setdefault(key, {"question_turn_id": turn["id"], "stage": stage,
                "question": turn["text"].strip(), "repeat_turn_ids": [], "responses": []})
            if question["question_turn_id"] != turn["id"]:
                question["repeat_turn_ids"].append(turn["id"])
            latest[stage] = question
        elif turn["role"] == "user" and stage in latest:
            source = sources.get((turn["id"], turn["version"]))
            if source and source.get("text") == turn["text"]:
                latest[stage]["responses"].append({"utterance_id": turn["id"], "source_version": turn["version"],
                    "event_id": source["id"], "excerpt": turn["text"][:800]})
    def progress_status(question):
        if not question["responses"]:
            return "no_reply_recorded"
        # Request-only replies leave the question conversationally open. Use
        # the full authoritative text, not the display excerpt, for intent.
        response = question["responses"][-1]
        source = sources[(response["utterance_id"], response["source_version"])]
        kind = dialogue_request_kind(source["text"])
        return {"repeat": "repeat_requested", "clarification": "needs_clarification",
                "uncertainty": "uncertainty_expressed", "skip_question": "skipped"}.get(kind, "reply_recorded")

    return [{**question, "status": progress_status(question),
             "interpretation": "A recorded reply does not establish technical resolution or correctness; generated questions do not prove audio delivery."}
            for question in questions.values()]


class Sessions:
    def __init__(self, store):
        self.store = store

    def view(self, session):
        result = {key: session[key] for key in PublicSession.model_fields if key in session}
        frozen = session.get("_content_snapshot")
        result["content_provenance"] = {"status": "captured" if frozen else "legacy_unpinned",
                                        "digest": frozen["digest"] if frozen else None}
        row = session_scenario(session)
        result["scenario"] = public_scenario(row, session["revealed"])
        result["coding_problem"] = session_coding(session)
        result["events"] = self.store.events(session["id"])
        result["findings"] = reviewed_observations(session, result["events"])[0]
        result["turns"] = turns_with_delivery(session["turns"], result["events"])
        result["duration_reached"] = time.time()-session["created"] >= session["duration_minutes"]*60
        return result

    def create(self, body, owner, snapshot):
        request = body.model_dump()
        fingerprint = hashlib.sha256(encode(request).encode()).hexdigest()
        with self.store.transaction() as db:
            for row in db.execute("SELECT body FROM sessions WHERE owner=?", (owner,)).fetchall():
                previous = json.loads(row[0])
                if previous.get("creation_key") == body.idempotency_key:
                    if previous["creation_fingerprint"] != fingerprint:
                        raise Conflict("Idempotency key was already used for a different request")
                    return previous
            if db.execute("SELECT 1 FROM sessions WHERE active=1").fetchone():
                raise Conflict("An interview is already active. Resume or end it before starting another.")
            if body.resume_id:
                resume = db.execute("SELECT body FROM resumes WHERE id=? AND owner=?", (body.resume_id, owner)).fetchone()
                if not resume:
                    raise ValueError("Resume upload expired or belongs to another owner. Upload again.")
            role = role_record(body.role)
            family = "frontend" if body.role == "frontend" or (body.role == "fullstack" and any(s in body.context.lower() for s in ("react", "browser", "frontend"))) else "caching"
            now = time.time()
            session = {"id": uid(), "revision": 0, "stage": STAGES[0], "paused": False, "generation_id": uid(), "turn_id": uid(), "created": now, "expires": now+30*86400, "snapshot": snapshot, "role_version": role["schema_version"], "family": family, "turns": [], "revealed": [], "support_level": "independent", "coding_skipped": False, "findings": [], "assessment_version": 0, "practice_objective": "", "last_error": None, "creation_key": body.idempotency_key, "creation_fingerprint": fingerprint, **{k: v for k, v in request.items() if k not in {"idempotency_key", "resume_id"}}}
            session["_opening_version"] = 1
            if snapshot["provider"] == "codex":
                session["_methodology_version"] = 2
            session["_content_snapshot"] = capture_content(role, body.experience, family)
            db.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?)", (session["id"], owner, 0, 1, session["expires"], encode(session)))
            self.store.event(db, session, "consent", {"cloud": True, "record_audio": body.record_audio, "version": "2026-10-20", "provider": snapshot["provider"], "retention": body.retention})
            self.store.event(db, session, "claims_confirmed", {"claims": session["claims"]})
            if body.resume_id:
                db.execute("DELETE FROM resumes WHERE id=?", (body.resume_id,))
        return session

    def mutate(self, sid, owner, body, operation, *, allow_completed=False):
        data = body.model_dump()
        fingerprint = hashlib.sha256(encode(data).encode()).hexdigest()
        with self.store.transaction() as db:
            session = self.store.get(sid, owner, db)
            prior = db.execute("SELECT fingerprint,response FROM requests WHERE session_id=? AND key=?", (sid, body.idempotency_key)).fetchone()
            if prior:
                if prior[0] != fingerprint:
                    raise Conflict("Idempotency key was already used for a different action")
                return json.loads(prior[1]), False
            if session["revision"] != body.expected_revision:
                raise Conflict("Session changed. Reload authoritative state before retrying.")
            if session["stage"] == "COMPLETED" and not allow_completed:
                raise Conflict("Interview has ended")
            session["revision"] += 1
            result = operation(db, session)
            self.store.save(db, session, owner)
            db.execute("INSERT INTO requests VALUES(?,?,?,?)", (sid, body.idempotency_key, fingerprint, encode(session)))
        return session, result

    def answer(self, sid, owner, body, *, speech_metadata=None):
        def operation(db, session):
            if session["paused"]:
                raise Conflict("Resume the interview before answering")
            if any(t.get("delivery") == "generating" for t in session["turns"]):
                raise Conflict("Stop the active response before submitting another answer")
            text = body.text.strip()
            if not text:
                raise ValueError("Enter an answer; silence is not an incorrect response")
            if dialogue_request_kind(text) == "repeat" and not repeatable_question(session):
                raise Conflict("No complete question is available to repeat in this stage")
            turn = {"id": uid(), "role": "user", "text": text, "version": 1, "versions": [{"version": 1, "text": text, "kind": "original"}], "stage": session["stage"], "support_level": session["support_level"], "delivery": "complete", "created": time.time()}
            turn["input_source"] = "local_speech" if speech_metadata is not None else "typed"
            if speech_metadata is not None:
                turn["speech_metadata"] = speech_metadata
            session["turns"].append(turn)
            session["turn_id"] = turn["id"]
            session["generation_id"] = uid()
            session["last_error"] = None
            session["draft_answer"] = ""
            event = self.store.event(db, session, "answer", {"utterance_id": turn["id"], "version": 1, "text": text, "visible_cards": list(session["revealed"]), "support_level": session["support_level"], "input_source": turn["input_source"]})
            session["findings"].append(statement_observation(session, turn, event))
            if session.get("_methodology_version") == 2 and session["stage"] == "RESUME_ROLE_DIALOGUE":
                phase = interview_plan(session)
                if phase["ready_for_coding"]:
                    session["stage"] = "CODING"
                    session["revealed"] = []
                    self.store.event(db, session, "advance", {"from_stage": "RESUME_ROLE_DIALOGUE", "text": "Resume and role discussion complete; begin coding.", "card_id": ""})
            return True
        return self.mutate(sid, owner, body, operation)

    def action(self, sid, owner, body, *, pause_error=None):
        def operation(db, s):
            action = body.action
            from_stage = s["stage"]
            regenerate = False
            if s["paused"] and action not in {"resume", "pause", "disconnect", "stop", "end"}:
                raise Conflict("Resume the interview before changing practice state")
            if action in {"hypothesis", "conclusion", "evidence"} and s["stage"] not in {"BASELINE_INCIDENT", "COACHED_RETRY", "TRANSFER"}:
                raise Conflict("Reasoning actions are available only within the current synthetic exercise")
            if action == "practice_objective" and s["stage"] not in {"REVIEW", "COACHED_RETRY"}:
                raise Conflict("Select a practice objective during review or coached practice")
            if action in {"pause", "disconnect", "stop", "keep_thinking", "end"}:
                s["generation_id"] = uid()
                for turn in s["turns"]:
                    if turn["delivery"] == "generating":
                        turn["delivery"] = "interrupted"
            if action in {"pause", "disconnect"}:
                s["paused"] = True
                if pause_error is not None:
                    s["last_error"] = pause_error
                if body.text.strip():
                    s["draft_answer"] = body.text
            elif action == "resume":
                s["paused"] = False
            elif action == "end":
                s["stage"] = "COMPLETED"
                s["paused"] = False
            elif action in {"advance", "skip"}:
                if s["paused"]:
                    raise Conflict("Resume before changing stage")
                attempts = [json.loads(r[0]) for r in db.execute("SELECT body FROM submissions WHERE session_id=?", (sid,))]
                completed_attempt = any(a["mode"] == "submit" and a["status"] not in {"queued", "running"} for a in attempts)
                if s["stage"] == "CODING" and not s["coding_skipped"] and not completed_attempt:
                    if action != "skip":
                        raise Conflict("Submit a coding attempt or explicitly skip coding before review")
                    s["coding_skipped"] = True
                if s["stage"] in {"BASELINE_INCIDENT", "TRANSFER"} and action != "skip":
                    if not any(e["kind"] == "conclusion" and e["stage"] == s["stage"] for e in self.store.events(sid)):
                        raise Conflict("Confirm your conclusion and verification plan, or explicitly skip")
                if s.get("_methodology_version") == 2:
                    sequence = ["RESUME_ROLE_DIALOGUE", "CODING", "REVIEW", "REPORT", "COMPLETED"]
                    s["stage"] = sequence[sequence.index(s["stage"])+1]
                else:
                    s["stage"] = STAGES[STAGES.index(s["stage"])+1]
                s["revealed"] = []
                s["support_level"] = "coached" if s["stage"] == "COACHED_RETRY" else "independent"
                s["generation_id"] = uid()
                regenerate = s["stage"] not in {"REPORT", "COMPLETED"}
            elif action == "evidence":
                scenario = session_scenario(s)
                card = next((c for c in scenario["public_evidence"] if c["card_id"] == body.card_id), None) if scenario else None
                if not card:
                    raise ValueError("Evidence card is not available in this exercise")
                required = card.get("requires", [])
                if isinstance(required, str):
                    required = [required] if required else []
                if any(r not in s["revealed"] for r in required):
                    raise Conflict("Request the preceding evidence first")
                if body.card_id not in s["revealed"]:
                    s["revealed"].append(body.card_id)
            elif action in {"hypothesis", "conclusion", "practice_objective"}:
                if not body.text.strip():
                    raise ValueError("Enter your confirmed explanation or practice objective")
                if action == "practice_objective":
                    s["practice_objective"] = body.text
            elif action == "hint":
                if s["stage"] != "COACHED_RETRY":
                    raise Conflict("Hints are available only in the coached exercise after the baseline and coding attempt")
                if not s["practice_objective"].strip():
                    raise Conflict("Choose a practice objective before requesting guided help")
                s["support_level"] = "coached"
                s["generation_id"] = uid()
                regenerate = True
            elif action in {"retry", "repeat"}:
                if action == "repeat" and repeatable_question(s) is None:
                    raise Conflict("No complete question is available to repeat. Retry an incomplete response explicitly.")
                s["generation_id"] = uid()
                regenerate = True
            elif action == "extend":
                s["duration_minutes"] += 10
            self.store.event(db, s, action, {"text": body.text, "card_id": body.card_id, "from_stage": from_stage})
            return regenerate
        return self.mutate(sid, owner, body, operation)

    def update_generation_text(self, sid, owner, generation_id, turn_id, text):
        """Persist a delta atomically before publication; safe to call off-loop."""
        with self.store.transaction() as db:
            state = self.store.get(sid, owner, db)
            if state["generation_id"] != generation_id or state["paused"] or state["stage"] == "COMPLETED":
                return False
            turn = next((turn for turn in state["turns"] if turn["id"] == turn_id
                         and turn["role"] == "assistant" and turn.get("generation_id") == generation_id), None)
            if turn is None or turn.get("delivery") != "generating":
                return False
            turn["text"] = text
            self.store.save(db, state, owner)
            return True

    def prompt(self, s):
        role = session_role(s)
        objectives = role["levels"][s["experience"]]["question_objectives"]
        answers = [t for t in s["turns"] if t["role"] == "user" and t["stage"] == s["stage"]]
        introduction = s.get("_opening_version") == 1 and s["stage"] == "RESUME_ROLE_DIALOGUE"
        opening_turn = next((t for t in s["turns"] if t.get("interview_opening") and t.get("delivery") == "complete"), None)
        introduction_answer = next((t for t in answers if opening_turn and s["turns"].index(t) > s["turns"].index(opening_turn) and not dialogue_request_kind(t["text"])), None)
        topic_answers = [t for t in answers if t is not introduction_answer]
        topic_position = dialogue_topic_position(topic_answers)
        objective = objectives[min(topic_position//2, len(objectives)-1)]
        # The application selects a bounded topic; the provider words the next
        # question. Topic progression is not evidence that a criterion is met.
        topic_index = topic_position//2
        claim_index = (topic_index//len(objectives)) % len(s["claims"])
        current_claim = {"claim_index": claim_index, **s["claims"][claim_index]}
        context = {"role": role["title"], "experience": s["experience"], "confirmed_claims": [{k: v for k, v in claim.items() if v and (k != "contribution" or v != claim.get("source_bullet"))} for claim in s["claims"]], "confirmed_context": s["context"][:16000], "target_job": s["job_text"], "stage": s["stage"], "objective": objective, "allowed_action": "adaptive_follow_up" if answers else "open_current_objective", "disclosed_scenario": public_scenario(session_scenario(s), s["revealed"]), "support_level": s["support_level"], "questions_already_asked": [t["text"] for t in s["turns"] if t["role"] == "assistant"][-16:]}
        context["candidate_selected_practice_objective"] = s["practice_objective"]
        context["current_claim"] = current_claim
        context["topic_progression_note"] = "Two substantive responses or an explicit question skip permit a topic transition; clarification and uncertainty preserve the topic budget. These rules do not establish correctness or resolved competence. Use the latest answer to clarify or follow up within this topic."
        if s["stage"] == "RESUME_ROLE_DIALOGUE":
            context["objective"] = objectives[topic_index % len(objectives)]
            context["allowed_action"] = "transition" if answers and topic_position and topic_position%2 == 0 else "adaptive_follow_up" if answers else "open_current_objective"
        elif s["stage"] == "CODING":
            context["coding_problem"] = session_coding(s)
            context["coding_language"] = s["language"]
            context["objective"] = "Discuss the candidate's approach, complexity, and verification against the supplied authored contract without supplying a solution."
            context["allowed_action"] = "ask_about_coding_approach"
        elif s["stage"] in {"BASELINE_INCIDENT", "TRANSFER"}:
            context["objective"] = "Ask the candidate to explain or investigate the disclosed synthetic facts; keep conclusions provisional and do not reveal hidden facts."
            context["allowed_action"] = "ask_about_disclosed_evidence"
        elif s["stage"] == "REVIEW":
            context["objective"] = "Explain that technical assessment is unavailable and invite one candidate-selected practice objective."
            context["allowed_action"] = "request_candidate_practice_objective"
        if introduction:
            if not answers and not any(t["role"] == "assistant" and t.get("delivery") == "complete" for t in s["turns"]):
                context["allowed_action"] = "greet_and_invite_introduction"
                context["objective"] = "Welcome the candidate warmly, briefly explain this is a practice interview, then ask them to tell you about themselves and the work they would like to discuss. Do not ask a technical question yet."
            elif introduction_answer is not None and answers[-1] is introduction_answer:
                context["allowed_action"] = "acknowledge_introduction_and_begin"
                context["opening_instruction"] = "Briefly acknowledge a specific detail from the candidate's introduction without evaluating it, then ask one grounded opening question about the current claim and role objective."
        if s.get("_methodology_version") == 2 and s["stage"] == "RESUME_ROLE_DIALOGUE" and context["allowed_action"] != "greet_and_invite_introduction":
            plan = interview_plan(s)
            context.update(interview_phase=plan["phase"], objective=plan["objective"], current_claim=plan["claim"], allowed_action=("acknowledge_introduction_and_begin" if context["allowed_action"] == "acknowledge_introduction_and_begin" else plan["action"]))
        if s.get("_methodology_version") == 2 and s["stage"] == "REVIEW":
            context["allowed_action"] = "invite_practice_review"
            context["objective"] = "Explain that a provisional AI practice rating and answer feedback will appear in View report after completion. Invite one question about their approach; do not invent a score in dialogue."
        events = self.store.events(s["id"])
        stage_events = [event for event in events if event["stage"] == s["stage"]]
        reasoning = [event for event in stage_events if event["kind"] in {"hypothesis", "conclusion", "evidence", "hint", "practice_objective"}]
        context["confirmed_reasoning_timeline"] = [
            {"event_id": event["id"], "kind": event["kind"], "text": event.get("text", "")[:2000], "card_id": event.get("card_id")}
            for event in reasoning[-16:]
        ]
        # Extractive memory retains provenance without inventing answered points.
        # Corrected utterance text is authoritative; original audio is kept separately.
        answer_events = statement_sources(events)
        context["grounded_recent_answer_summary"] = [
            {"event_id": answer_events[(turn["id"],turn["version"])]["id"], "utterance_id": turn["id"], "source_version": turn["version"], "excerpt": turn["text"][:800]}
            for turn in answers[-3:] if (turn["id"],turn["version"]) in answer_events
            and answer_events[(turn["id"],turn["version"])].get("text") == turn["text"]
        ]
        context["conversation_progress"] = conversation_progress(s["turns"], events)[-4:]
        context["grounded_dialogue_memory"] = memory_context(s)
        if answers and context["allowed_action"] not in {"request_candidate_practice_objective", "guided_practice_for_selected_objective"}:
            latest = answers[-1]
            request_kind = dialogue_request_kind(latest["text"])
            if request_kind:
                source = answer_events.get((latest["id"], latest["version"]))
                if source and source.get("text") == latest["text"]:
                    context["candidate_request"] = {"event_id": source["id"], "utterance_id": latest["id"],
                        "source_version": latest["version"], "text": latest["text"],
                        "kind": request_kind}
                    context["allowed_action"] = ("transition" if s["stage"] == "RESUME_ROLE_DIALOGUE" else "offer_explicit_stage_skip") if request_kind == "skip_question" else "rephrase_current_question" if request_kind == "clarification" else "offer_narrower_question_or_skip"
                    if request_kind == "repeat":
                        context["allowed_action"] = "repeat_current_question_locally"
                    # Keep the actual last completed question, rather than a
                    # topic scheduled by the count of responses. No correctness
                    # inference follows from a request for help or uncertainty.
                    question = next((turn for turn in reversed(s["turns"][:s["turns"].index(latest)])
                                     if turn["role"] == "assistant" and turn.get("stage") == s["stage"]
                                     and turn.get("delivery") == "complete"), None)
                    context["question_to_clarify"] = {"turn_id": question["id"], "text": question["text"]} if question else None
        # Only disclosed cards enter live context. No private references or hidden test outputs.
        if context["disclosed_scenario"]:
            context["disclosed_scenario"].pop("available_cards", None)
        previous_question = next((turn for turn in reversed(s["turns"]) if turn["role"] == "assistant" and turn.get("delivery") == "complete"), None)
        previous_answer = next((turn for turn in reversed(s["turns"]) if turn["role"] == "user"), None)
        entering_stage = previous_question is not None and previous_question["stage"] != s["stage"]
        if entering_stage or context["allowed_action"] == "transition":
            context["conversation_transition"] = {
                "from_stage": previous_question["stage"] if previous_question else None,
                "to_stage": s["stage"],
                "previous_question": previous_question["text"] if previous_question else None,
                "latest_answer": previous_answer["text"] if previous_answer else None,
                "separate_exercise": entering_stage and s["stage"] in {"BASELINE_INCIDENT", "CODING", "COACHED_RETRY", "TRANSFER"},
            }
        system = session_prompt(s, "live_interviewer_v1.md")
        system += "\nSound like a considerate human interviewer: greet before requesting an introduction, listen to the response, and connect the next question to a specific detail when available. Avoid repetitive praise, checklist narration, and abrupt question dumps. Follow the supplied opening action before technical objectives."
        system += "\nNever announce the interview has ended, thank the candidate for completing it, or stop asking questions unless the application stage is REPORT or COMPLETED. Only the application advances stages. Never assume constraints, scale, ownership, technologies, outcomes, or correctness not supplied. Ask a clarification or label an example explicitly hypothetical. Each response contains one focused question, not a checklist of several questions. Avoid 'next objective' and repetitive praise. Start from what they actually built or did; probe their own contribution, tradeoffs, a concrete example, and how they checked it. For role fundamentals, ask practical questions at the supplied experience level and do not pretend hypothetical facts belong to their project. Do not reveal a model answer during the interview; keep technical verification and coaching for the separate practice review."
        system += "\nApplication policy: do not alter stages, call tools, rate competence, or diagnose weaknesses. Do not repeat questions already answered. Topic progression is coverage scheduling, not a finding that an answer is correct. For review, follow the supplied review objective; any separate practice score is provisional and uncalibrated."
        system += "\nFor transition, ask one concise question about the supplied next objective in this same response. A transition is within the current stage; never return only a statement such as 'let us move on', and never claim the application advanced a stage."
        system += "\nWhen conversation_transition is supplied, bridge the switch before the question: briefly acknowledge a concrete detail from the latest answer without judging correctness, then explain the new focus in one short sentence. For a new role topic, say you are moving from their experience to a general role example. For a separate_exercise, explicitly introduce it as a separate hypothetical exercise, never part of their hackathon or past work. Connect topics only when the supplied facts support the connection; do not invent one. Then ask exactly one focused question in the same response. Avoid repetitive thanks, praise, or abrupt topic resets."
        system += "\nFor rephrase_current_question, explain or reword question_to_clarify neutrally without supplying its answer or switching topics. For offer_narrower_question_or_skip, acknowledge uncertainty without judgment and offer one narrower question or the explicit skip control. These requests never establish competence or resolve a technical point."
        system += "\nA skip_question request in resume dialogue permits moving to the supplied next objective without judging the skipped answer. For offer_explicit_stage_skip, point to the explicit stage-skip control; never change stages or disclose solutions based on spoken text. Clarification and uncertainty do not count as substantive topic responses."
        system += "\nConversation progress statuses describe recorded conversational actions only. needs_clarification, repeat_requested, uncertainty_expressed, and skipped do not mean a substantive answer was given. Use the linked response and question when addressing an open point; do not treat reply_recorded as proof of technical correctness or semantic resolution."
        system += "\nGrounded dialogue memory groups conversationally addressed points and open details using quoted sources. Avoid asking for information already supplied, including paraphrased questions; follow up on a specific remaining detail instead. This optional memory is provisional, never a correctness assessment. The latest answer and recent transcript override older coverage. Stay within the application's current objective and allowed action."
        if s["stage"] == "COACHED_RETRY":
            system += "\n"+session_prompt(s, "coach_v1.md")
            context["allowed_action"] = "guided_practice_for_selected_objective" if s["practice_objective"] else "request_candidate_practice_objective"
        return [{"role": "system", "content": system}, {"role": "user", "content": "UNTRUSTED CONTEXT DATA:\n"+encode(context)}, *[{"role": t["role"], "content": t["text"]} for t in s["turns"][-10:]]]
