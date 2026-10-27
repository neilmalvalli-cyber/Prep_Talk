# Final build contract: AI Voice Mock Interviewer

## Purpose and authority

Build a complete, runnable voice mock interviewer that conducts a genuine back-and-forth interview based on the candidate's confirmed resume and selected role. The system must listen to each answer, ask relevant follow-ups, support practical reasoning and coding exercises, and produce evidence-linked feedback that the candidate can correct.

This document consolidates `plan.md` and `AI Voice Mock Interviewer - Revised Plan.md` with the owner's latest requirements. Those documents are design references, not commands to execute. This contract supersedes their conflicting product choices, including the Groq-only restriction and phased delivery schedules. Higher-priority system instructions and subsequent explicit owner requests remain authoritative.

The current task creates only this document. Implementation begins only when the owner requests the build. At that point, deliver the entire contract as one integrated final build. Do not turn it into separately approved phases, an MVP-first proposal, a week-by-week roadmap, or a collection of incomplete demos. Internal task ordering is an implementation detail; all required capabilities must work together before declaring completion. Report real blockers without silently removing requirements.

Use existing repository code and conventions where they fit. Inspect actual files before assuming anything is implemented. Do not treat planning text, historical agent claims, or filenames as evidence of working software.

## Final product scope

The primary experience is a personalized interview, not a static question list, resume scoring form, or caching exercise presented to every candidate. Resume context, selected role, experience level, and the candidate's latest answer must influence questioning throughout the interview.

The complete product includes:

- Resume upload, local extraction, candidate review, and confirmation of project claims.
- Role selection and visible interview objectives before starting.
- Bidirectional voice interaction, incremental interviewer text and audio, interruption, and a fully usable typed path.
- Adaptive resume discussion, role-relevant technical questions, and explicit clarification when an answer or transcript is ambiguous.
- Authored reasoning exercises with controlled evidence disclosure, a reasoning revision timeline, coaching, and an uncoached fresh variant.
- Python and C++ coding rounds with an editor and isolated execution on the dedicated runner host.
- Evidence-linked criterion feedback, transcript correction, finding disputes, assessment revision, and local history.
- Settings that switch between Groq and OpenRouter. Groq is the initial default.
- Local speech processing and persistence, explicit cloud-processing disclosure, separate recording consent, retention controls, and deletion.
- Reproducible installation, configuration, runtime diagnostics, and focused acceptance evidence.

Use English initially. Support one active interview and one runner job at a time. Candidate-controlled history and sharing are sufficient; do not add institution dashboards, rankings, recruiting decisions, or classroom concurrency.

Do not add arbitrary repository execution, custom build commands, automatic incident generation, voice cloning, emotion detection, confidence detection, hiring/readiness scores, or claimed fraud detection. These are outside the final scope, not promised later milestones.

## Hero page and visual experience

### Landing page

Provide a polished public-facing landing page at `/`, leading directly into interview setup. It must communicate resume-based, role-specific conversation before discussing secondary features. Treat this page and the interview screen as one visual system.

Use this initial content:

- Headline: “Practice the interview your resume starts.”
- Supporting copy: “Choose your role, bring your resume, and talk through real follow-up questions. Get feedback tied to what you actually said.”
- Primary action: “Prepare my interview”, opening resume and role setup without requesting microphone access or starting cloud processing.
- Secondary action: “See an example”, opening an accessible, clearly labeled sample exchange using synthetic resume content.
- Brief privacy note: “Speech stays on this device. Selected text and code go to your chosen AI provider.” Link to the fuller data-sharing explanation.

Use a spacious split hero on desktop: left-aligned headline, supporting copy, and actions on one side; the glowing interviewer sphere and a short sample question on the other. On mobile, stack the copy, actions, and a smaller sphere without horizontal scrolling. Keep the primary action visible in the initial viewport on common laptop sizes. Navigation contains the product name, How it works, Settings, and My interviews; protect private history through the existing owner-access mechanism.

Make the sphere the distinctive visual rather than surrounding it with decorative gradients or a grid of generic feature cards. Beneath the hero, show a compact actual workflow: confirm your resume and role, answer adaptive follow-ups, and review evidence-linked feedback. Include one synthetic example showing how different answers lead to different follow-up questions. Add a concise privacy and control section explaining typed fallback, interruption, provider selection, and optional recording.

Do not invent testimonials, usage counts, employer logos, success rates, or hiring promises. The example exchange must never be presented as a real user's session. It needs no model call. If example audio is included, playback requires an explicit user action and must provide a transcript.

### Visual direction

Use a calm midnight-blue interview environment with a luminous pearl/cyan sphere inspired by the soft, fluid orb of ChatGPT voice chat. The avatar is an abstract glowing sphere, not a face, human portrait, robot, or static chat icon. Use original rendering and product identity; do not add OpenAI branding or imply affiliation.

Initial design tokens:

