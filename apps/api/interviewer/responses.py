"""Public API contracts. Unknown stored/provider fields never become public fields.

Request models reject unexpected input; these output models deliberately filter
unexpected fields. Invalid declared values fail response validation instead of
being coerced into apparently valid evidence. Private snapshots and idempotency
metadata have no corresponding output fields.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from .dialogue_memory import AnsweredPoint, OpenDetail


Provider = Literal["groq", "openrouter", "codex"]
Language = Literal["python", "cpp"]
Stage = Literal["RESUME_ROLE_DIALOGUE", "BASELINE_INCIDENT", "CODING", "REVIEW", "COACHED_RETRY", "TRANSFER", "REPORT", "COMPLETED"]
Support = Literal["independent", "coached"]


class PublicModel(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True, allow_inf_nan=False)


class Auth(PublicModel):
    authenticated: bool
    csrf_token: str | None = None


class Health(PublicModel):
    status: Literal["ok"]


class ProviderConfig(PublicModel):
    live_model: str
    assessment_model: str
    live_route: str = ""
    assessment_route: str = ""
    paid_opt_in: bool


class ProviderSettings(PublicModel):
    groq: ProviderConfig
    openrouter: ProviderConfig
    codex: ProviderConfig


class Settings(PublicModel):
    provider: Provider
    revision: int
    providers: ProviderSettings


class Snapshot(PublicModel):
    provider: Provider
    config: ProviderConfig
    consent_version: str | None = None
    settings_revision: int | None = None
    captured_at: float | None = None


class VoiceReadiness(PublicModel):
    ready: bool
    detail: str
    status: str | None = None
    missing: list[str] = Field(default_factory=list)
    warmup_seconds: float | None = None


class ProviderReadiness(PublicModel):
    status: Literal["configured", "missing"]
    validated: bool


class ProviderStatuses(PublicModel):
    groq: ProviderReadiness
    openrouter: ProviderReadiness
    codex: ProviderReadiness


class RunnerReadiness(PublicModel):
    configured: bool


class AssessmentReadiness(PublicModel):
    automatic_ratings: Literal[False]
    reason: str


class Readiness(PublicModel):
    voice: VoiceReadiness
    providers: ProviderStatuses
    runner: RunnerReadiness
    assessment: AssessmentReadiness


class Level(PublicModel):
    expectations: str
    competencies: list[str]
    question_objectives: list[str]
    coding_problem: str


class Levels(PublicModel):
    junior: Level
    intermediate: Level


class Role(PublicModel):
    schema_version: int
    role_id: str
    title: str
    levels: Levels
    reasoning_families: list[str]
    rubric_refs: list[str]


class Roles(PublicModel):
    roles: list[Role]


class Pricing(PublicModel):
    prompt: str | float | int | None = None
    completion: str | float | int | None = None
    request: str | float | int | None = None
    image: str | float | int | None = None
    audio: str | float | int | None = None
    audio_output: str | float | int | None = None
    web_search: str | float | int | None = None
    internal_reasoning: str | float | int | None = None
    input_cache_read: str | float | int | None = None
    input_cache_write: str | float | int | None = None


class Model(PublicModel):
    id: str
    name: str | None = None
    pricing: Pricing | None = None
    supported_parameters: list[str] = Field(default_factory=list)
    structured_outputs: bool | None = None


class Catalog(PublicModel):
    models: list[Model]
    fetched_at: float
    pricing_note: str


class Endpoint(PublicModel):
    provider_name: str | None = None
    tag: str | None = None
    provider_tag: str | None = None
    pricing: Pricing | None = None
    supported_parameters: list[str] = Field(default_factory=list)


class EndpointData(PublicModel):
    endpoints: list[Endpoint]


class Endpoints(PublicModel):
    data: EndpointData


class ProviderTest(PublicModel):
    status: Literal["validated"]
    provider: Provider
    validated_at: float
    live: Literal[True]
    structured_assessment: Literal[True]


class Claim(PublicModel):
    source_bullet: str
    page: int | None = None
    offset: int
    project: str = ""
    contribution: str = ""
    technology: str = ""
    result: str = ""
    measurement: str = ""
    confidentiality: str = ""


class ResumePage(PublicModel):
    page: int | None
    text: str


class Resume(PublicModel):
    id: str
    text: str
    context: str
    pages: list[ResumePage]
    claims: list[Claim]
    redaction_note: str
    created: float


class RemovedResume(PublicModel):
    deleted: Literal[True]


class ProviderError(PublicModel):
    code: str
    message: str
    retry_after: str | None = None


class ValidationIssue(PublicModel):
    loc: list[str | int]
    msg: str
    type: str


class Error(PublicModel):
    detail: str | list[ValidationIssue]
    error: ProviderError | None = None


class Timing(PublicModel):
    clock: str | None = None
    request_started: float | None = None
    request_kind: str | None = None
    first_usable_content: float | None = None
    endpoint_decision: float | None = None
    speech_end_estimate: float | None = None
    speech_end_basis: str | None = None
    configured_silence_seconds: float | None = None
    stt_started: float | None = None
    stt_completed: float | None = None
    first_tts_clause_server: float | None = None
    first_tts_chunk_server: float | None = None
    first_audio_admitted_server: float | None = None
    first_text_received_client_ms: float | None = None
    first_text_displayed_client_ms: float | None = None
    first_playback_client_ms: float | None = None
    first_text_received_receipt_server: float | None = None
    first_text_displayed_receipt_server: float | None = None
    first_playback_receipt_server: float | None = None


class AudioInterval(PublicModel):
    start: float
    end: float


class Word(AudioInterval):
    text: str


class SpeechMetadata(PublicModel):
    source: str
    language: str | None = None
    received_at: float | None = None
    final: bool | None = None
    audio_duration_seconds: float | None = None
    words: list[Word] = Field(default_factory=list)
    word_timestamp_basis: str | None = None
    timing: Timing | None = None
    audio_interval: AudioInterval | None = None
    session_words: list[Word] = Field(default_factory=list)
    session_timestamp_basis: str | None = None
    clock_note: str | None = None
    recording_artifact: str | None = None
    held_segments: list["SpeechMetadata"] = Field(default_factory=list)


class SpeechDelivery(PublicModel):
    status: Literal["buffering", "playing", "estimated_complete", "interrupted", "closed", "unavailable"]
    generation_id: str
    generated_text_chars: int
    displayed_text_chars: int
    generated_audio_ms: float
    estimated_played_ms: float
    peak_pending_audio_ms: float
    timing: Timing
    delivery_note: str
    turn_id: str


class TextVersion(PublicModel):
    version: int
    text: str
    kind: Literal["original", "candidate_correction"]


class Turn(PublicModel):
    id: str
    role: Literal["user", "assistant"]
    text: str
    version: int
    versions: list[TextVersion] = Field(default_factory=list)
    stage: Stage
    support_level: Support | None = None
    delivery: Literal["generating", "complete", "interrupted", "incomplete"]
    created: float
    generation_id: str | None = None
    input_source: Literal["typed", "local_speech"] | None = None
    speech_metadata: SpeechMetadata | None = None
    speech_delivery: SpeechDelivery | None = None
    timing: Timing | None = None


class Usage(PublicModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    prompt_time: float | None = None
    completion_time: float | None = None
    total_time: float | None = None
    queue_time: float | None = None


class Event(PublicModel):
    id: str
    kind: Literal["consent", "claims_confirmed", "answer", "transcript_correction", "candidate_correction", "finding_dispute", "voice_delivery", "provider_paused", "generation_finished", "dialogue_memory_finished", "submission", "submission_cancelled", "recovery", "disconnect", "pause", "resume", "stop", "keep_thinking", "repeat", "retry", "advance", "skip", "end", "evidence", "hypothesis", "conclusion", "hint", "practice_objective", "extend"]
    stage: Stage
    revision: int
    created: float
    text: str | None = None
    card_id: str | None = None
    from_stage: Stage | None = None
    cloud: bool | None = None
    record_audio: bool | None = None
    version: int | str | None = None
    provider: Provider | None = None
    retention: Literal["30_days", "delete_on_close"] | None = None
    claims: list[Claim] | None = None
    utterance_id: str | None = None
    visible_cards: list[str] | None = None
    support_level: Support | None = None
    input_source: Literal["typed", "local_speech"] | None = None
    reason: str | None = None
    code: str | None = None
    interrupted_generation_id: str | None = None
    generation_id: str | None = None
    turn_id: str | None = None
    delivery: Literal["complete", "interrupted", "incomplete"] | None = None
    model: str | None = None
    route: str | None = None
    usage: Usage | None = None
    first_content_seconds: float | None = None
    request_seconds: float | None = None
    correction_kind: str | None = None
    finding_id: str | None = None
    submission_id: str | None = None
    language: Language | None = None
    mode: Literal["run", "submit"] | None = None
    status: str | None = None
    generated_text_chars: int | None = None
    displayed_text_chars: int | None = None
    generated_audio_ms: float | None = None
    estimated_played_ms: float | None = None
    peak_pending_audio_ms: float | None = None
    timing: Timing | None = None
    delivery_note: str | None = None


class Fact(PublicModel):
    fact_id: str
    text: str


class AvailableCard(PublicModel):
    card_id: str
    title: str


class RevealedCard(PublicModel):
    card_id: str
    text: str
    source: str
    requires: list[str] | str | None = None


class Coaching(PublicModel):
    visible_before_attempt: bool
    lesson: str
    guided_steps: list[str]
    assistance_level: str


class Scenario(PublicModel):
    scenario_id: str
    schema_version: int
    title: str
    initial_facts: list[Fact]
    available_cards: list[AvailableCard]
    revealed_cards: list[RevealedCard]
    general_role_exercise: bool
    coaching: Coaching | None = None


class CodingContract(PublicModel):
    language: str
    stdin: str
    stdout: str
    complexity_expectation: str
    build: str


class PublicTest(PublicModel):
    stdin: str
    stdout: str


class CodingProblem(PublicModel):
    schema_version: int
    problem_id: str
    title: str
    statement: str
    contract: CodingContract
    public_tests: list[PublicTest]


class Span(PublicModel):
    start: int
    end: int


class StatementReference(PublicModel):
    id: str
    version: int
    premise: str


class Dispute(PublicModel):
    id: str
    text: str
    created: float


class Finding(PublicModel):
    id: str
    session_id: str
    criterion: Literal["candidate_statement"]
    status: Literal["reference_only", "stale", "disputed"]
    rating: None
    utterance_id: str
    source_version: int
    source_event_id: str
    quote: str
    evidence: str
    quote_span: Span
    audio_interval: AudioInterval | None = None
    reference: StatementReference
    inference: str
    coaching: str
    support_level: Support
    assessment_version: int
    disputes: list[Dispute] = Field(default_factory=list)


class Provenance(PublicModel):
    status: Literal["captured", "legacy_unpinned"]
    digest: str | None


class Session(PublicModel):
    id: str
    revision: int
    stage: Stage
    paused: bool
    generation_id: str
    turn_id: str
    created: float
    expires: float
    snapshot: Snapshot
    role_version: int
    family: str
    turns: list[Turn]
    revealed: list[str]
    support_level: Support
    coding_skipped: bool
    findings: list[Finding]
    assessment_version: int
    practice_objective: str
    last_error: ProviderError | None
    context: str
    claims: list[Claim]
    role: Literal["backend", "frontend", "fullstack"]
    experience: Literal["junior", "intermediate"]
    language: Language
    duration_minutes: int
    cloud_consent: bool
    record_audio: bool
    retention: Literal["30_days", "delete_on_close"]
    job_text: str
    content_provenance: Provenance
    scenario: Scenario | None
    coding_problem: CodingProblem
    events: list[Event]
    duration_reached: bool
    draft_answer: str | None = None


class HistoryEntry(PublicModel):
    id: str
    role: str
    experience: str
    stage: Stage
    created: float
    expires: float
    revision: int
    paused: bool
    provider: Provider


class History(PublicModel):
    sessions: list[HistoryEntry]


class Outcome(PublicModel):
    kind: Literal["passed", "wrong_answer", "runtime_error", "timeout", "output_limit", "infrastructure_error"]
    stdout: str | None = None
    stderr: str | None = None
    expected_stdout: str | None = None
    exit_code: int | None = None


class TestSummary(PublicModel):
    passed: int = Field(ge=0)
    total: int = Field(ge=0)

    @model_validator(mode="after")
    def consistent_counts(self):
        if self.passed > self.total:
            raise ValueError("Passed count exceeds attempted count")
        return self


class CompileResult(PublicModel):
    exit_code: int | None = None
    stdout: str
    stderr: str


class ExecutionResult(PublicModel):
    kind: Literal["passed", "wrong_answer", "compile_error", "runtime_error", "timeout", "output_limit", "infrastructure_error", "cancelled"]
    public: list[Outcome] = Field(default_factory=list)
    public_summary: TestSummary | None = None
    hidden: TestSummary | None = None
    compile: CompileResult | None = None
    error: str | None = None
    message: str | None = None


class Execution(PublicModel):
    id: str
    status: Literal["queued", "running", "complete", "cancelled", "infrastructure_error"]
    result: ExecutionResult | None = None


class Submission(PublicModel):
    id: str
    session_id: str
    problem_id: str
    language: Language
    source: str
    mode: Literal["run", "submit"]
    status: Literal["queued", "running", "complete", "cancelled", "infrastructure_error", "infrastructure_failure"]
    created: float
    content_digest: str | None = None
    detail: str | None = None
    execution: Execution | None = None


class SubmissionMutation(PublicModel):
    session: Session
    submission: Submission


class Delete(PublicModel):
    deleted: bool
    cleanup_pending: bool
    session_id: str
    cloud_deletion: Literal[False]
    note: str


class Criterion(PublicModel):
    criterion_id: str
    name: str
    rubric_version: int
    rating: None
    status: Literal["not_observed", "insufficient_evidence"]
    source_utterance_ids: list[str]
    source_event_ids: list[str]
    explanation: str


class CausalReference(PublicModel):
    supported_cause: str
    facts_required: list[str]
    non_supporting_fact: str | None = None
    supporting_fact: str | None = None
    limits: list[str]
    verification_examples: list[str]


class ReferenceReview(PublicModel):
    schema_version: int
    reference_id: str
    scenario_id: str
    causal_reference: CausalReference
    criterion_anchors: dict[str, dict[Literal["0", "1", "2", "3"], str]]


class RecordedReply(PublicModel):
    utterance_id: str
    source_version: int
    event_id: str
    excerpt: str


class ConversationPoint(PublicModel):
    question_turn_id: str
    stage: Stage
    question: str
    repeat_turn_ids: list[str]
    responses: list[RecordedReply]
    status: Literal["reply_recorded", "no_reply_recorded", "repeat_requested", "needs_clarification", "uncertainty_expressed", "skipped"]
    interpretation: str


class MemoryQuestion(PublicModel):
    id: str
    stage: Stage
    text: str


class ConversationMemory(PublicModel):
    status: Literal["unavailable", "provisional_conversational_coverage"]
    answered_points: list[AnsweredPoint]
    unresolved_details: list[OpenDetail]
    questions: list[MemoryQuestion] = Field(default_factory=list)
    note: str | None = None


class SupportLevels(PublicModel):
    baseline: Literal["independent"]
    coached: Literal["coached"]
    fresh: Literal["independent"]


class PracticeAnswer(PublicModel):
    utterance_id: str
    source_version: int
    quote: str
    score: int | None = Field(ge=0, le=4)
    verdict: Literal["correct", "partial", "incorrect", "not_assessable"]
    reason: str
    improvement: str


class PracticeReview(PublicModel):
    status: Literal["current", "stale"]
    model: str
    generated_at: float
    source_revision: int
    overall_score: float | None = Field(ge=0, le=100)
    assessed_answers: int
    summary: str
    answers: list[PracticeAnswer]
    limitations: list[str]


class Report(PublicModel):
    practice_review: PracticeReview | None = None
    session_id: str
    revision: int
    assessment_version: int
    status: Literal["partial"]
    mode: Literal["authored_reference_review"]
    automatic_ratings_enabled: Literal[False]
    calibration_limitation: str
    claims: list[Claim]
    topics_tested: list[Stage]
    timeline: list[Event]
    turns: list[Turn]
    findings: list[Finding]
    criterion_coverage: list[Criterion]
    excluded_findings: int
    technical_assessment_status: Literal["unavailable"]
    code_review_status: Literal["unavailable"]
    reference_review: list[ReferenceReview]
    coding_outcomes: list[Submission]
    support_levels: SupportLevels
    conversation_progress: list[ConversationPoint]
    conversation_memory: ConversationMemory
    unresolved_questions: list[str]
    next_practice_action: str
    snapshot: Snapshot


class AnswerOffer(PublicModel):
    sdp: str
    type: Literal["answer"]
    generation_id: str
    session_id: str


class StreamEvent(PublicModel):
    type: Literal["connected", "resync", "state", "delta", "complete", "error", "voice_error", "execution", "deleted"]
    session_id: str
    generation_id: str | None = None
    turn_id: str | None = None
    revision: int | None = None
    state: str | None = None
    text: str | None = None
    text_so_far: str | None = None
    error: ProviderError | None = None
    message: str | None = None
    submission_id: str | None = None
    status: str | None = None
