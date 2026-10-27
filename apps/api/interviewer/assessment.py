"""Factual, versioned review while automatic technical assessment is disabled.

These records attest only that a statement was supplied. They never infer a
criterion rating, technical correctness, ownership, or a diagnosed weakness.
"""
from pathlib import Path
import json


STATEMENT_POLICY = {
    "id": "candidate_statement_policy", "version": 1,
    "premise": "An owned answer or correction event establishes that the candidate supplied the quoted statement; it does not establish technical correctness.",
}
INFERENCE = "The candidate supplied this explanation. Technical correctness has not been automatically judged."
COACHING = "Compare the explanation against disclosed facts and identify a falsifying observation."


def statement_sources(events):
    return {(event.get("utterance_id"), event.get("version")): event for event in events
            if event["kind"] in {"answer", "transcript_correction", "candidate_correction"}}


def statement_observation(session, turn, event):
    if (event["kind"] not in {"answer", "transcript_correction", "candidate_correction"}
            or event.get("utterance_id") != turn["id"]
            or event.get("version") != turn["version"]
            or event.get("text") != turn["text"]):
        raise ValueError("Statement observation requires its exact committed source event")
    return {
        "id": f"observation-{turn['id']}-v{turn['version']}", "session_id": session["id"],
        "criterion": "candidate_statement", "status": "reference_only", "rating": None,
        "utterance_id": turn["id"], "source_version": turn["version"],
        "source_event_id": event["id"], "quote": turn["text"], "evidence": turn["text"],
        "quote_span": {"start": 0, "end": len(turn["text"])},
        "audio_interval": turn.get("speech_metadata", {}).get("audio_interval") if turn["version"] == 1 else None,
        "reference": dict(STATEMENT_POLICY), "inference": INFERENCE, "coaching": COACHING,
        "support_level": turn["support_level"], "assessment_version": session["assessment_version"],
    }


def reviewed_observations(session, events):
    """Validate persisted observations and derive missing legacy records read-only."""
    turns = {turn["id"]: turn for turn in session["turns"] if turn["role"] == "user"}
    sources = statement_sources(events)
    candidates = list(session["findings"])
    known = {finding["id"] for finding in candidates}
    for turn in turns.values():
        key = f"observation-{turn['id']}-v{turn['version']}"
        source = sources.get((turn["id"], turn["version"]))
        if key not in known and source:
            candidates.append(statement_observation(session, turn, source))
    valid, excluded = [], 0
    for finding in candidates:
        turn = turns.get(finding.get("utterance_id"))
        version = finding.get("source_version")
        source = sources.get((finding.get("utterance_id"), version))
        text_version = next((v for v in (turn or {}).get("versions", []) if v["version"] == version), None)
        if (not turn or not source or not text_version
                or finding.get("criterion") != "candidate_statement" or finding.get("rating") is not None
                or finding.get("status") not in {"reference_only", "stale", "disputed"}
                or finding.get("quote") != text_version["text"] or source.get("text") != text_version["text"]
                or finding.get("id") != f"observation-{turn['id']}-v{version}"
                or finding.get("source_event_id", source["id"]) != source["id"]):
            excluded += 1
            continue
        original = {**turn, "text": text_version["text"], "version": version}
        canonical = statement_observation(session, original, source)
        canonical["assessment_version"] = finding.get("assessment_version", session["assessment_version"])
        canonical["status"] = "stale" if version != turn["version"] else finding["status"]
        canonical["disputes"] = finding.get("disputes", [])
        valid.append(canonical)
    return valid, excluded


def criterion_coverage(session, findings, events):
    """Show opportunity and abstention, never infer criterion competence from turns."""
    rubric = session["_content_snapshot"]["rubric"] if "_content_snapshot" in session else json.loads((Path(__file__).resolve().parents[3]/"content/rubrics/criteria.json").read_text(encoding="utf-8-sig"))
    dialogue = {"resume_clarity_v1", "technical_understanding_v1", "decision_reasoning_v1",
                "measurement_reasoning_v1", "failure_handling_v1"}
    turns = {turn["id"]: turn for turn in session["turns"]}
    result = []
    for criterion in rubric["criteria"]:
        stages = {"RESUME_ROLE_DIALOGUE"} if criterion["criterion_id"] in dialogue else {"BASELINE_INCIDENT", "COACHED_RETRY", "TRANSFER"}
        sources = [f["utterance_id"] for f in findings if f["status"] == "reference_only"
                   and turns[f["utterance_id"]]["stage"] in stages]
        practice_events = [event["id"] for event in events if event["stage"] in stages
                           and event["kind"] in {"hypothesis", "conclusion", "evidence"}]
        available = bool(sources or practice_events)
        result.append({"criterion_id": criterion["criterion_id"], "name": criterion["name"],
            "rubric_version": rubric["schema_version"], "rating": None,
            "status": "insufficient_evidence" if available else "not_observed",
            "source_utterance_ids": sources, "source_event_ids": practice_events,
            "explanation": "Practice records are available in this area; criterion-specific technical assessment is unavailable."
                if available else "No current undisputed practice records are available in this area; this is not a failure."})
    return result