| Token | Value and purpose |
|---|---|
| Canvas | `#101D35`, deep blue background |
| Surface | `#192B48`, controls and supporting panels |
| Primary text | `#F3F7FC`, readable headings and body |
| Secondary text | `#B7C7DD`, supporting copy and labels |
| Sphere cyan | `#75DCEB`, illuminated edges and internal movement |
| Sphere pearl | `#EAFBFF`, soft luminous center and highlights |

Use locally bundled Manrope for interface text and headings, with a system sans-serif fallback. Keep headings in sentence case, body copy comfortably readable, and paragraphs under approximately 75 characters per line. Verify contrast for actual foreground/background combinations; palette choices do not replace accessibility checks. Keep glow out of text and focus indicators.

Render the sphere with a soft spherical silhouette, layered translucent light, subtle internal cloud-like movement, and a restrained outer halo. Preserve depth without sharp spikes, rapid flashes, excessive bloom, or constant large changes in size. Prefer browser-native rendering sufficient for this effect; do not add a 3D framework solely for the avatar. Provide a static gradient sphere if advanced rendering is unavailable.

### Interview screen and voice avatar

During the spoken interview, center the glowing sphere above the current question and a persistent plain-language status label. Keep selected role, elapsed time, and active provider visible but secondary. Place microphone, Done speaking, Keep thinking, Pause, typed answer, and End interview controls within easy reach below the conversation area. The sphere is an avatar, not an unlabeled control.

Keep transcript access available throughout. Desktop may use a side panel; mobile may use an accessible expandable panel. During evidence and coding tasks, reduce the sphere to a smaller visible presence so evidence cards or the editor receive the main workspace. Do not hide the active question, current voice state, or Stop control behind the editor.

Drive avatar state from the actual session and audio lifecycle, never from decorative timers that pretend the system is listening or speaking:

| State | Sphere behavior | Visible label |
|---|---|---|
| Ready | Gentle, low-amplitude ambient movement | “Ready when you are” |
| Listening | Soft halo responds to local microphone activity after permission | “Listening” |
| Processing | Slow internal light movement, distinct from audio-reactive motion | “Preparing a follow-up” |
| Speaking | Smooth pulse follows audio actually playing in the browser | “Interviewer speaking” |
| Keep thinking | Stable, quiet glow; no endpoint countdown pressure | “Take your time” |
| Paused | Motion stops and brightness reduces while remaining visible | “Interview paused” |
| Reconnecting | Restrained static appearance with textual recovery status | “Reconnecting” |
| Error or unavailable voice | Static sphere with nearby actionable explanation | Specific error plus recovery action |
| Completed | Settled glow with access to the report | “Interview complete” |

Speaking animation must follow playback activity rather than token arrival or queued synthesis. Listening animation may use a locally computed, smoothed audio level solely for visual feedback; do not retain it or use it for scoring. Mic-muted or unavailable states must never appear to be listening. On interruption, stop the speaking pulse when playback stops and transition to the actual new state. A text-only interview uses processing and ready states without simulating audio.

Respect `prefers-reduced-motion`: remove continuous rotation, pulsing, and morphing; retain a static sphere plus clear state text. Do not rely on color or animation alone. Mark the purely decorative sphere as hidden from assistive technology and expose state changes through a concise, appropriately paced status region. Avoid announcing every animation frame or streamed token.

Bound rendering cost, pause decorative rendering when the page is hidden, and release audio-analysis resources when the session ends. Sphere rendering must not delay streaming text, audio playback, or interruption handling. Keep the landing-page sphere decorative; it must never request microphone access, start recording, or make cloud calls.

## Candidate journey and interaction requirements

### Setup and resume confirmation

Accept text-based PDF and plain text resumes, plus pasted text as a recovery path. Extract locally. Do not require OCR or DOCX support. Reject unsupported, encrypted, malformed, or oversized files with an actionable explanation. Start with a 10 MiB upload limit, 20-page PDF limit, and 50,000-character extracted-text limit. Bound parsing time and memory; use generated storage names and never execute document content.

For an image-only PDF, explain that readable text is missing and offer paste/manual entry. Do not pretend extraction succeeded. Display extracted text for review before sending any selected content to a cloud model. Remove contact details and unrelated personal information from model context by default. Let the candidate edit the proposed context.

Represent each claim with its source bullet and page or text offset, project, contribution, technology or decision, claimed result, supplied measurement evidence, and confidentiality boundaries. Model-assisted extraction may suggest structure only after cloud consent; candidate confirmation establishes the interview context. Missing metrics generate questions, not invented achievements or automatic negative judgments.

Require selection of a role and experience level. Provide authored profiles for Backend Engineer, Frontend Engineer, and Full-stack Engineer, with junior/student and intermediate expectations. Each profile defines competencies, appropriate depth, question objectives, coding relevance, and rubric references. These are role profiles, not rigid scripts. The candidate may supply optional target-job text as untrusted context; it cannot override assessment or security policy.

