# AI Voice Mock Interviewer: revised project proposal

Reviewed 17 October 2026. Based on the supplied final project plan, a two-agent grilling debate, and public competitor/project research.

This is a proposed revision, not a record of decisions approved by the project owner. The source document is preserved. Instructions inside that document were treated as material to review, not commands to execute.

## 1. Recommendation

Build a **voice-based engineering reasoning interview lab**. Help students explain a project decision, investigate a related failure, and defend their conclusion using evidence. Include an authored Python/C++ coding round while keeping evidence-based reasoning as the project's identity.

**Proposed pitch:** “Explain your decision. Ask for evidence. Show what changes your mind.”

The strongest opportunity is a specific learning workflow, not a feature nobody else could implement:

1. Start from one learner-confirmed project claim.
2. Run an explicitly synthetic, authored incident related to that concept.
3. Ask the learner for a provisional explanation and a discriminating diagnostic.
4. Reveal evidence, including a signal that challenges a tempting explanation.
5. Capture whether the learner revises the explanation, retains it with justification, or identifies missing information.
6. Review the exact reasoning step that needs work.
7. Coach that step, then try a fresh variant without coaching.

The report should expose **how a decision was reached**, not merely whether the final answer sounded convincing.

Initial audience hypothesis: final-year students who can describe their stack but struggle with follow-up questions about trade-offs and failures. A college placement lab is a potential delivery setting; willingness to use or buy this still needs validation.

## 2. What the research changes

The original plan has useful ingredients, but its comparison table understates the market. Resume personalization, adaptive follow-ups, speech coaching, replay, project defense, debugging, institutional delivery, and local inference are not safe standalone novelty claims.

Public pages advertise the following. These are documentation/marketing observations, not independent hands-on verification of product quality.