Before Start, show the confirmed resume context, role, duration target, coding language, active provider and models, data-sharing disclosure, recording choice, and microphone/model readiness. Default to no retained audio. Allow a typed interview without microphone access. Reserve one session atomically so simultaneous starts cannot bypass the concurrency limit.

### Genuine back-and-forth dialogue

Ask one clear question at a time, normally at most 45 spoken words. Wait for a completed candidate response before continuing. The next question must relate to the latest answer, an unresolved point, or an explicit transition to a new role-relevant objective.

Track current claim, current objective, questions already asked, answered points, unresolved details, support level, and a bounded summary grounded in event IDs. Use recent turns directly. Preserve the complete transcript separately; a summary is never the sole evidence for assessment.

Application code chooses the permitted conversational action and topic boundaries. The live model can word an adaptive follow-up within those boundaries using the answer. Do not place separate planner and evaluator calls before every spoken response. Ordinary conversation must not require confirmation clicks after every answer. Explicit confirmations are required for assessment-critical claim changes, hypotheses, evidence requests, hints, submissions, and stage progression.

Use neutral clarification when the candidate's meaning is unclear. Accept “I don't know,” requests to repeat or rephrase, and requests to skip. Do not treat silence as an incorrect answer. Avoid repeating resolved questions. Allow an explicit extension or wrap-up when the duration target is reached; slow speech and accommodations must not silently reduce competence ratings.

Example behavior for the same confirmed caching claim:

- If a backend candidate says they used TTL only, ask how updates remain correct before expiry.
- If the candidate says they explicitly invalidated keys, ask how write and invalidation failures were handled.
- If a frontend candidate describes stale browser data, ask how client state or request caching was invalidated, without assuming Redis.
- If the candidate says they measured a 40% improvement, ask which latency statistic, workload, and baseline produced it.

These examples demonstrate branching expectations. Do not hard-code them as the complete interview. Never invent the candidate's stack, responsibilities, production traffic, or results.

### Reasoning exercises and role relevance

Keep synthetic tasks visibly separate from the candidate's real project. A synthetic exercise measures the demonstrated concept; it cannot verify past employment or ownership.

Use versioned authored scenario records. Each contains initial facts, public evidence cards, reveal rules, accepted alternative explanations, private causal references, criterion anchors, and a matched fresh variant. The interviewer receives only disclosed facts. Hidden references remain server-side and are available only to assessment.

Include the revised plan's caching family: baseline stale price caused by reader/invalidation key mismatch, a coached evidence-interpretation exercise, and a fresh stale-price case caused by replica lag while caching is bypassed. An aggregate cache-hit dashboard must not establish correctness of a particular request.

Also provide a role-appropriate frontend family covering stale UI data or asynchronous response ordering, with a coached exercise and a fresh variant requiring a different diagnosis. Full-stack profiles may select the appropriate family from confirmed context. When no family matches the resume, disclose that the selected exercise is a general role exercise. Never pretend a caching task describes an unrelated project.

Capture provisional explanation, requested diagnostic, revealed facts, revision or justified retention, conclusion, and verification plan. Accept multiple sensible investigation orders. Do not charge a diagnostic-request penalty. Hypothesis changes are valuable only when justified; retaining a hypothesis can be correct.

### Review, coaching, and completion

Finish the baseline and coding attempt before exposing relevant solutions. Review supported observations, teach one concrete reasoning gap, provide a guided exercise, and then conduct a fresh uncoached variant. Keep assisted and independent results separate. If assessment is unavailable, use an explicitly labeled authored reference review and a candidate-selected practice objective; do not invent a diagnosed weakness.

Display a report with confirmed resume claims, topics actually tested, reasoning timeline, coding outcomes, criterion findings, corrections/disputes, support levels, unresolved questions, and a concrete next practice action. Report improvement only as an observation within these attempts, not proof of durable learning.

## Architecture and ownership

Use React, TypeScript, and Vite for the client; Monaco for editing; Python 3.11, FastAPI, and Pydantic for the backend; SQLite and local files for persistence. Use Pipecat with SmallWebRTC for browser audio, Silero VAD, local faster-whisper transcription, and local Kokoro ONNX synthesis. Use server-side cloud clients for Groq and OpenRouter.

Host the browser on Windows and the application/speech services in Ubuntu under WSL2 on the planned RTX 4050 Laptop GPU with 6 GB VRAM. Treat hardware availability as an assumption to verify. Run one backend worker to avoid duplicate speech models. Use a dedicated Ubuntu laptop for the runner. Keep resumes, recordings, and cloud keys off the runner.

Keep responsibilities explicit:

| Owner | Responsibilities |
|---|---|
| Browser | Accessible setup, settings, transcript, microphone, playback, evidence actions, editor, corrections, reports |
| Session service | Consent, role/context snapshots, state transitions, turn ownership, allowed actions, event persistence |
| Voice integration | Local STT/TTS, endpointing, stream forwarding, playback progress, cancellation |
| Provider integration | Provider-specific requests, content deltas, validated structured results, errors and usage |
| Content records | Role profiles, scenario facts, coding contracts, rubrics, private references |
| Assessment service | Evidence validation, criterion coverage, version dependencies, disputes and report rendering |
| Runner | Authenticated fixed-language jobs, sandbox limits, trusted test comparison, cleanup |

Use a small common provider boundary because two implementations are explicitly required. Do not create a general plugin platform or a multi-agent interview runtime. Avoid Redis, Celery, vector databases, and agent frameworks. SQLite-backed jobs and bounded in-process workers are sufficient at this concurrency, provided restart recovery is explicit.

Fit these responsibilities into existing structure. If the repository remains documentation-only, use `apps/web`, `apps/api`, `apps/runner`, `content/roles`, `content/scenarios`, `content/coding`, `content/rubrics`, `prompts`, and `evals`. Keep private runtime data under ignored `data/`. Resolve compatible dependencies and commit lockfiles during the build; do not copy stale scaffold commands blindly.

## Groq and OpenRouter settings contract

### Selection and persistence

The Settings screen must expose an LLM provider selector with exactly `Groq` and `OpenRouter`; initial value is `Groq`. Persist the choice server-side so it survives reload and restart. Store separate live and assessment model IDs per provider so switching back restores that provider's configuration. The chosen provider handles live dialogue, permitted claim processing, coaching, and assessment; do not secretly send assessment to the other provider.

Groq initial model choices are `openai/gpt-oss-20b` for live dialogue and `openai/gpt-oss-120b` for assessment/code review. Verify availability at implementation and runtime preflight. If unavailable, show the problem and require an explicit valid selection; never silently substitute a model.

OpenRouter requires explicit live and assessment model selection from its available catalog, filtered or validated for required capabilities. Do not assume Groq model identifiers or parameters transfer unchanged. Do not invent a permanently free OpenRouter default. Clearly show model IDs, known pricing information and its freshness, or that pricing could not be verified. Paid processing requires explicit opt-in before requests. Use configured provider account spending controls; local token caps alone are not a guaranteed monetary ceiling.

Settings changes apply to newly created sessions. Freeze provider, model IDs, approved routing, relevant parameters, and consent version at session creation. Existing sessions and their background jobs keep that snapshot. Explain this in Settings. To use another provider for an active interview, end it and start a new session; this keeps context-sharing and assessment provenance unambiguous without hot-switch races.

### Credentials and validation

Load `GROQ_API_KEY` and `OPENROUTER_API_KEY` from protected backend environment configuration. The UI shows configured/missing/invalid status and a connection-test action, never the key. Credentials must not enter frontend bundles, browser storage, API responses, transcripts, exported reports, or logs. Do not use `VITE_` secrets.

Keep base URLs fixed in server code: Groq at `https://api.groq.com/openai/v1` and OpenRouter at `https://openrouter.ai/api/v1`. Do not expose arbitrary endpoint URLs. Settings writes and connection tests require authenticated owner access. A connection test uses a small synthetic request, discloses potential cost, and never uploads candidate data.

Missing credentials may allow a setting to be saved, but Start must remain blocked for cloud interviewing until configuration validates. The unused provider's absent key must not prevent starting with the configured provider. Persist settings atomically and reject invalid provider values, unsupported models, and malformed model IDs.

### Request behavior and routing

Use asynchronous clients with reused connections, bounded timeouts, and explicit cancellation. Normalize live content deltas, completion state, usage where available, and typed failures at the provider boundary. Keep provider-specific parameters there.

For supported Groq GPT-OSS requests, use low reasoning effort for live dialogue and exclude returned reasoning. Excluding returned reasoning does not eliminate internal reasoning. Use non-streamed schema-constrained responses for assessment where supported, then validate with application schemas.

For OpenRouter, use explicit model IDs and its documented streaming chat-completions interface. Forward only content deltas. Handle keep-alive events, empty deltas, and errors after streaming begins. OpenRouter may route to downstream providers; disclose that data path. Require an approved downstream provider selection for each configured model, constrain requests to it with documented routing controls, and disable provider fallback. Do not enable auto-model routing, model fallback lists, browsing plugins, or silent paid fallback. Validate current `provider.only`, `provider.allow_fallbacks=false`, and capability controls against documentation before implementation.

If an assessment model cannot meet required structured-output capabilities, reject that assessment configuration. Do not silently reinterpret arbitrary prose as validated findings. Validate all returned references and schema constraints even when strict output is supported.