| Product or project | Observed capability | Good part to adopt | Consequence for this plan |
|---|---|---|---|
| [Final Round AI practice documentation](https://docs.finalroundai.com/docs/mock-interviews/starting-a-mock) | Goal-specific spoken practice, multiple scenarios, debrief-to-practice continuation | Let feedback lead directly into another exercise | Voice and role personalization are baseline features |
| [Yoodli customization documentation](https://support.yoodli.ai/en/articles/9628260-customizing-practice) | Custom roleplays, rubrics, organizational groups, pressure scenarios | Define observable rubric goals before writing interviewer prompts | Personas, pressure mode, and college delivery are not unique |
| [Huru current facts](https://huru.ai/press/) | Spoken/video answers, structured content feedback, practice plans, organizational offering | Give one actionable improvement per answer | General interview coaching is crowded; current facts explicitly exclude acoustic analysis and code execution |
| [Rolewyn interview](https://rolewyn.com/products/interview) | Resume-claim cross-examination, weak-spot memory, grounded answer sketches | Probe a specific claim and leave missing evidence explicit | “Resume defense” alone is already an advertised product proposition |
| [RoundJump](https://roundjump.com/) | Project/repository context, voice, walkthroughs, live-change rehearsal, trade-off feedback | Connect an explanation to the artifact or decision being discussed | Own-project interviews and changing requirements are not enough to differentiate |
| [PrepLinx code comprehension](https://www.preplinx.com/ai-mock-interview/code-comprehension) | Unfamiliar code, planted defects, tracing, fixes, regression discussion | Evaluate comprehension and verification, not only solution writing | Replacing DSA with debugging alone is also insufficient |
| [MockIF debugging](https://mockif.com/debugging-interview-practice) | Planted-bug practice with a voice interviewer and process feedback | Reward reproducible reasoning and verification | Voice-driven diagnostic practice already has overlap |
| [Frontend Interviews methodology](https://frontendinterviews.com/methodology) | Diagnose, teach, retry, transfer, and spaced return | Check the same skill in a new context after coaching | Retry/transfer is sound pedagogy, not a new invention |
| [DeepInterview release v0.3.0](https://github.com/ngoanpv/DeepInterview/releases/tag/v0.3.0) | Published local-model interview path | Keep preparation, live interaction, and post-session analysis separate | Fully local voice practice is not novel by itself |
| [iarsingh/ai-mock-interviewer](https://github.com/iarsingh/ai-mock-interviewer) | Local-first voice-led practice, topic sets, typed fallback, optional local inference | Keep a usable typed path and clear degraded behavior | Audit every audio component: the README warns browser recognition can require the internet |

[MockGPT](https://mockgpt.io/) also advertises transcript replay and next-practice recommendations, but its FAQ says it is preparing early access. Treat it as an advertised direction, not proof of a generally released feature.

Do not copy implementations without reviewing their licenses. Borrow the interaction patterns and evaluate whether reusing code actually reduces work.

### Honest novelty statement

In the public sources reviewed, I did not find an explicit description of the complete combination of learner-confirmed project context, staged diagnostic evidence, a visible belief-revision timeline, correction-aware assessment, and an uncoached matched variant. The updated deployment combines local speech with cloud reasoning; full local inference is not a current promise.

That is a **differentiation hypothesis**, not proof of worldwide originality. Related debugging products and learning loops are substantial prior art. Search cannot establish that a feature is absent from every released product, including private or undocumented features.

Use “designed around evidence-based reasoning practice” in a pitch. Avoid “world's first,” “no competitor has this,” and “detects fake projects.”

## 3. A concrete demo

**Learner-confirmed claim:** “I used caching to reduce API latency.” The learner can edit the claim and say what they personally implemented. The system does not demand confidential code or invent measurements.

**Boundary:** the following exercise is synthetic. It is related to caching, not a reconstruction of the learner's actual production system.

**Incident:** after a product update, one API response still returns an old price. The initial packet shows a successful database write and an old API response.

The learner says: “The cache might not be invalidated.” The interviewer asks: “What observation would distinguish that from reading the wrong database?”

The learner can request authored diagnostic cards such as:

- Database read: the primary contains the new price.
- Request trace: this response was served by a cache hit.
- Key trace: the reader uses a versioned key; invalidation deletes an unversioned key.
- Dashboard panel: aggregate cache hit rate looks normal, which does not establish that this particular key is correct.

The cards have fixed facts and provenance. The LLM does not invent new logs to steer the candidate toward an answer. Multiple sensible investigation orders are accepted.

The learner concludes that a key mismatch explains this incident and proposes a targeted regression check. Alternatively, a learner who lacks enough evidence can identify the missing diagnostic and give a conditional next step.

**Feedback:** “You used an aggregate metric to dismiss a request-specific failure. The panel did not test that claim.” Show the candidate's confirmed quote, the relevant card, and the reasoning rule. This is more useful than “your confidence was low.”

**Coached retry:** practice distinguishing aggregate evidence from request-specific evidence.

**Uncoached variant:** the same stale-price symptom now comes from a delayed replica read; the cache is bypassed. The previous cache repair is incorrect here. Record whether the learner checks the evidence or repeats the memorized solution.

**Demo payoff:** the report compares the initial explanation, requested diagnostics, revisions, conclusion, and performance on the fresh case. Do not claim that one improved attempt proves durable learning.

## 4. Niche and extra features, ranked

These are candidate opportunities. None is established as absent from every other product. Build the first workflow before accumulating extras.

| Priority | Feature | Observable behavior and value | Novelty confidence / scope |
|---|---|---|---|
| Core | **Reasoning revision timeline** | Record a provisional hypothesis, diagnostic request, revealed evidence, and justified revision or retention; replay each decision | Potentially distinctive presentation and assessment combination; moderate build effort |
| Core | **Same symptom, different cause** | A fresh case resembles the first but requires a different conclusion; detects answer reuse within the exercise | Strong demo and useful evaluation; transfer learning itself already exists |
| Core | **Scoring that can be corrected** | Candidate fixes a mistranscribed term or challenges a missing premise; affected judgments are withdrawn or recomputed with history | Trust feature; not claimed unique |
| Next | **Impact-measurement defense** | Ask what “40% faster” measures: baseline, percentile, sample size, workload, and changes made together; distinguish correlation from causal evidence | Sharper than generic “explain Redis”; claim-defense products overlap |
| Next | **Explain without disclosing** | Candidate supplies a redacted decision card instead of proprietary code; interviewer respects an explicit confidentiality boundary and tests a synthetic analogue | Useful for internships and restricted projects; local deployment supports it |
| Later experiment | **Insufficient-evidence cases** | Some authored cases cannot be resolved from available evidence; learner should request missing information or give a conditional recommendation | Useful reasoning niche; prevent a game where “not enough data” always wins |
| Later experiment | **Stakeholder handoff** | Explain the same incident to an engineer and a product manager; preserve facts while changing detail and next actions | Concrete communication practice; roleplay itself is common |
| Later experiment | **AI-patch skepticism** | Inspect a plausible suggested repair, identify a counterexample, and justify acceptance or rejection | Timely but crowded; code-review practice already exists, so not a headline differentiator |

Do not introduce a diagnostic-request penalty in v1. Asking for evidence is usually desirable. Resource budgets only make sense when an authored scenario defines realistic cost, risk, or time constraints and accepts alternative effective paths.

## 5. A complete, narrow first version

### Included

- One learner, one session at a time, on a local installation.
- One confirmed project decision card, entered manually or extracted from a text-based resume and corrected by the learner.
- One authored caching incident family with a baseline case, coached exercise, and fresh variant.
- Spoken questions and answers, transcript, visible evidence cards, and typed fallback.
- Explicit candidate confirmation of hypothesis statements used in assessment.
- Deterministic session stages and evidence reveal rules.
- Criterion-level feedback, audio/transcript replay where recording is enabled, corrections, and a targeted next exercise.
- Local speech inference and storage, disclosed cloud text/code processing, visible recording consent, retention controls, and deletion.
- A code editor and isolated Python/C++ execution for authored stdin/stdout problems, with verified test feedback.

### Deferred

Arbitrary repositories and custom build commands; whole-repository ingestion; automatic incident generation; system-design whiteboard; company personas; pressure mode; emotion/confidence inference; expressive TTS experiments; voice cloning; full Hinglish support; placement dashboards; student rankings; simultaneous classroom sessions; certificates; universal readiness scores.

These are scope choices for the proposed MVP, not permanent product bans. The coding round uses a small authored problem set rather than a broad DSA catalog. The 19-minute flow below describes the reasoning exercise; allow a separate 15-minute coding stage before review when running the complete interview.

### Suggested 19-minute session

| Stage | Time | Output |
|---|---:|---|
| Setup and consent | 2 min | Audio check, retention choice, accessibility controls |
| Confirm one project decision | 3 min | Learner-approved claim, personal contribution, known boundaries |
| Baseline incident | 6 min | Diagnostic requests, confirmed hypotheses, justified conclusion |
| Review and coached retry | 3 min | One specific reasoning gap and guided practice |
| Fresh variant | 3 min | Uncoached evidence of applying the targeted skill |
| Report | 2 min | Replay, criterion results, unresolved questions, next exercise |

Time limits guide the session; an accommodation or slow speech must not silently reduce a competence score. Prompt to wrap up or let the learner extend where practical.

## 6. Scoring that deserves trust

Remove the global 100-point score from the first version. Fixed arithmetic does not make an LLM judgment correct. Show a small criterion vector with evidence and coverage instead.

| Criterion | What counts as evidence |
|---|---|
| Problem framing | Learner distinguishes observed symptom from assumed cause |
| Diagnostic selection | Requested observation can separate plausible explanations |
| Evidence interpretation | Learner applies a card only to claims that the card supports |
| Revision and uncertainty | Learner revises when warranted, or explains why evidence does not overturn the hypothesis |
| Decision and verification | Proposed action addresses the supported cause and includes an appropriate check |

Use 0–3 anchored ratings only when observable, plus **not observed** and **insufficient evidence**. An illustrative anchor for evidence interpretation is: 0 contradicts a clearly relevant observation after clarification; 1 cites a result without connecting it to the claim; 2 connects relevant evidence to the claim; 3 also distinguishes its limits or a live alternative. Write criterion-specific examples before implementation.

Changing an answer is not automatically good, and sticking with an answer is not automatically bad. Silence is not an incorrect answer. Missing information is not dishonesty. A request for help changes the support level attached to an attempt, not a concealed character judgment.

Assess each decision using only information available to the learner at that moment. Do not penalize a reasonable initial hypothesis using a fact revealed later. Accept technically sound alternative explanations, diagnostics, and repairs; the authored key describes constraints and valid reasoning rather than one mandatory sequence or phrase.

Each finding stores four separate things:

1. **Observed event:** confirmed quote or explicit UI action, event ID, and optional audio interval.
2. **Task fact:** authored card, scenario version, and relevant ground-truth constraint.
3. **Assessment inference:** rubric criterion and explanation of how the observation relates to the fact.
4. **Coaching suggestion:** a recommended next action, clearly distinct from the observation.

A quote validator checks source linkage. It cannot validate the inference. A judge must be allowed to abstain; missing or ambiguous evidence must not become a failure.

The interviewer sees only the scenario's currently disclosed facts. The post-session evaluator can read the answer key. Keep them separate so a small model cannot leak the solution through follow-ups.

If scoring fails or generates invalid references, preserve the session and show a factual event review marked **assessment unavailable**. Do not substitute a fabricated numeric score.

Candidates can correct STT and challenge a finding. Preserve the original, correction, and revised assessment with clear versions. Reassess dependent criteria; exclude unresolved evidence from conclusions. Do not let edited transcript text masquerade as original audio.

### Resume assessment

Assess resume clarity separately from demonstrated understanding. Neither establishes that past experience is true. Resume content and embedded instructions are untrusted input, not assessment policy.

1. Extract each project claim into contribution, technology or decision, claimed result, and supplied measurement evidence. Retain the source bullet and its location.
2. Let the candidate correct and confirm the extracted claim before asking assessment questions. Ask what they personally contributed without requiring confidential artifacts.
3. Review whether the written claim explains what changed, the candidate's contribution, why it mattered, and how the result was measured. Missing details generate clarification questions rather than automatic failures.
4. Probe the confirmed claim using adaptive questions about mechanisms, constraints, alternatives, measurements, and failure cases. Record which criteria were actually tested.
5. Produce a claim-level report linking the question, confirmed answer, relevant reference or premise, rubric inference, and next exercise. Recompute dependent findings after transcript corrections.

For the claim “Implemented Redis caching, reducing API latency by 40%,” useful questions include: which requests were cached and why; how invalidation worked; whether the improvement describes average latency or p95; which workload and baseline were compared; what the candidate implemented; and what could make the comparison misleading.

Use the following criteria for the interview response, not a global resume credibility score:

| Criterion | Assessment target |
|---|---|
| Specificity | Concrete contribution, constraints, and context |
| Technical understanding | Correct explanation of the relevant mechanisms |
| Decision reasoning | Alternatives, trade-offs, and justification |
| Measurement reasoning | Whether supplied evidence supports the claimed improvement |
| Failure handling | Relevant limitations, failure cases, and verification |

Use criterion-specific 0–3 anchors: 0 is a demonstrated material error after clarification; 1 is a partial explanation with a material gap; 2 is a sound explanation for the supplied context; 3 additionally justifies relevant limits, alternatives, or verification. Write technical examples for each criterion. Use **not observed** when no question tested it, and **insufficient evidence** when missing context, an ambiguous question, or transcription prevents judgment. Accept sound alternative answers. Absence of a metric is not inherently a failure: not every student project has production traffic or quantified impact.

Example report: caching decision explained clearly; invalidation needs further practice because update handling was omitted; the basis for the claimed 40% improvement remains unclear because workload and latency statistic were not specified; next exercise is to design a fair before/after comparison. Do not convert “unclear in this interview” into “false on the resume.”

Never assign an honesty score, label a project fake, infer ownership from hesitation, or invent accomplishments in a suggested rewrite. Related synthetic tasks measure understanding of the exercised concept; they cannot verify that the candidate built the original project. If an actual claim cannot be checked from supplied evidence, leave it unverified rather than treating it as disproven.

### Speech feedback

Retain optional descriptive duration, pace, and pause feedback after validating measurement. Define whether WPM uses total answer duration or speaking time. Do not mix acoustic measures into technical competence or infer honesty, ownership, emotion, or confidence from them.

Filler extraction requires manual validation; an ASR prompt does not guarantee verbatim disfluency preservation. Count only when the actual transcription method is reliable. Personal baselines help comparison but do not eliminate transcription bias or disability-related differences. Drop universal pace/pitch targets and automatic difficulty changes triggered by hesitation.

## 7. Architecture and ownership

The repository currently contains no implementation. This is an architectural proposal, not a tested stack or hardware claim.

Keep the original local voice pipeline and code-owned state machine. Put the new invariant—the facts of the exercise—inside a small authored scenario record and deterministic transition logic. Do not add a live debate between agents to the product; the two-agent debate was a planning technique.

| Responsibility | Owner |
|---|---|
| Microphone, playback, evidence cards, confirmations, correction UI | Browser client |
| Consent, session state, allowed transitions, scenario fact disclosure, event persistence | Application backend |
| Transcription and synthesis | Local speech model processes |
| Wording of permitted follow-ups, reasoning assessment, and code review | Backend calls to cloud LLMs with disclosed text/code sharing |
| Scenario facts, valid diagnostic results, accepted causal explanations, rubric examples | Versioned authored content |
| Source validation, coverage, assessment versioning, report rendering | Backend assessment/report logic |

Use stable IDs for the scenario version, attempt, evidence card, utterance, correction, and assessment. A report reads persisted events rather than a lossy conversational summary. An interrupted request must not reveal a card twice, advance two stages, or attach late audio to a new turn. Cancellation invalidates pending audio and model responses from the old turn.

Updated deployment choice: use the RTX 4050 6GB laptop for the browser, backend, local GPU STT, and local CPU TTS. Reasoning and code-review LLMs use cloud APIs. Use a second dedicated Ubuntu laptop for isolated Python/C++ execution; its purpose is separation of untrusted code and compilation load, not extra inference VRAM. Four separate 6GB GPUs do not automatically act as one 24GB GPU.

Keep only one chosen speech pipeline in v1. Benchmark the original fast TTS baseline before investigating expressive alternatives. The desired output is a useful, responsive interview, not a particular model brand.

The user subsequently included Python and C++ coding rounds in the first release. Run only authored stdin/stdout problems through fixed compiler/runtime images on the second laptop. Require gVisor-backed isolation, no network or secrets, filesystem restrictions, resource limits, timeouts, and bounded output. A container label alone is insufficient assurance. Compilation and tests establish observed behavior; cloud review does not replace execution.

### Required end-to-end streaming

Streaming applies to both live interviewer text and synthesized audio reaching the browser. A backend that streams from the provider but buffers the full response before forwarding it does not meet this requirement.

- Use the cloud LLM's streaming response for live dialogue. Forward usable content deltas promptly to the browser through the Pipecat WebRTC data channel, with session, turn, and response identifiers. Do not forward internal reasoning or provider metadata as spoken text.
- In parallel, accumulate those same content deltas into short, complete clauses or sentences. Send the first suitable chunk to local Kokoro without waiting for the full LLM response. Avoid synthesizing isolated tokens or cutting technical identifiers in half.
- Forward available synthesized audio frames through the WebRTC media track and start browser playback while later text and audio are still being generated. Do not wait to build or download a complete WAV/MP3 file, assemble a full-response Blob, or finish the whole utterance.
- Kokoro may generate a chunk before yielding its samples. Distinguish model-level incremental synthesis from transport streaming: the requirement is incremental text chunk synthesis plus immediate transport of available audio. Verify actual time to first audio rather than claiming sample-level model streaming without measurement.
- Preserve chunk order with bounded queues. Keep at most two unsynthesized text chunks and approximately one second of queued unsent audio initially. Apply backpressure instead of dropping words; tune these bounds from interruption and underrun measurements.
- Maintain independent generated-text and playback progress. The UI can show text arriving ahead of speech, but mark interrupted output clearly. Generated text is not evidence that the candidate heard the whole question.
- Candidate barge-in or Stop cancels the cloud request, invalidates the response generation, clears queued synthesis/audio, and stops browser playback. Drop late results carrying the previous generation ID, including non-cancellable local inference results.
- On disconnect, pause generation and invalidate pending playback. Reconnect by loading persisted session state; never replay stale buffered audio automatically. If synthesis fails, retain the displayed question and offer text continuation without presenting an incomplete audio delivery as complete.
- Keep strict structured assessment/report generation outside the spoken critical path. It may run non-streamed when required by the provider. Live dialogue must not wait for those jobs.

Instrument speech end, endpoint decision, STT completion, cloud request start, first content delta, first text sent/received, first TTS chunk submission, first audio generated, and first browser playback. Measure the end-to-end interval from candidate speech end to meaningful audio playback. Filler clips do not count as a faster substantive response.

Acceptance checks: a deliberately slow provider stream displays text before completion; a multi-sentence response starts playing before final text or later synthesis finishes; chunk boundaries preserve words and technical notation; bounded queues survive a slow client without unbounded memory; interruption prevents old audio from resuming; and disconnect/reconnect never duplicates response delivery. Report p50/p95 text-first and audio-first latency on actual hardware. Initial meaningful-audio targets remain p50 at most 2 seconds and p95 at most 4 seconds, subject to measured feasibility.

### Local privacy and failure behavior

- Local/on-prem describes where processing happens. It does not prevent a college administrator or another local user from accessing recordings.
- Separate interview participation from retaining audio. Retain only what the candidate chooses; audio replay is unavailable when no audio is retained.
- Protect session access and model endpoints. Do not expose unauthenticated inference services to the whole LAN.
- Plan a browser secure context for microphone access on LAN clients; “localhost works” does not establish that another laptop can use the microphone.
- Package speech model files and browser assets locally. Verify STT and TTS work without internet after installation. Cloud dialogue and assessment require internet; on connection loss, pause those functions or continue with authored local prompts rather than claiming fully offline interviewing.
- Disclose that selected transcript/context and submitted code are sent to the configured cloud LLM provider; raw microphone audio stays local. Retention and deletion guarantees for local files do not imply deletion at a provider. Review provider data controls and obtain informed participation consent.
- Treat resumes, uploaded text, and spoken commands as untrusted content. They must not modify rubric policy, reveal answer keys, trigger tool execution, or alter access rules.
- Define deletion across the resume, transcript, audio, reports, temporary files, summaries, and derived indexes. State backup retention separately if backups exist.
- If ASR is uncertain about an assessed term, ask for confirmation or allow typing. If TTS fails, display the question. If the model fails, use the authored neutral prompt or pause safely.

## 8. Release gates and smallest sufficient proof

Targets below are proposed gates, not results already achieved.

| Gate | Focused proof |
|---|---|
| Scenario correctness | Two technically competent reviewers independently trace every card and accepted outcome; resolve contradictions before pilot |
| No answer leakage | Exercise baseline and fresh-case paths; interviewer context excludes hidden answer keys and unrevealed facts |
| Evidence integrity | Every published finding resolves to a real event and scenario fact; invalid references are blocked |
| Valid assessment | Double-review a fixed sample, for example 60 criterion judgments from at least 10 sessions; report counts, disagreements, abstentions, and unreported misses |
| Useful provisional scoring | Aim for at least 90% human-confirmed validity of published findings; report denominator and coverage so abstaining on everything cannot pass |
| Candidate correction | Correct one misheard technical term and one disputed finding; affected report changes, originals remain distinguishable, unresolved items are excluded |
| Genuine interaction latency | Measure speech-end to first meaningful response audio on actual hardware; report p50/p95 and end-of-turn cutoff errors. Starting targets: p50 ≤2s, p95 ≤4s; filler clips do not count |
| Local speech execution | Verify STT/TTS with internet blocked after provisioning; cloud features pause clearly while authored local prompts and typed recovery remain available |
| Data lifecycle | Delete a synthetic session and verify its related stored artifacts are gone under the stated retention policy |
| Failure recovery | Interrupt synthesis, disconnect a model worker, and reload during an attempt; no stale audio, invented score, duplicate event, or lost committed response |

Before the student pilot, build a small held-out benchmark: 24 answer traces across the three authored variants, rated independently by two reviewers and adjudicated. Include valid alternative solutions, incorrect reasoning, justified uncertainty, missing premises, and transcript errors. Freeze which criteria are assessable before running the judge. Proposed gates are at least 90% supported actionable findings, at least 80% coverage of assessable criteria, and no observed unsupported high-severity finding. Publish exact counts and exclusions; these small samples cannot demonstrate a zero-error system. Exercise six injected transcript repairs and five distinct recovery paths.

If precision or coverage misses the gate, disable automatic defect labels and scores for the pilot. Keep voice practice, authored reference comparison, and candidate-reviewed observations. Do not silently change cloud providers, send additional data, or enable paid processing to rescue assessment quality.

Pilot usefulness and reasoning performance separately. Ask learners whether they can identify their next concrete practice action. Have reviewers score fresh-case attempts without seeing whether they came before or after coaching. Counterbalance case order where possible; record hints and support levels.

A roughly 20-student pilot can expose failure modes and estimate usability. It cannot establish hiring validity or prove coaching caused improvement. A later controlled comparison against a well-prompted general assistant plus the same exercise would test whether the product adds enough value to justify its complexity.

## 9. Proposed 12-week roadmap

The original schedule is retained as a planning envelope. Team capacity and hardware throughput remain unverified.

| Weeks | Deliverable and exit condition |
|---|---|
| 1–2 | Author and manually facilitate the first case and fresh variant with 5 learners; confirm the reasoning gap matters before optimizing voice |
| 3–4 | Local voice/text loop, consent, claim confirmation, deterministic evidence cards; one complete baseline attempt |
| 5–6 | Python/C++ editor and isolated runner, persistent event timeline, grounded criterion report, and correction flow; verify sandbox limits and curated findings |
| 7–8 | Coached exercise and fresh variant; compare support levels and outcomes without claiming mastery |
| 9–10 | Actual-hardware streaming latency, interruption/recovery, local-speech offline verification, runner access, and deletion checks |
| 11–12 | Pilot, independent assessment review, scenario revision, and a reproducible demo with published limitations |

If time is short, retain the authored reasoning loop and cut voice expressiveness, speech dashboards, extra roles, and distribution. If the initial manual sessions show no value over ordinary project questioning, revise the learning task before building more infrastructure.

## 10. What the agent debate resolved

One agent used the grilling skill to challenge the plan; a second answered as a provisional designer. They worked through three rounds: purpose and trust, workflow and architecture, then competitor overlap and release gates.

| Challenge | Recommended resolution |
|---|---|
| What improvement matters? | Better evidence-backed explanations and decisions, demonstrated on a fresh case |
| Can resume defense be the novelty claim? | No; competitors explicitly advertise it |
| Does quoting the transcript establish that a criticism is true? | No; separately validate the task premise and assessment inference |
| Can a model establish project ownership or honesty? | No; report what the learner demonstrated in this exercise |
| Is local operation enough to differentiate? | No; make it a verified deployment property supporting the workflow |
| Is adaptive speech behavior reliable assessment? | No; keep accessibility controls explicit and acoustic feedback descriptive |
| Should every session produce a score? | No; abstain or show factual review when evidence/scoring is inadequate |
| What is the smallest convincing demo? | One coherent case family, visible diagnostic reasoning, grounded correction, and a fresh variant |

### Assumptions for owner review

The agents cannot approve these on the user's behalf:

1. Prioritize engineering reasoning over generic DSA in the first release.
2. Start with final-year students and a caching case family.
3. Limit the first system to one concurrent session and candidate-controlled sharing.
4. Treat the original 12-week schedule as a target, pending team capacity and hardware checks.

No software implementation, purchases, deployment, recruitment, or external messages were performed for this review.