Never automatically switch Groq to OpenRouter or vice versa on error. Handle authentication failure, unavailable model, rate limits, insufficient credits, network failure, context overflow, malformed output, and partial-stream failure distinctly. Respect `Retry-After`; bound retries and prioritize live dialogue over reports. Do not automatically restart an already delivered partial response. Preserve it as incomplete and offer explicit retry or typed continuation.

Record the selected provider/model, actual downstream route when available, request status, usage availability, and latency without exposing secrets or raw sensitive payloads. Do not treat unknown usage as zero.

## State, persistence, and concurrency invariants

Use a deterministic session state machine:

`SETUP → CLAIM_CONFIRMATION → RESUME_ROLE_DIALOGUE → BASELINE_INCIDENT → CODING → REVIEW → COACHED_RETRY → TRANSFER → REPORT → COMPLETED`.

These are interview stages, not build phases. Support paused and ended states without bypassing entry conditions. Setup requires confirmed context, selected role, consent, and valid provider configuration. Coding requires a selected authored problem; review requires a completed or explicitly skipped attempt. Record skips and unavailable modules, and never rate skipped criteria as failures. Stage transitions require authoritative backend validation and persisted events.

Persist sessions, resume sources and confirmed claims, role/content versions, consent records, turns, utterance versions, generation/delivery state, evidence actions, immutable submissions, executions, assessments, disputes, settings snapshots, and jobs. Use stable IDs and explicit foreign-key ownership.

Every action carries an idempotency key and expected session revision. Every response carries session ID, turn ID, and generation ID. Every assessment records exact input versions, rubric/scenario versions, and provider/model snapshot. Commit state changes and their events atomically. Reject duplicate effects, stale actions, and late results. A retry of the same submission request returns the same submission; an intentional new submission gets a new immutable snapshot.

On restart, recover committed events and mark interrupted work accurately. Requeue only jobs safe to repeat and still current. Do not publish old assessments after corrections, or recreate deleted sessions from pending jobs. Serialize state changes per session and apply database-level concurrency checks rather than relying solely on browser controls.

## Voice and streaming behavior

Load faster-whisper once, initially `large-v3-turbo` on CUDA with `int8_float16`. Start with English, beam size 1, word timestamps, and no previous-text conditioning. Use 16 kHz mono at the STT boundary, while respecting transport and TTS sample rates with proper resampling. Run inference outside the async event loop and consume lazy transcription results in the worker. Preserve timing against a session audio clock.

Use Kokoro-82M ONNX on CPU, initially `af_heart`, normal speed, and locally cached model/voice assets. Normalize technical pronunciation for speech only; preserve original transcript text. Verify current licenses, CUDA/cuDNN requirements, and Pipecat service compatibility before installation. If the planned STT model fails hardware acceptance, benchmark a smaller local model and disclose any changed default and accuracy tradeoff.

Warm speech models and playback before voice Start. Use approximately 600 ms silence as the initial endpointing setting, then calibrate. Provide Done speaking, Keep thinking, Pause, Stop, Repeat question, and typed answer controls. Support keyboard navigation, readable status, and transcripts without requiring sound.

Stream live provider text immediately to the browser through the WebRTC data channel. Simultaneously accumulate short complete clauses for TTS. Begin transmitting available audio frames without waiting for the whole response or a complete audio file. Do not synthesize individual tokens or split technical identifiers. Kokoro chunk synthesis followed by frame transport satisfies incremental delivery; do not claim sample-level model streaming without evidence.

Initially bound queues to two unsynthesized text chunks and roughly one second of unsent audio. Apply backpressure without dropping words. Track generated text, displayed text, and delivered speech separately. Playback acknowledgments indicate an estimate of delivery, not proof the candidate heard it. Mark interrupted or uncertain delivery and permit repetition.

On barge-in or Stop, immediately stop client playback, cancel cloud generation, invalidate the generation ID, and clear queued synthesis and audio. Discard late results, including results from local inference that cannot be cancelled. Never allow old audio to resume. Preserve delivered context and mark remaining generated text as interrupted rather than pretending it was spoken.

Disconnect pauses generation and invalidates playback. Reconnect fetches authoritative state; it must not replay buffered audio or duplicate questions automatically. STT ambiguity supports confirmation or typing. TTS failure retains text and offers text continuation. Cloud failure pauses adaptive dialogue or uses explicitly labeled authored local prompts; do not claim fully offline AI interviewing.

## Coding and execution isolation

Provide Monaco editing, Python/C++ selection, an authored stdin/stdout contract, public examples, Run and Submit actions, and immutable submission history. Include at least one appropriate authored problem per supported role profile, with both languages supported. Discuss the candidate's approach and complexity conversationally without supplying the solution during assessment.

The runner must authenticate application requests and execute both compilation and runtime under gVisor-backed isolation. If the runner or required isolation is unavailable, execution is unavailable. Never fall back to running candidate code on the application host or in an ordinary unrestricted container.

Enforce these starting limits:

| Resource | Limit |
|---|---|
| Source | 64 KiB |
| Python | Fixed Python 3.11 runtime image |
| C++ | Fixed compiler image, `-std=c++20 -O2` |
| Compilation | 15 seconds, 1 GiB memory |
| Each test execution | 2 seconds, 256 MiB memory |
| Execution suite | 30 seconds wall time, with a separate bounded compilation allowance |
| CPU | One CPU per job |
| Process count | Explicit finite limit, initially 64 |
| Temporary filesystem | Bounded ephemeral storage, initially 64 MiB |
| Captured output | 64 KiB combined stdout/stderr per case |

Disable network, GPU access, privileges, host mounts, Docker socket access, package installation, and user-provided build commands. Use read-only roots and bounded temporary filesystems. Keep expected outputs outside the candidate sandbox. Runtime receives only the required artifact/input, not compiler privileges or answer files. Kill the whole job on timeout/output violation and clean up after failure and cancellation.

Show full public-test diagnostics and aggregate hidden-test outcomes. Distinguish compile error, runtime error, wrong answer, timeout, output/resource limit, and infrastructure failure. Infrastructure failures cannot become candidate failures. LLM review may identify static concerns, but only execution records establish observed test behavior. Passing authored tests does not prove universal correctness.

## Assessment and correction contract

Separate resume clarity, demonstrated technical understanding, diagnostic reasoning, coding test outcomes, code-review concerns, and optional delivery observations. Never combine them into a global credibility, honesty, confidence, or hiring score.

Resume/role criteria: specificity, technical understanding, decision reasoning, measurement reasoning, and failure handling. Diagnostic criteria: problem framing, diagnostic selection, evidence interpretation, revision/uncertainty, and decision/verification. Author criterion-specific 0–3 anchors and technical examples before enabling ratings.

An observed criterion may receive 0–3; `not_observed` and `insufficient_evidence` must have no numeric rating. A material error requires clear evidence after relevant clarification. Missing context is not proof of failure. Accept technically sound alternatives and evaluate decisions against facts available at that moment.

Each published finding contains:

- An observed event or confirmed quote, source version, and optional audio interval.
- A relevant task fact or justified technical reference and its version.
- The criterion, rating/status, and assessment inference connecting evidence to the premise.
- A separate coaching suggestion, support level, and assessment version.

Validate ownership, quote spans, source versions, evidence visibility at decision time, reference existence, and rating/status consistency. A valid quote does not establish a valid inference. Permit abstention and block unsupported findings. If structured assessment fails, keep the factual event review and mark assessment unavailable. Render reports from validated persisted records without an unnecessary final LLM rewriting pass.

Transcript corrections preserve the original and create a new version. Finding challenges remain distinguishable from automatic acceptance of the candidate's preferred conclusion. Mark dependent findings stale or disputed immediately, exclude unresolved findings from conclusions, and recompute affected criteria. Never relabel edited text as original audio. Late assessment results for superseded versions cannot become current.

Optional speech feedback may describe answer duration, overall pace including pauses, articulation rate over speaking time, and pauses with defined denominators. Keep these separate from technical competence. Hide filler/repetition statistics until manually validated against recordings. Never infer emotion, personality, ownership, honesty, or competence from accent, pitch, volume, hesitation, or speed.

## Security, privacy, and data lifecycle

Treat resumes, job descriptions, spoken text, code comments, and model outputs as untrusted data. Delimit candidate context separately from trusted prompts. Model text cannot change policy, execute tools, reveal hidden cards, change settings, or authorize transitions. Enforce these boundaries in backend code and payload construction, not prompts alone.

Use authenticated session ownership for every API, signaling request, artifact, report, and runner result. A single-user local installation may use a simple owner session mechanism; it still needs protection against cross-session access and unintended LAN exposure. Use same-origin browser access, restrictive CORS, appropriate CSRF protection for cookie-authenticated mutations, secure cookies in HTTPS deployment, and redacted logs.

Default to loopback exposure. A LAN deployment needs authenticated access and HTTPS/secure-context microphone support; localhost testing is insufficient. Do not expose unauthenticated inference endpoints. Keep renderer dependencies and model assets local after provisioning.

Before any cloud call using candidate context, disclose that selected resume text, transcript, and submitted code may reach the selected provider and, for OpenRouter, its approved downstream provider. Raw microphone audio remains local. Record consent independently of audio retention. Changing provider for a new session requires the corresponding disclosure. Local deletion does not promise deletion from cloud-provider systems.

Provide visible retention choices: delete on session close or retain locally until a displayed expiry date, initially 30 days. Audio retention remains separately opt-in. Delete expired data on startup and during runtime. Explain that local machine administrators may access local files. Do not create backups by default; document backup retention separately if added.

Deletion cancels jobs, tombstones the session against late writes, and removes resumes, extracted text, audio, transcripts, summaries, reports, code, temporary artifacts, and derived records. Handle partial filesystem deletion as pending cleanup and retry; do not falsely report success. Do not promise forensic erasure from storage media. Never send deletions to a cloud provider without a supported mechanism and explicit scope.

## Required application interfaces

Use typed request/response schemas and an authenticated same-origin API. Equivalent existing routes are acceptable if they preserve these responsibilities.

| Interface | Contract |
|---|---|
| `GET /api/roles` | Return role profiles and supported objectives |
| `POST /api/resumes` | Validate, extract locally, and return editable context with provenance |
| `DELETE /api/resumes/{id}` | Remove abandoned uploads owned by the caller |
| `GET/PATCH /api/settings` | Read/update non-secret defaults with version checks |
| `GET /api/providers/{provider}/models` | Return available models and known capabilities/pricing metadata |
| `POST /api/providers/{provider}/test` | Test explicit configuration using synthetic input |
| `POST /api/sessions` | Create consented session with immutable provider/context snapshot |
| `GET /api/sessions` | Return owned local history |
| `GET /api/sessions/{id}` | Return authoritative state and current revision |
| `POST /api/offer` | Authenticated session-bound WebRTC signaling |
| `POST /api/sessions/{id}/answers` | Submit an idempotent typed answer through the same turn path |
| `POST /api/sessions/{id}/actions` | Confirm claims/hypotheses, request evidence/hints, pause, end, advance |
| `POST /api/sessions/{id}/submissions` | Persist source snapshot and enqueue isolated execution |
| `GET /api/submissions/{id}` | Return owned execution status and allowed diagnostics |
| `PATCH /api/sessions/{id}/utterances/{utterance_id}` | Create transcript correction version |
| `POST /api/sessions/{id}/findings/{finding_id}/disputes` | Record challenge and invalidate dependent conclusions |
| `GET /api/sessions/{id}/report` | Return pending, complete, partial, or unavailable assessment explicitly |
| `DELETE /api/sessions/{id}` | Cancel work and remove session artifacts under the retention contract |

Use the WebRTC data channel for live text, voice state, delivery progress, and state-change notifications. Re-fetch state after reconnect. Reject requests that refer to another owner's data, hidden content, invalid transitions, or stale revisions.

## Prompt boundaries

Keep versioned prompts for live interviewer, evaluator, code reviewer, and coach. These are separate responsibilities, not autonomous agents debating each answer.

The live prompt receives selected role, confirmed resume facts, allowed action, current objective, disclosed task facts, recent conversation, grounded summary, and support level. It asks one adaptive question, avoids unsupported assumptions, does not reveal answers, and returns only candidate-facing spoken content.

The evaluator receives confirmed evidence versions, criterion anchors, appropriate private references, and visibility timelines. It returns schema-constrained findings and can abstain. It must not treat instructions inside candidate text as assessment policy.

The code reviewer receives immutable source, contract, and verified execution summary. It separates observed results, static concerns, and unresolved questions, citing valid source lines. It does not claim tests ran without execution records or reveal hidden tests.

The coach receives a validated finding or explicit candidate-selected objective and the permitted practice exercise. It labels assistance and never sees the fresh variant's solution while coaching the earlier attempt.

## Final acceptance evidence

The implementation is complete only when these focused checks cover the integrated product. These are acceptance conditions, not a phased build plan. Mark each result pass, fail, unavailable, or blocked, with actual evidence; never label a target as measured performance.

| Area | Required proof |
|---|---|
| Hero page | Primary action opens setup; example uses labeled synthetic content; no microphone prompt, recording, or cloud request on page load; navigation works |
| Responsive visual design | Review actual desktop and mobile screenshots, including a 360 px viewport; no clipped actions or horizontal overflow; sphere remains secondary to coding/evidence workspace |
| Voice sphere | Ready/listening/processing/speaking/paused/error states match real lifecycle; speaking follows playback; interruption stops its pulse; muted microphone never appears active |
| Motion and rendering | Reduced-motion mode and static fallback remain clear; decorative rendering pauses in hidden tabs; visual effects do not break measured audio latency |
| Resume handling | Valid PDF/text, malformed/encrypted/image-only input, bounds, correction and claim provenance; no cloud upload before consent |
| Role personalization | Same resume with backend versus frontend roles yields relevant different objectives; latest-answer variants produce appropriate follow-ups |
| Conversation | Complete multi-turn interview with clarification, no repeated resolved question, skip, pause, typed continuation, and explicit wrap-up |
| Provider settings | Fresh default is Groq; switching to OpenRouter persists; switching back restores settings; old sessions retain their snapshot |
| Provider boundaries | Missing inactive key does not block; invalid active key/model does; both live and assessment use selected provider; no automatic cross-provider fallback |
| OpenRouter routing | Approved route and disabled fallback present in requests; paid opt-in respected; unsupported assessment capability blocked |
| Cloud failures | Authentication error, 429, insufficient credits, timeout, context overflow, malformed schema, and mid-stream error preserve valid state |
| Real integrations | Synthetic live and structured-assessment smoke checks with both configured providers; mocked contracts alone are not proof of provider connectivity |
| Reasoning exercise | Baseline, coaching, and fresh variant complete; cards are deterministic; hidden answers never enter live context or browser payloads |
| Coding | Both languages: correct/wrong code, compilation/runtime failure, infinite loop, excessive output, process/network attempt, timeout, cancellation and cleanup |
| Isolation | Verify actual gVisor execution and resource/network restrictions; runner outage never executes locally or creates a candidate failure |
| Streaming | Slow provider text appears before completion; first audio plays before later synthesis completes; no full-response buffering |
| Interruption | Repeated barge-in cancels prior generation, clears queues, and never resumes stale audio |
| Recovery | Slow client remains bounded; disconnect/reload, backend restart, runner loss, and model failure do not duplicate events or lose committed responses |
| Corrections | Misheard term and disputed finding produce versioned updates; stale assessment cannot publish; unresolved findings are excluded |
| Privacy/security | Secret scan of frontend/responses/logs; unauthorized access and injection tests; no raw audio upload; secure-context LAN microphone check if LAN is shipped |
| Retention | Synthetic session deletion and expiry remove related artifacts; pending jobs cannot recreate them; abandoned uploads are cleaned up |
| Accessibility | Keyboard-operated setup/settings/interview/report, visible labels/focus/status, and complete typed operation without a microphone |

Measure candidate speech end, endpoint decision, STT completion, cloud request start, first usable content, browser text receipt, first TTS chunk, first audio generation, and first browser playback. Report actual cold/warm results and p50/p95 with sample counts. Initial meaningful-audio targets are p50 at most 2 seconds and p95 at most 4 seconds; interruption target is playback stopping within 200 ms of detection. Filler audio does not count. Report misses honestly and their hardware/network conditions.

Verify local STT and TTS with internet blocked after provisioning. Cloud-dependent dialogue must pause clearly while typed input and authored local prompts remain available.

For automated adverse labels and numeric criteria, use at least 24 held-out answer traces across baseline, coached, and fresh cases, reviewed independently by two technically competent humans and adjudicated. Cover every shipped scenario family, valid alternatives, justified uncertainty, missing premises, and transcript errors. Freeze assessable criteria before judging. Target at least 90% supported actionable findings, at least 80% coverage of assessable criteria, and no observed unsupported high-severity finding. Publish numerators, denominators, disagreements, and exclusions. Include six transcript-repair injections and five distinct recovery paths.

An automated agent cannot impersonate human review. If calibration is unavailable or misses gates, ship the complete practice workflow with automatic adverse labels and numeric ratings disabled, factual reference comparison available, and the calibration limitation explicit. This is the defined safe assessment behavior, not permission to omit the report or correction system.

## Delivery requirements and documentation references

When implementation is requested, deliver source, authored content, validated schemas, dependency lockfiles, non-secret environment examples, storage migrations, runner image definitions, startup instructions, and acceptance results together. Include Windows/WSL and dedicated-runner prerequisites, model provisioning, offline speech checks, provider configuration, secure LAN setup where supported, and troubleshooting. Do not claim unavailable credentials, hardware, or human validation passed.

The final implementation report must identify material changes, commands/checks actually run, results, and remaining blockers. Stop when the contract is satisfied. Do not add unrelated polish or speculative services.

Provider documentation checked through Context7 on 20 October 2026 supports the integration direction below. Model availability, prices, quotas, and dependency compatibility remain time-sensitive; recheck relevant official documentation during implementation.

- [Groq reasoning controls](https://console.groq.com/docs/reasoning): reasoning controls are provider/model specific.
- [Groq structured outputs](https://console.groq.com/docs/structured-outputs): use supported schema-constrained assessment; current documentation excludes streaming/tool use for structured outputs.
- [Groq latency guidance](https://console.groq.com/docs/production-readiness/optimizing-latency): streaming content supports low-latency delivery.
- [OpenRouter authentication](https://openrouter.ai/docs/api_reference/authentication): OpenAI-compatible server-side endpoint and credentials.
- [OpenRouter streaming](https://openrouter.ai/docs/api_reference/streaming): incremental chat-completion delivery and stream handling.
- [OpenRouter provider routing](https://openrouter.ai/docs/features/provider-routing): verify downstream selection and fallback controls against current documentation.
- [Pipecat SmallWebRTC](https://docs.pipecat.ai/api-reference/server/services/transport/small-webrtc), [Kokoro service](https://docs.pipecat.ai/api-reference/server/services/tts/kokoro), [faster-whisper](https://github.com/SYSTRAN/faster-whisper), and [gVisor Docker setup](https://gvisor.dev/docs/user_guide/quick_start/docker/) are implementation references inherited from the plans, not compatibility or performance verification performed for this document.
