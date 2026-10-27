# Implementation acceptance evidence

Date: 20 October 2026. This file records observed checks, not intended guarantees. Implementation remains active; the complete contract in `agent.md` is not yet proven.

The latest scoped status and internal gaps are recorded in [contract-audit.md](contract-audit.md). This file is chronological; earlier unavailable-runtime statements are superseded by the later measured checks, not silently rewritten as historical successes.

## Evidence collected

- Repository initially contained planning documents only; historical README commands referenced absent `backend`, `frontend`, and `runner` directories. Source now lives under the contract's `apps/` layout.
- Backend dependencies resolved and locked in `apps/api/uv.lock`; installed in the application virtual environment. Host Python is 3.12.10, Node.js 24.15.0, uv 0.13.0.
- Backend Python compilation passed.
- `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests -q --basetemp=apps/api/.pytest-proof-4`: **19 passed**, one Starlette TestClient deprecation warning. Tests ran outside the sandbox after temporary-directory restrictions blocked the first attempt.
- Tests cover authenticated ownership/CSRF/origin, common resume redaction/provenance and malformed/oversized input, atomic single-session reservation including concurrent starts, creation/action idempotency, stale revisions, explicit evidence cards without private references, full typed stage progression, coding skip requirements, transcript preservation/correction, stale/disputed factual observations, deletion tombstones, runner-unavailable failure without local execution, restart recovery and provider-specific persistence.
- Provider tests use HTTPX MockTransport: content deltas only, reasoning excluded, explicit Groq reasoning controls, OpenRouter approved route/fallback controls, authentication/rate-limit/credits/model/context errors, partial-stream preservation without retry, and strict assessment model selection. These are **mocked contracts**, not real provider connections.
- Runner agent parsed 22 JSON records, seven JSONL fixture files and compiled runner Python syntax. No runner dependency, Docker image, Docker daemon or gVisor runtime was installed or executed on this computer.

## Unavailable checks and remaining work

- `wsl --list --quiet` returned `Wsl/E_ACCESSDENIED`. WSL/GPU/CUDA hardware cannot be verified from this environment at present.
- No provider credentials have been established as usable. Live Groq/OpenRouter smoke tests, catalog availability, actual route capability, paid account controls and adaptive dialogue latency are unverified.
- Local Pipecat/STT/TTS runtime and model assets have not been provisioned. Actual audio, offline STT/TTS, playback acknowledgment, interruption timing and cold/warm latency require runtime acceptance on target hardware.
- Dedicated Ubuntu runner installation and adversarial resource/network/process/output/timeout cleanup checks must run on the owner's separate PC. Installer source is provided; execution here is explicitly prohibited by the owner.
- Independent human content review and double-reviewed calibration are unavailable. Numeric/adverse automatic assessment remains disabled; authored factual reference practice is the required safe mode.
- Browser integration, actual desktop/mobile screenshots, accessibility interaction and final source/requirement audit remain in progress.

## Release decision

Not complete. Passing unit checks do not establish full integrated contract compliance. Keep the active goal open until browser and integration work plus explicit unavailable-prerequisite reporting are finished.

## Current revalidation

- Backend plus runner **static-only** checks: 35 passed, one TestClient deprecation warning (`pytest apps/api/tests apps/runner/tests`). This did not import or execute the runner service or install runner dependencies.
- Local voice helper checks: 6 passed (`pytest apps/api/interviewer/voice/test_manager.py`). These are lightweight tests without speech models or actual audio transport.
- Current web production build: passed TypeScript and Vite. Monaco is loaded separately from the 210 KB initial JavaScript bundle; its larger editor bundle produces a size advisory.
- Browser smoke observed the landing example dialog, owner login and setup, desktop CTA visibility, and 360 px document width without overflow. No browser errors or external asset requests were recorded. Screenshots are under `docs/screenshots`; `docs/browser-results.json` stores the observed result. This smoke does not establish the complete candidate journey.
- Dedicated Ubuntu installer remains `apps/runner/install-dedicated-ubuntu.sh`; it was not executed on this computer.

## Integrated browser journey

`node evals/browser-journey.cjs` completed against the explicitly synthetic acceptance server with no browser JavaScript errors. It exercised owner authentication, saving provider settings, synthetic live/structured connection testing, local pasted resume extraction, claim/context confirmation, cloud consent, interview creation, streamed adaptive TTL follow-up, baseline evidence disclosure and conclusion, explicit coding skip, authored review, coached exercise, fresh transfer, completion and report. Screenshots: `interview-desktop.png` and `report-desktop.png`. Results: `browser-journey-results.json`.

The runner was intentionally skipped rather than mocked as executed. This browser run proves UI/backend integration with a synthetic provider, not live cloud adaptivity, voice playback or isolated candidate execution. Full real-integration acceptance remains open.

Visual review of the desktop interview screenshot found an icon-sized CSS rule clipping the new text Send button. The integrated stylesheet now gives text actions a 108 px minimum width and 44 px minimum height, stacks the input/button on mobile, and preserves 44 px voice controls. Production build was rerun after the fix.

## Disconnect invariant correction

Audit found that disconnect previously cancelled only an actively running generation task. Completed cloud text could leave queued voice output alive without authoritative pause. Disconnect now atomically pauses the session, changes its generation ID, increments revision, marks unfinished text interrupted, persists a disconnect event, and cancels playback/generation. Repeated disconnect is idempotent; completed sessions are unchanged. The focused system suite passed 20 tests, including the new regression. Normal resync notifications keep their stream open; only a dropped slow-client queue closes for reconnect.

## Repeat-question behavior

Audit found Repeat previously asked the provider to generate another response, so the button could change the question. Repeat now delivers the exact persisted question through the same text/audio path with a new generation, no cloud request, and `local-repeat` provenance. A regression forbids provider access and checks exact text plus completed delivery.

## Client generation ownership correction

The live EventSource handler captured the initial `voice.connected` value and applied completion/state events without checking their generation. Late completion could therefore reset the status during a newer response. The handler now reads current session/voice refs, rejects mismatched session/generation state events, and applies fetched session state only when its revision is at least current. This preserves authoritative generation ownership across interruption and delayed fetch responses. TypeScript/Vite production build rerun after the change.

## Cloud failure pause

A partial cloud failure now pauses adaptive dialogue, invalidates its generation, stops connected speech, preserves the committed answer and partial question, and records the typed provider failure. The interview displays the persisted failure after reload and requires Resume before Retry. This is explicit cloud-dependent recovery, not an offline-AI claim. The new regression injects a partial stream followed by failure and checks preserved content, paused state, generation invalidation and incomplete delivery.

## Grounded reasoning context

The live interviewer previously received disclosed cards and ordinary turns but omitted separately confirmed hypotheses and conclusions. Its bounded context now includes the latest 16 confirmed reasoning actions with persisted event IDs and a six-answer extractive memory with utterance IDs and current source versions. It does not infer resolved points, substitute summaries for the full transcript, or include unrevealed cards/private causal references. Regression verifies the confirmed hypothesis and requested card are present with real event provenance while hidden evidence is absent. Focused system suite: 23 passed.

## Keep-thinking turn ownership

Multiple VAD-finalized segments accumulated during Keep thinking previously invoked the answer callback repeatedly on Done speaking. That could start competing model generations or reject a later segment as an overlapping answer. Done speaking now merges held segments into one committed candidate turn, retaining separate segment timing metadata. Single-segment metadata remains unchanged. Voice helper regressions: 7 passed. These checks do not establish hardware STT/TTS operation.

Runtime prerequisite recheck: no GROQ_API_KEY, OPENROUTER_API_KEY, RUNNER_URL or RUNNER_BEARER_TOKEN was present in backend environment/local .env; Pipecat, faster-whisper, Kokoro and local model directory were absent. No credential values were printed.

## Speech provenance persistence

The authenticated local speech callback previously discarded its timing metadata when entering the common answer path. Turns now preserve `input_source` and local STT metadata through transcript corrections; the original version remains distinguishable from candidate edits. Relative word timestamps are explicitly labeled as segment-relative rather than falsely described as session-clock intervals. Typed clients cannot supply speech metadata through the strict public answer schema. A regression checks persistence, correction provenance and rejection of a forged typed metadata payload. Full session-clock audio alignment still requires implementation/real-runtime verification.

## Session-clock alignment and recording reconnect safety

Local speech now carries an interval and word offsets aligned to session creation using the server connection offset plus the decoded 16 kHz sample count, while retaining original segment-relative word offsets. The metadata explicitly states that transport delay is unmeasured; these are approximate transport-clock observations, not proof of hearing or calibrated latency. Each opted-in connection writes a unique recording artifact and stores its generated name in speech metadata. Reconnect no longer overwrites the earlier connection's WAV. Default no-recording creates no artifact. Eight lightweight voice checks pass, including deterministic alignment; hardware timing remains unverified.

## Dedicated-runner acceptance tooling

Added `apps/runner/acceptance_dedicated.py`, a stdlib-only dedicated-host script covering authenticated runsc readiness, unauthenticated rejection, both languages' correct submissions, wrong answer, compile/runtime errors, timeout, excessive output, idempotent retry and deletion verification. It refuses non-Linux execution. Only Python syntax was checked on this computer; the runner remains uninstalled and unexecuted here. Network/process/memory host enforcement still needs explicit dedicated-host proof.

## PDF parser lifecycle bounds

Resume parsing now reserves one parser slot with a one-second admission timeout instead of spawning a child per simultaneous upload. Busy callers receive an actionable retry/paste response. A `finally` block kills and reaps the child on timeout or request cancellation, and releases the slot; malformed child output gets an extraction error. Existing Linux worker address-space/CPU and input/page/text limits remain enforced. Two lifecycle regressions inject timeout and cancellation and verify kill, reap and slot release. Focused system suite: 26 passed.

## Mobile correction, dispute, persistence and deletion browser acceptance

The synthetic-provider browser journey and recovery scripts both passed after making the harness wait for history loading before counting deletion rows. At 360 px, correction produced a preserved original plus candidate version; a challenge marked the new observation disputed; provider selection saved to OpenRouter, persisted across reload and switched back to Groq; deleting the interview removed its history row. Document width remained 360 px and no browser JavaScript errors were captured. Evidence: `browser-recovery-results.json`, `screenshots/report-mobile-corrected-360.png`. This proves UI/persistence integration in the synthetic acceptance environment, not real provider routes or hardware audio.

## Hardware prerequisite revalidation

After filesystem/network permissions changed, WSL Ubuntu became accessible. `nvidia-smi` on Windows and Ubuntu identified NVIDIA GeForce RTX 4050 Laptop GPU with 6,141 MiB VRAM (Windows driver 610.62). Ubuntu's default Python is 3.14.4; the voice dependency install selected Python 3.11.17 via uv. The local speech environment is being provisioned under the ignored voice `.venv`; this is application speech software only. No runner/Docker/gVisor installation or execution occurred. Current faster-whisper documentation confirms CUDA 12 cuBLAS and cuDNN 9 requirements; Linux-only dependencies are now declared explicitly. GPU identification is not evidence of successful model inference or latency acceptance.

## Actual Ubuntu speech runtime installation

The live WSL install completed with Python 3.11.17, Pipecat 1.13.0, faster-whisper 1.2.1, CTranslate2 4.8.3, Kokoro ONNX 0.6.1, cuBLAS 12.9.2.10 and cuDNN 9.27.0.42. `VoiceManager._load_runtime()` succeeded against these installed packages. This supersedes earlier package-absence observations; model inference is still unverified.

Provisioning first failed because `Systran/faster-whisper-large-v3-turbo` is not a publicly available model ID. The public former Mobius repository redirects to `dropbox-dash/faster-whisper-large-v3-turbo`; live Hub metadata returned MIT license and revision `0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf`. The script now uses that pinned conversion revision. A download is running; no model success is claimed yet. Voice locks were regenerated with the explicit Linux GPU dependencies. No runner software was installed or executed.

## Installed transport API proof

WSL runtime inspection confirmed `SmallWebRTCConnection.send_app_message` exists in installed Pipecat 1.13.0, and verified the Silero analyzer and PipelineParams constructors used by the adapter. Added `evals/local_speech_check.py` to exercise real Kokoro synthesis and CUDA Whisper transcription on three synthetic utterances, recording cold warmup, per-attempt synthesis/transcription latency and actual recognized text. It explicitly distinguishes HF offline mode from OS-level network blocking. This check has not run yet because the Whisper weight download is still live and incomplete; the specific HF process was revalidated rather than restarted.

## Actual local WebRTC transport acceptance

`evals/webrtc_transport_check.py` negotiated a real local aiortc client with installed Pipecat SmallWebRTC, using no external ICE servers, speech models, microphone, cloud or runner. The peer reached `connected` and received the exact server JSON over channel `pipecat`. The first run exposed an actual cleanup bug: installed Pipecat provides `disconnect()`, not `close()`. Adapter cleanup and early-failure cleanup now use `disconnect`; rerun exited successfully. Evidence: `docs/webrtc-transport-results.json`. Added an idempotent cleanup regression; nine voice helper tests pass. This transport test does not establish browser audio or model-pipeline behavior.

## Unified installation and asset URL correction

The main API now declares a locked `voice` optional dependency set so production startup does not require manually merging separate virtual environments. `apps/api/run-local-speech.sh` selects Python 3.11, syncs the exact main lockfile into ignored local data storage, sets CUDA library search paths and starts one worker. A real unified installation is running.

Whisper model download completed. Kokoro provisioning then exposed another stale scaffold URL: v1 weights are under the official `model-files-v1.0` release, not `model-files`. GitHub's live release API confirmed both asset names/URLs; the provisioning script was corrected and its download is running. Earlier weight-availability statements remain superseded only when actual downloads and warmup complete.

## Provisioning completed; real model check started

Whisper and Kokoro v1.0 ONNX/voice assets finished downloading. The unified WSL API environment installed successfully (95 packages, Python 3.11.17). Bash syntax checks passed for application startup, speech check, model provisioning and the Ubuntu runner installer; syntax checking did not install or execute the runner. Actual CUDA Whisper/CPU Kokoro warmup and three synthetic speech checks are running through `evals/run_speech_check.sh`. No inference result or latency claim is made until that process completes.

## Actual CUDA STT and CPU TTS results

`bash evals/run_speech_check.sh` completed on WSL Ubuntu, RTX 4050 6 GiB, Python 3.11.17. Real Whisper large-v3-turbo CUDA `int8_float16` and Kokoro ONNX CPU loaded and passed warmup. Initial process warmup took 57.266 seconds. Three synthesized 3.179-second English utterances were transcribed exactly, with nine timestamped words each. TTS durations: 1.036, 1.060, 1.064 seconds; STT durations: 0.321, 0.318, 0.303 seconds. Raw evidence is `docs/local-speech-results.json`.

These are three repeated synthetic utterances, not a transcription accuracy benchmark, hardware microphone check, meaningful-audio end-to-end p50/p95, or browser interruption result. HF offline mode was enabled but OS networking was not disabled for this first run. A separate OS-isolated network-namespace run is now executing; the check verifies only loopback interfaces before claiming network isolation. The runner remains untouched.

## OS-isolated offline speech passed

The second actual STT/TTS run completed inside `unshare --user --map-root-user --net`, with only loopback present. Both models warmed and all three synthetic utterances transcribed exactly. Evidence: `docs/local-speech-offline-results.json`. Warmup took 34.496 seconds; CPU TTS took 1.332/1.103/1.061 seconds, CUDA STT 0.326/0.367/0.307 seconds. This establishes local model execution without external network connectivity after provisioning. It does not establish cloud-independent adaptive interviewing, human-speech accuracy, physical microphone operation, browser playback or end-to-end latency.

Added `evals/voice_pipeline_check.py` to exercise real SmallWebRTC + VAD + model pipeline with synthetic silent uplink and synthesized downlink, playback acknowledgments and interruption. It is running; no pipeline success is claimed until completion.

## Real model/WebRTC downlink observed

The actual voice pipeline check completed successfully: real SmallWebRTC transport, Silero VAD, local models, synthesized downlink frames, matching text delta and interruption message. It observed 63 received frames and first non-silent decoded audio 0.842 seconds after submitting the local text. This excludes microphone endpointing/STT/cloud latency and is not the full latency target. Evidence: `docs/voice-pipeline-results.json`.

Installed Pipecat automatically enabled RTVI, logging warnings about this application's intentionally separate playback-ack messages. The pipeline now explicitly disables unused RTVI and uses the current add_workers/run API. A longer real-pipeline run is checking acknowledgment/backpressure over multiple seconds rather than stopping at first audio. Browser hardware and upstream speech behavior remain unverified.

## Sustained WebRTC audio/acknowledgment check

The extended real downlink run completed: 269 received audio frames, matching text, playback acknowledgments reaching 5,380 ms and zero pending server audio at the observation point. First audible decoded frame arrived 0.961 seconds after local text submission. The synthetic client also receives silence, so acknowledged elapsed media time is a delivery estimate rather than speech-duration or hearing proof. Interruption message arrived. This supersedes the first-frame-only evidence but does not prove a 200 ms browser stop target.

The check now injects Kokoro-generated English speech through an actual aiortc uplink track and waits for the VAD/Whisper answer callback. That specific live run is in progress. No physical microphone or provider is involved.

## Real upstream test exposed VAD frame mismatch

The initial real synthetic-uplink run timed out after Silero correctly logged speech start/stop. Installed Pipecat's VADProcessor emits `VADUserStartedSpeakingFrame` and `VADUserStoppedSpeakingFrame`, separate from the application-level UserSpeaking frames. TranscriptProcessor previously recognized only the latter. It now accepts both types. The failed run is not counted as a successful upstream check. A rerun after this correction is live; previous downlink success still stands independently.

## Real two-way local voice passed

After accepting the installed VAD frame types, the real WebRTC pipeline completed. Synthesized downlink reached the aiortc client, and the synthetic microphone phrase “I invalidated the cache after the write.” traveled through WebRTC, Silero endpointing and CUDA Whisper to the answer callback exactly. Metadata included seven relative words, session-aligned intervals and `recording_artifact: null` under no-recording consent. Matching text and interruption messages were received. Evidence: updated `docs/voice-pipeline-results.json` and ignored detailed runtime log.

The check uses an actual model/transport pipeline with generated audio, not a physical microphone or real cloud response. First audible downlink after local text submission was 1.430 seconds in this run. This is not speech-end-to-cloud-to-browser latency acceptance. A subsequent audit also expanded barge-in detection to queued/in-flight TTS and pending audio after cloud generation has finished; previously only ongoing text generation enabled VAD interruption. Voice helper tests remain nine passed.

## Browser/WSL real speech acceptance started

Started a separate loopback WSL acceptance API on port 8001 using real local speech and explicitly synthetic cloud responses. Runtime data is isolated under `data/voice-browser-acceptance`; the main backend now respects `VOICE_MODEL_DIR` independently of session storage. `evals/browser-voice.cjs` runs Chrome with a labeled fake microphone device, creates an authenticated consented session, enables the real speech connection, repeats the persisted question, observes actual speaking state and checks Stop. The test is running; it does not involve a physical microphone, real provider or runner.

## Browser real-voice test did not pass

Chrome negotiated the real WSL WebRTC connection and the server committed the repeated text, but the browser never entered actual speaking state before the test deadline. No browser voice success is claimed. A client handoff race was found: voice text for a new generation may arrive before its HTTP state response; the client previously discarded it, then kept playback muted. The client now checks mismatched generation IDs against authoritative server state before accepting playback, rather than accepting stale messages or dropping valid early ones. Further investigation/rerun remains required because server synthesis activity also needs confirmation for this path.

## Voice handoff diagnostic harness

Added an authenticated synthetic-harness-only voice diagnostic endpoint that reports generation ownership, queue size and sender/pipeline task health without transcript payloads or credentials. Production `interviewer.main:app` does not include this endpoint. It will support the next browser rerun so failed playback can be traced to actual queue/task state rather than inferred from animation. The frontend handoff fix compiled successfully.

## Current integrated regression run

`pytest apps/api/tests apps/api/interviewer/voice/test_manager.py apps/runner/tests`: **51 passed**, one TestClient deprecation warning. Runner checks remain static; no candidate execution occurred here. Browser voice diagnostics initially returned 404 because the built-site catch-all mount preceded the harness-only route; the harness now registers its diagnostic route before that mount. This is a test harness routing correction, not evidence that voice playback passed.

## Interruption/output ordering investigation

Browser diagnostics showed matching new generation IDs, live sender/pipeline tasks and an empty clause queue, but no synthesized output. Pipecat's worker interruption is enqueued asynchronously and is transformed into an InterruptionFrame later; a newly queued speech frame could be discarded by that delayed flush. The adapter now waits for that actual interruption frame to traverse the output boundary before allowing the next generation. This is an event acknowledgment, not a decorative timer. Real browser rerun is required to confirm the diagnosis; no pass is claimed yet.

## Browser voice verification completed

The real Chrome/WebRTC check now passes with local Whisper/Kokoro and synthetic cloud responses. The interruption barrier waits for the old interruption frame to traverse transport output before a new utterance is queued, preventing the old interruption from flushing the new utterance. The client also reconciles early assistant-text events against the authoritative generation.

Evidence: `docs/browser-voice-results.json` and `docs/screenshots/browser-real-voice-speaking.png`. The browser observed the speaking state and Stop cleared it in 68 ms, with no page errors. This measures a UI state transition, not acoustic silence. The microphone was a Chrome synthetic device; physical microphone, real provider calls, repeated-interruption stress, and dedicated-host runner acceptance remain unverified.

After these changes, the combined API/voice/static-runner suite passed 51 tests and the frontend production build passed. The build retains the Monaco chunk-size advisory; tests retain the Starlette TestClient deprecation warning. No runner was installed or executed on this computer. The Ubuntu installer remains `apps/runner/install-dedicated-ubuntu.sh`, to be run from a source checkout on the separate Ubuntu PC.

## Real browser barge-in and failure recovery

The extended `evals/browser-voice-recovery.cjs` uses real Chrome Web Audio, WebRTC/Opus, Pipecat, Silero VAD, CUDA Whisper and CPU Kokoro, with a synthetic microphone utterance and synthetic cloud responses. It exposed and fixed a deadlock: application cancellation awaited interruption traversal from inside the processor that needed to forward that interruption. Application callbacks now run in owned tasks outside the frame loop and are cancelled during connection cleanup. Spoken answers also publish authoritative state updates so the browser sees committed transcripts and the next generation.

Media-only disconnection now pauses and invalidates the authoritative session even when SSE remains connected. Replaced/abandoned connection attempts cannot acquire microphones after leaving the screen, and old peer callbacks cannot change a newer peer. Lifecycle events are forwarded over the data channel as well as SSE. STT errors offer explicit retry/typing. A TTS outage releases synthesis waiters, clears output, preserves displayed text, and requires reconnect for further speech.

The browser failure injection caught a second concrete bug: the message decoder treated the text `message` field in a direct `voice_error` as though it were a nested packet, silently dropping the actionable error. Only object-valued envelopes are now unwrapped. The recovery screen was visually inspected in `docs/screenshots/browser-voice-tts-failure.png`.

The recorded successful extended run in `docs/browser-voice-recovery-results.json` passed repeated Stop, actual synthetic-browser-mic STT, VAD barge-in, explicit versioned transcript correction, reload pause, reconnect without replay/duplicate questions, injected TTS failure followed by typed continuation, media-only disconnect pause, and abandoning warmup without microphone acquisition. It produced no page errors. Stop-to-audio-element-muted/paused measurements were 58/35/41 ms in that run; these are not acoustic-silence measurements or a latency benchmark. Whisper transcribed “cache” as “cash”; the original remained preserved and the test corrected it explicitly.

Visual inspection also exposed Repeat selecting an interrupted fragment after a correction cancelled a question. Repeat now selects the latest complete persisted question; if none exists, it rejects before mutation and directs the candidate to retry explicitly. The combined source test suite after this correction passed 55 tests. The final browser rerun after that backend change is recorded separately when it completes. The frontend build passed with its existing Monaco advisory. Real providers, physical microphone, and dedicated runner enforcement remain unverified; internal contract-audit gaps also remain.

The final browser rerun after the complete-question Repeat correction also passed every extended recovery assertion, with no page errors. Updated result artifact: `docs/browser-voice-recovery-results.json`; Stop-to-muted/paused samples: 54/40/29 ms (n=3). These supersede the earlier samples only for the current recorded run, not as a performance distribution. The updated outage screenshot was inspected and now retains a complete question while showing the actionable synthesis failure and typed input.

## Local schema validation and factual report ownership

`Providers.structured` now validates results against the exact authored JSON Schema with `Draft202012Validator` and an explicit local-only `referencing.Registry`. New locked dependencies are jsonschema 4.26.0 and referencing 0.37.0. Local `$defs` references work; external references cannot retrieve resources. Wrong types (including numeric `1` in a boolean slot), extra properties, malformed/non-finite JSON, malformed envelopes, refusals and incomplete generation are rejected with a typed unavailable-assessment error. Structured timeouts retain their distinct timeout classification. No cross-provider retry is introduced. Real provider checks remain unavailable.

Live stream parsing also rejects malformed event/choice/delta/content shapes, preserves final usage-only events, and marks length-limited or empty output incomplete/unavailable instead of presenting it as a completed question. Usage-only events do not count as first usable content.

The new `interviewer/assessment.py` owns factual statement records and their validation. Answers/corrections commit observations with the same transaction and revision as their source event. Reports validate owned utterances, exact preserved source text/version, event identity and quote spans; they rebuild fixed factual inference text rather than trusting arbitrary persisted prose. Invalid or numeric-rated records are excluded. Older sessions can derive a missing current observation read-only and dispute it through the normal versioned mutation. Corrected text does not inherit an original-audio interval.

This trace exposed an existing correction-event bug: a payload `kind` field overwrote the event's authoritative type. Store event identity/type/stage/revision/time now take precedence over payload keys, and corrections retain `correction_kind` separately. The validator recognizes the previous correction-event representation for compatibility.

All ten authored criteria are displayed with null ratings, available source links, and explicit `not_observed`/`insufficient_evidence` abstention. These are practice-record availability statuses, not technical judgments or diagnosed weaknesses. Stale/disputed statements do not contribute current source links. Topics reflect actual answer/reasoning/submission events rather than merely entered/skipped stages. Automatic technical assessment and code review are explicitly unavailable; the full evaluator/coach ownership audit remains open.

The combined suite passed 89 tests before the last topic-list correction; its focused system rerun covers that correction. Production frontend build passed with the existing Monaco advisory. Windows and WSL API environments were synced from the updated main lock; no runner installation occurred. The integrated synthetic-cloud browser journey passed with ten visible criteria and working evidence navigation. Mobile correction/dispute/settings/deletion passed, with document width exactly 360 px at a 360 px viewport and no page errors. Desktop/mobile criterion screenshots were visually inspected. The real local-model browser recovery also passed again after factual-observation changes: synthetic mic/cloud, Stop-to-muted/paused samples 53/49/36 ms, transcript correction, barge-in, reconnect, injected TTS outage, typed continuation, and abandoned warmup checks. These remain scoped synthetic checks, not provider or physical-microphone acceptance.

## Voice backpressure, generation frames, and bounded input

Installed Pipecat source confirmed that default `push_frame` queues downstream work rather than waiting for its processing. The previous queued audio guard could therefore block while TTS continued filling a queue ahead of it. The guard now uses native `enable_direct_mode=True`. Native TTS `context_id` and speech-frame metadata carry an immutable generation, replacing the ad hoc pending-generation deque. Late old frames/completion signals are rejected independently of mutable sender state. Typed answers cancel pending prior audio before starting a new generation, including after the old text completed.

Browser acknowledgment accounting now uses the HTML audio media clock only after audible samples are detected, caps progress to generated-audio notifications, and resets for each generation. It runs independently of decorative rendering. Idle time cannot prepay later audio. The server ignores malformed/stale/duplicate acknowledgments and clamps credit to generated frames. A locally stopped generation is suppressed while its cancellation is in flight; Repeat waits for the outstanding mutation so rapid Stop/Repeat does not use a stale revision.

The real Chrome/local-model recovery test withheld acknowledgments and measured exactly 1,000 ms pending transport audio, with only one 20 ms offered frame waiting before the guard. Restoring acknowledgments resumed playback without a Repeat request. This measures the application transport window, not the total model batch, native transport, browser jitter buffers, acoustic silence, or proof of hearing. The active Kokoro batch and bounded batch lookahead remain separate.

Decoded active speech is capped at 120 seconds; Keep thinking is capped at 32 segments/12,000 characters. Limit handling explicitly pauses/closes voice, preserves an editable bounded draft and reason under the session's retention/deletion policy, and submits no partial answer. Done speaking now collects its forced endpoint before committing one combined answer. STT is bounded to a 15-second application wait, and its uncancellable native worker stays owned until it finishes; readiness blocks reconnect while that task is busy. Late results are discarded.

`browser-voice-recovery-results.json` now includes the slow-client proof and an injected near-limit held draft followed by real browser/VAD/STT input. That limit path saved exactly 12,000 characters, paused/closed voice without creating an answer, then accepted one reviewed shorter typed answer. All previous barge-in, correction, reconnect, TTS-failure and abandoned-warmup assertions also passed with no page errors. Stop-to-muted/paused samples in this run were 54/42/41 ms (n=3), not a performance distribution or acoustic measurement.

The updated actual local-model/WebRTC script withheld `finish_text` until after first audible output, then supplied a later clause. It passed: first audio arrived 1.2849 seconds after the first clause, before stream completion (n=1). Actual synthetic upstream STT also passed. Evidence: `docs/voice-pipeline-results.json`. This is local transport/TTS evidence with no cloud or physical microphone, not the required full speech-to-meaningful-audio p50/p95.

Final combined source suite: 98 passed, one existing Starlette TestClient warning. The production frontend build passed with the existing Monaco size advisory. Runner checks remained static; no runner installation or execution occurred. Full latency instrumentation, delivery provenance, TTS cancellation concurrency and remaining contract audit work are still open.

## Delivery provenance and measured latency

Voice now emits bounded lifecycle snapshots for each generation: generated/displayed character counts, admitted audio duration, estimated played duration, peak pending audio, and first text receipt/display/playback milestones. The API validates ownership, generation, numeric bounds and matching persisted assistant turns, appends diagnostic events without changing action revisions, and projects the latest snapshot into session/report turns. Deleted sessions reject late snapshots. Reports label playback as estimated, never proof of hearing. The browser records display after React commit and playback after measured audible samples.

Speech metadata now records server-clock VAD endpoint, estimated speech end (endpoint minus configured silence), STT start/completion, while assistant turns record request start and first usable content. Voice adds first TTS clause/chunk and audio admission. Browser timestamps use a separately labeled browser clock; latency samples subtract only browser-clock values. VAD estimates and synthetic source ends are explicitly distinguished from physical speech.

Cancellation audit found Kokoro's async stream can leave a native inference batch running after its wrapper is cancelled. The application now owns one public `Kokoro.create` call per complete clause, outside the event loop, shielded until completion with a 15-second caller wait. Later clauses cannot overlap an uncancelled native task. Late output is generation-rejected. This preserves clause-level incremental transport, but a long individual clause must finish synthesis before its frames are sent; no sample-level model streaming claim is made. A threaded regression proves cancellation does not overlap the next model call.

Combined tests after delivery/TTS changes: 101 passed, one existing Starlette TestClient warning. Frontend production build passed with its existing Monaco advisory.

Actual Chrome/WebRTC/VAD/CUDA Whisper/CPU Kokoro latency measurement used ten synthetic spoken answers and synthetic cloud responses. The first diagnostic run polled SQLite-backed session state every 100 ms and measured p50 7.070 s / p95 10.566 s; it is preserved at `docs/browser-latency-polling-baseline-results.json` with that overhead caveat. The revised measurement waited on native browser playback markers instead of polling during inference: n=10, p50 4.847 s / p95 5.302 s; warm subsequent n=9, p50 4.849 s / p95 5.314 s. Targets of 2 s / 4 s were missed. Raw markers, interpolation method, environment and synthetic limitations are in `docs/browser-latency-results.json` and `docs/browser-latency-default-cpu-results.json`. Recorded process model warmup was 43.883 s; the revised run used already-loaded models. Real provider latency and physical microphone timing remain unavailable.

A local CPU profile compared Kokoro's default thread setting with 1/2/4 threads, three synthesis samples each. Median synthesis was 1.285/2.673/1.813/1.486 s respectively. The existing default performed best in this bounded comparison; no speculative thread setting was applied. Evidence: `docs/tts-cpu-profiles.json`. These isolated model samples do not override the integrated target miss.

## Deletion authority and complete shutdown

Deletion now inserts the tombstone and removes the owned session transactionally before its first asynchronous cleanup wait. Previously the session remained writable while voice/cloud cleanup awaited, leaving a window for a late spoken answer or mutation. Cleanup then cancels generation without consulting deleted voice state, closes voice, removes files, and retries remote cleanup under the existing pending-cleanup contract. A regression invokes a late answer from inside voice cleanup and proves the session and tombstone have already revoked authority; a failed filesystem cleanup remains explicitly pending.

Application shutdown now awaits the cancelled retention task, closes every voice session even when its cloud generation already completed, and awaits cancelled runner-request workers. VoiceManager owns close_all rather than leaving connection enumeration to the API. Tests cover closing two idle voice connections and repeatable cleanup. No dedicated runner was installed or executed.

## Real PDF extraction acceptance

Generated synthetic text PDFs were passed through the actual extraction subprocess, rather than a mocked parser. This exposed a launch-directory dependency: `python -m interviewer.extract` could not resolve the module when the API was imported from another working directory. The subprocess now executes the absolute sibling `extract.py` path using the current interpreter. A valid two-page PDF extracts with correct page/offset provenance; offsets now include the newline that joins PDF pages in the displayed review text.

The real worker checks encrypted PDFs, blank/image-only equivalents, malformed PDF, 21-page input, and text exceeding 50,000 characters. Additional API checks cover unsupported extensions, invalid UTF-8, 10 MiB upload overflow, and non-object JSON. Non-object resume JSON now yields an actionable validation error instead of an attribute exception. These fixtures are synthetic and make no OCR or arbitrary-PDF compatibility claim. Linux worker resource limits and timeout/cancellation cleanup remain as previously implemented; Windows typed development does not provide Linux address-space limits.

## Explicit dialogue topic ownership and prompt loading

The production dialogue now loads `prompts/live_interviewer_v1.md` and additionally loads `prompts/coach_v1.md` for the coached stage. Previously those versioned files existed but an inline live prompt owned the actual behavior. Backend topic context now explicitly identifies a current confirmed claim, selects role objectives, and marks permitted transitions after two completed answers per topic. After the role's objective cycle, it selects the next confirmed claim. This is deterministic coverage scheduling, not an inference that answers are correct, complete, or competence criteria resolved. The provider remains responsible for wording a relevant follow-up/neutral clarification within those boundaries, with no extra planner/evaluator call per turn.

Coached context requests a candidate-selected objective when one is absent, and labels guided practice once supplied. The regression verifies multiple confirmed claims, objective cycling, trusted versioned prompt use, and absence of the fresh case's hidden diagnosis. Real provider conversational quality, explicit resolved/unresolved-point tracking, and the remaining evaluator/code-review audit remain open.

## Stage-specific live context and public coding allowlist

Audit found the live coding interviewer had role objectives but no authored problem statement, so it could not reliably discuss the actual editor task. Coding context now includes the selected role/experience problem's statement, stdin/stdout contract, public examples and language, with a permitted approach-discussion action. Baseline/fresh stages explicitly select disclosed-evidence discussion; review requests a candidate-selected objective under unavailable technical assessment. These remain conversational boundaries, not model authority to transition stages or reveal cards.

A shared public coding projection now allowlists schema version, ID, title, statement, contract and public tests for both browser and live context. It excludes hidden-test-set pointers as well as private/future fields; the previous denylist could accidentally expose newly added private properties. Parameterized regressions cover all three roles and confirm the live/browser contract matches, hidden pointers are absent, and transfer context does not retain the coding problem. This proves payload construction, not real provider coding-dialogue quality or dedicated execution.

## Corrected live-memory provenance

Live extractive memory previously paired corrected text/version with the original answer event ID. It now uses the same version-indexed statement-source lookup as factual report validation and requires an exact source-text match. Corrections made in a later stage remain discoverable because source lookup spans the owned session's events, while topic selection still uses stage-local answers. A regression corrects a dialogue answer during the baseline stage and verifies that revisiting dialogue context cites the correction event and v2 text, never the original misheard event. This is provenance validation, not a correctness inference or replacement for the complete transcript.

## Provider catalog failure normalization

Model and OpenRouter downstream catalog parsing now validates response envelopes before replacing cached catalogs. Malformed JSON/shapes become typed `malformed_output` errors; network failures and timeouts remain distinct. A failed catalog fetch preserves the previous catalog and cannot commit changed settings. OpenRouter route discovery and configuration preflight now share the provider-owned endpoint method rather than bypassing its error boundary in the API. Model IDs are validated before endpoint lookup. MockTransport regressions cover malformed catalogs, retained cached data, route timeouts and connection failure; these are not real-provider connectivity evidence.

## Current integrated and focused accessibility recheck

The current combined API/provider/voice/static-runner suite passed 122 tests, with one existing Starlette TestClient deprecation warning. The browser journey was rerun against a newly started isolated synthetic-provider API after all recent backend changes: setup, adaptive typed follow-up, baseline evidence/conclusion, explicitly skipped coding, review/coached/fresh/report, ten criteria and evidence navigation passed with no page errors. Mobile correction, dispute, settings persistence and deletion passed again, document width 360 at viewport 360.

`evals/browser-accessibility.cjs` adds actual keyboard-only interaction for landing example opening, focus cycling inside its dialog, Escape dismissal, owner-key sign-in, Settings navigation and opening setup. Chrome reduced-motion emulation confirmed no continuously animated sphere descendants. No microphone/warmup/signaling or provider-test requests occurred, no page errors, and no horizontal overflow at 360 px. Evidence: `docs/browser-accessibility-results.json`. This focused check does not claim a full keyboard interview/report exercise, screen-reader conformance, every focus-return behavior, or comprehensive accessibility certification. Those remaining audit scopes stay open.

## Practice-action stage and pause boundaries

The session service now rejects evidence/hypothesis/conclusion actions outside the current baseline/coached/fresh exercise, practice-objective selection outside review/coaching, and practice mutations while paused. Only resume, pause, stop and end remain permitted while paused. Guided hints require an explicitly selected practice objective, preserving the safe-mode distinction between candidate-selected practice and a diagnosed weakness. Rejections roll back revision/events atomically. Evidence/reasoning/hint controls reflect these boundaries in the client. Fifty focused system tests passed, including rejection/no-write checks and explicit objective-before-hint behavior. These checks do not establish the remaining evaluator or real-provider acceptance.

## Runner uncertainty after application restart or network loss

Application restart now persists a remote cancellation record for each interrupted queued/running submission while marking its local result infrastructure failure. It never reruns candidate source. A failed remote create/poll likewise queues cancellation because a timed-out request may already have been accepted remotely. New submissions are blocked while any runner cleanup remains pending, preserving the one-job invariant across uncertain remote state. The existing cleanup worker retries authenticated deletion and removes the cancellation record only on success/404. The regression seeds an interrupted job, recovers it, verifies durable cancellation and infrastructure status, and confirms a new submission is rejected without mutation. This is application-state proof; dedicated Ubuntu execution/cancellation enforcement remains unverified and no runner was installed or executed here.

## Runner response integrity and cleanup retry proof

The application now validates remote job identity, known lifecycle status, and result-envelope shape on create and poll. Malformed/mismatched responses become infrastructure failures with durable cancellation, instead of leaving a queued submission after an unhandled decoding error or accepting another job's result. MockTransport checks supply invalid payloads, return 503 on the first cancellation and 404 on retry, and verify the cleanup record survives failure and clears only after acknowledged absence. Only synthetic HTTP messages were exchanged; no candidate code or runner process executed. This envelope check does not replace dedicated-host isolation acceptance or full semantic execution-result validation.

## Microphone lifecycle status

Browser listening state now requires a live, enabled, non-muted audio track. Disabled, device-muted or ended tracks instead show a static dimmed sphere and actionable microphone-unavailable text; actual interviewer playback may still show speaking. Pause-driven track enablement is separated from generation changes so a new question cannot re-enable a disabled track. The extended real-WebRTC/synthetic-microphone acceptance explicitly disables the browser input track, checks muted status with no listening sphere, and re-enables it before the remaining recovery journey. The frontend production build passed; browser result is recorded when that run completes.

The microphone lifecycle browser run completed successfully: disabled input never appeared listening, re-enabled input returned to listening, and all extended voice recovery assertions passed with no page errors. Evidence: `docs/browser-voice-recovery-results.json`. Cloud responses and microphone source remained synthetic; local speech/WebRTC were real. Stop-to-muted/paused samples were 37/37/37 ms (n=3), not acoustic latency or a performance distribution.

## Candidate-controlled execution cancellation

The coding workspace now offers Cancel execution while its attempt is queued/running. The authenticated session-bound cancellation endpoint uses expected revision/idempotency, verifies job ownership, preserves immutable submitted source, records cancellation atomically, cancels the local request worker, and queues/retries remote cleanup when configured. Cancellation is explicitly not a candidate failure. A late remote response cannot overwrite a submission that is no longer queued/running. Tests cover owned cancellation, identical retry without duplicate events, rejection of a new cancellation on a finished attempt, and unknown-job rejection. No candidate code executed locally; actual remote cancellation still requires dedicated-host acceptance. The frontend production build includes the control.

## Prepared dedicated-host behavioral probes

The dedicated Ubuntu acceptance script now includes default-route absence/denied external-connection checks, a bounded fork attempt with children held behind a pipe, active-job cancellation, and a known-good job after cancellation. Probe source executes only when this script is run against the dedicated authenticated runner; nothing was installed or executed on the application computer. Python syntax compilation passed. The script reports limitations explicitly: these checks do not independently prove cgroup/kernel policy, all network paths, memory/GPU/filesystem hardening, or host security. Actual results remain unavailable until the owner runs it on the separate Ubuntu PC.

## Language-specific coding drafts and editor browser check

Python and C++ now have separate in-memory editor drafts with appropriate starter syntax. Switching languages restores that language's draft rather than carrying Python into a C++ attempt. Immutable submitted snapshots remain unchanged; unsent drafts are still not promised to survive reload. The language selector now has an explicit associated label after the real browser check could not identify its previous implicit accessible name reliably.

The integrated synthetic-provider browser journey now actually loads Monaco, switches to C++ and observes the C++ starter, then switches back and observes the Python starter before explicitly skipping execution and finishing review/coaching/fresh/report. It passed with no page errors; the production build passed with the existing Monaco size advisory. No runner or candidate source execution occurred. Evidence: `docs/browser-journey-results.json` includes `language_specific_editor_starters`.

## Current-source completion audit clarification

The contract audit was refreshed against current session/report source. It identifies incomplete immutable authored-content provenance (sessions reread role/scenario/coding/rubric files), generic rather than event-grounded unresolved questions, incomplete response-schema coverage, and outstanding browser/real-host cancellation proof. Existing safe factual review, topic scheduling, prompts, coding allowlists and recovery tests are credited only for their actual scope. These are internal requirements, so the task remains active and is not classified as blocked solely by missing provider credentials or dedicated-host access. See `docs/contract-audit.md` for the concrete remaining work; no completion claim is made.

Current combined suite revalidation: 129 passed, one existing Starlette TestClient warning. This includes static runner checks only, not dedicated execution.

## Transcript-grounded open questions

Live context and reports now derive conversation progress from persisted turns and exact current-version answer/correction events. Repeated identical wording within a stage is one conversational point with repeat IDs; complete questions with no recorded reply appear explicitly in the report. Incomplete/interrupted text does not become a completed question and breaks automatic reply pairing. A reply records only that a candidate response exists, including uncertainty; it never establishes technical resolution, correctness, or audio hearing. The generic calibration sentence is no longer used as the report's unresolved-question list. The new report copy explains skipped/unheard possibilities and abstains from competence judgments. Fifty-six system tests and the frontend build passed; the pairing regression was rerun after the incomplete-turn guard. Full semantic unresolved-detail tracking and real-provider dialogue quality remain separate audit work.

## Immutable authored content and execution identity

New sessions capture private copies of role, scenario, causal reference, rubric, public coding contract, and live/coach prompt content. Session views expose only a provenance status and digest; private references remain outside live model and browser context. The frozen-content regression removes access to the current content/prompt directories and still exercises dialogue context, evidence disclosure, coding projection, and report generation. Legacy sessions remain explicitly unpinned; no original version is invented.

Coding submissions now carry the SHA-256 digest captured from the complete public problem and hidden test record. The dedicated runner checks that digest against the same in-memory content it will execute before any candidate container is created. Both public-example and full-suite requests reject changed public or hidden content. The digest participates in job-ID idempotency. Legacy sessions lacking this execution identity reject submission before a job is saved. The dedicated acceptance client computes the digest from target-host authored files.

Verification here executes only the extracted JSON content loader and static source checks, never the runner service, Docker, gVisor, or candidate source. Loader regression checks matching public/full suites and rejects separate statement and hidden-test changes. Real dedicated-host enforcement remains unverified. Frontend dependency installation was explicitly approved; the production build passed with the existing Monaco chunk advisory. npm reported two low-severity dependency vulnerabilities; no forced breaking upgrades were applied.

## Integrated keyboard journey and focus ownership

Added `evals/browser-keyboard-journey.cjs`, executed against the normal production web bundle and the isolated synthetic-provider browser harness at port 8002. All web interactions use Tab, Enter, Space, selection keys and typed keyboard input; locators inspect and wait rather than click or force focus. Browser-native consent, correction, dispute and deletion dialogs use Playwright's dialog API, so this is not evidence of physical keyboard operation inside native dialogs or screen-reader conformance. No microphone/warmup requests occurred, no candidate code executed, and no real cloud request was made.

The journey covers sample Escape with trigger restoration, skip navigation, owner access, provider configuration/test, resume review and claim editing, answer-dependent follow-up, pause/resume, evidence disclosure, hypothesis and conclusion confirmation, stage-heading focus, Python/C++ starters, actual Monaco keyboard editing and Tab exit, unavailable-runner recovery, selected practice objective, authored hint, fresh conclusion, completion, report evidence navigation, versioned transcript correction, current-observation dispute and local deletion. The report preserves the superseded statement as stale and the current challenged statement as disputed. Both remain excluded from conclusions. Results are in `docs/browser-keyboard-journey-results.json`.

Focus now moves to the page heading after screen/authentication transitions, to the applicable exercise heading after stage changes, back to the sample trigger on closing, to linked report sections, and to the history heading after deletion. A visible-on-focus skip control bypasses navigation. Monaco has an explicit accessible name, starts with Tab navigation enabled and shows its documented Ctrl+M / macOS Ctrl+Shift+M toggle. Context7's official Microsoft Monaco accessibility guide was consulted; the installed declaration also confirms `tabFocusMode`. Monaco's native EditContext has no visible bounding box but is keyboard focusable, so the acceptance helper checks actual focus rather than requiring its input box to be visually sized.

The journey exposed reasoning drafts carrying from baseline into fresh tasks. Hypothesis and conclusion drafts now clear on stage change; the explicit practice objective persists. Task stages select the compact workspace by default, including when reopening a saved coding/evidence stage. Screenshot review additionally found Monaco's default light theme and concatenated timeline metadata; the editor now uses `vs-dark`, and timeline labels and stage/time metadata occupy separate lines. Reviewed viewport artifacts: `keyboard-coding-focus-mobile.png`, `keyboard-report-focus-mobile.png`, `keyboard-report-focus-desktop.png`; full-page captures are retained alongside them. Both tested widths had document width equal to viewport width (360 and 1440 px). No page errors were observed.

Repeated runs exposed an independent concurrency defect: successful provider-stream completion incremented the action revision between a candidate's confirmation and the next request. Successful text delivery now updates its transcript, delivery diagnostics and generation-finished event without changing the action revision. Provider failure still increments the revision, pauses the session and replaces its generation, so an action based on pre-failure state remains rejected. The regression completes a generation after a committed hypothesis and then confirms a conclusion using the same action revision; it also checks that failed generation invalidates the old revision. The final browser journey waits for actual action responses and checks HTTP success rather than silently proceeding after a failed confirmation.

Verification: production TypeScript/Vite build passed with the existing Monaco chunk advisory; focused keyboard/reduced-motion acceptance passed; the full keyboard journey passed after the generation-revision fix. The combined API/voice-helper/runner-content suite passed 133 checks before that final fix, and the updated system suite passed 59 afterward. Dedicated-runner checks remain source/content checks only. Full technical inference, semantic unresolved-detail tracking, remaining schema/security audit, latency targets, real providers, physical microphone, dedicated Ubuntu enforcement and human calibration remain separate unfinished requirements.

Final revalidation after the successful-generation revision fix: 134 combined API, voice-helper and runner-source/content checks passed in 45.00 seconds, with the existing Starlette TestClient deprecation warning. The current production build and complete keyboard journey passed; the latest saved keyboard result corresponds to this backend revision behavior. No runner service or candidate code ran on the development computer.

## Typed public responses and private-field boundaries

Added `apps/api/interviewer/responses.py` as the public HTTP contract. Every JSON API route now declares its response model. The models use strict declared value types, reject non-finite numbers, and filter undeclared fields rather than copying whole stored or provider records. Unset optional legacy fields remain omitted. Fixed provider maps and role levels require both supported selections; safe assessment models require null ratings, disabled automatic ratings, and explicitly unavailable technical assessment/code review. Candidate-facing session/report structures include typed claims, provenance, provider snapshots, transcript versions and delivery diagnostics, events, coding contracts, factual observations, references, criterion coverage, execution results and aggregate hidden counts. Available evidence-card models cannot contain undisclosed card text. Known pricing components and route/model metadata are separately allowlisted.

`Sessions.view` now selects declared public session fields instead of copying a stored record and removing one private key. It reuses validated factual observations, preventing unsupported stored findings from appearing through session responses while the report already excludes them. Private content snapshots, creation fingerprints, idempotency request keys, provider internals, unknown timing fields and hidden-test inputs/outputs have no corresponding public fields. Internal API calls that return dictionaries still pass through the outer route response model. Authentication's explicit cookie response is constructed from the public auth model before serialization.

App-originated notifications are validated with a bounded-field envelope before SSE or WebRTC dispatch and must match the subscriber session. The streaming response itself remains a native event stream, rather than pretending to be a JSON response model. Voice-manager-specific data-channel messages remain separately constructed from scalar fields and retain their existing voice tests; this change is not a new blanket audit of all transport messages.

Malformed declared output returns a generic 500 without serializing or logging validation diagnostics, since those diagnostics may include complete private stored/provider values. Request validation returns only location, message and error type, omitting rejected input and context objects. Public auth, signaling and mutations reject extra request properties. Non-ASCII owner tokens, cookies and CSRF values use byte comparisons and receive ordinary authentication rejection instead of Python's string-comparison error. Malformed/negative/oversized Content-Length values are rejected, and security headers/no-store now apply to early middleware errors as well as normal responses. Header-only limits do not prove a general streaming request-body bound; the existing resume/file parsers retain their own limits and broader resource review remains open.

Regression evidence includes private canaries injected into stored session fields, confirmed claims, provider config, transcript/timing, references, public coding contract/examples, revealed evidence, events, submissions and nested execution diagnostics. Actual HTTP session, mutation, report and job responses preserve valid public evidence while removing canaries; hidden outcomes contain only passed/total. Mocked catalogs/routes drop unknown metadata, signaling drops runtime fields, invalid stored values fail closed, and malformed request validation never echoes credential/context canaries. Notification tests reject a mismatched channel and filter unknown fields. Two pre-existing fixtures with incomplete synthetic jobs/turns were corrected to match actual persisted records rather than weakening required output fields.

Verification: 141 combined API, voice-helper and runner-source/content checks passed (one existing Starlette TestClient warning). After the final malformed-header handling edits, 19 focused authentication, validation, response, signaling, catalog and notification checks passed. The complete synthetic-provider keyboard journey also passed with the strict response models, including settings, resume/claims, dialogue, evidence, Monaco, safe runner outage, coaching/fresh, report correction/dispute and deletion. No real provider, physical microphone or dedicated runner execution is claimed. Context7's current FastAPI response-model documentation was consulted for nested filtering, exclude-unset behavior and explicit Response bypass handling. Full security/retention audit, real integrations and other open contract items remain active.

The browser harness was then restarted with the final authentication/header edits. After its startup was confirmed, the complete keyboard journey passed again with no page errors or microphone requests, matching 360/1440 px document widths. An initial attempt before the new server had finished starting received connection refused; no application journey had begun in that attempt. The successful rerun supplies the latest saved browser result. Frontend sources and the previously built production bundle were unchanged during this response-boundary work.

## Retention crash recovery and owned cleanup

Retention now removes a completed `delete_on_close` session even when its normal expiry is still in the future. This handles a crash between committing completion and the HTTP deletion path. Startup awaits the same cleanup pass used during runtime before serving requests. The pass expires records, cancels orphaned request tasks, closes retired voice connections, removes session artifacts and retries remote erasure. Tombstones remain durable throughout. A failed close or filesystem removal for one session leaves cleanup pending and does not stop cleanup of other retired sessions. Resolved artifact aliases and invalid IDs are rejected rather than followed into another directory.

Submissions persist `remote_attempted=False` when created. The backend commits `True` immediately before any remote network await. Expiry, cancellation, deletion and restart queue remote cleanup only when dispatch may have occurred; legacy records without the marker conservatively require cleanup. An unavailable, never-dispatched attempt therefore no longer leaves an impossible remote cleanup obligation. Lost POST responses still require cancellation. The marker is internal and absent from the public response schema. Deletion awaits cancelled application job tasks before returning.

Voice connections remain owned until cleanup succeeds. A failed disconnect can retry while its recording is released in a finally block. Delivery-diagnostic failure cannot prevent transport/recording release. A separately owned, shielded close task prevents cancellation of its caller (including a voice callback being cancelled by shutdown) from abandoning cleanup. Successful cleanup removes only the same connection instance from the manager; replaced connections cannot be removed by an older cleanup callback.

Proof: 149 combined API, voice-helper and runner-source/content checks passed, with the existing Starlette TestClient deprecation warning. Regressions simulate a crash after delete-on-close completion with persisted answer, idempotency records, upload consumption, an undispatched job and a synthetic recording file; the next cleanup removes all associated data and permits a new session. Separate checks cover dispatch intent before mocked POST, restart before dispatch, transient media and file failures across repeated passes, path alias rejection, diagnostic failure, and cancellation of a cleanup waiter. No runner service or candidate source was executed. Real local-model browser recovery is being revalidated separately; synthetic unit failures do not prove physical media behavior.

Real local-model recovery revalidation completed successfully against the updated WSL backend: `docs/browser-voice-recovery-results.json` records real Chrome/WebRTC, CUDA Whisper and CPU Kokoro with synthetic cloud and browser microphone input. Repeated Stop-to-muted/paused samples were 53/45/36 ms (n=3, UI/media state only, not acoustic silence). Slow-client audio remained at 1,000 ms pending plus one 20 ms offered frame and resumed without Repeat. VAD barge-in, actual upstream transcription, explicit versioned correction, reload pause, reconnect without replay/duplication, injected TTS failure with typed continuation, media-only disconnect, held-draft limit recovery, disabled-mic state and abandoned warmup all passed with no page errors. This supplies transport/model proof for the cleanup changes; physical microphone and dedicated runner acceptance remain unavailable.

## Explicit ownership and cross-session reference audit

Added focused HTTP regressions for a stored foreign-owner session and upload. Authenticated access to session state, report, SSE, submission status, typed answers, state actions, corrections, disputes, code submission/cancellation, signaling, session deletion and abandoned-upload deletion all return 404. Foreign history is omitted. Exact before/after session bodies, events, immutable submission contents, upload ownership, tombstones and remote cleanup queue prove that rejection does not mutate or delete the foreign records. No inference or runner process is invoked.

A second regression creates two sessions owned by the installation and attempts to use the first session's utterance, finding and submission IDs under the second session's URL. All three reject with 404, with both session bodies and the job unchanged and no cancellation queued. This distinguishes owner authorization from the additional session-reference boundary. Both focused regressions passed (one existing Starlette TestClient deprecation warning). Existing broad suite evidence remains 149 passed before these two added tests; it has not been relabeled as a newly run 151-test suite. These cases strengthen the ownership evidence but do not establish a complete security audit or real dedicated-host authorization.

## Strict consent and action input types

All Pydantic request models now use strict type validation in addition to rejecting unknown fields. Cloud, recording and potentially-paid provider consent require actual JSON booleans; strings such as `"true"`/`"yes"` and numbers no longer coerce into permission. Action revisions, duration and claim provenance numbers likewise require their declared types, including rejecting booleans as integer revisions. Model configuration uses the existing Pydantic dependency; current official strict-mode documentation was fetched through Context7. Valid browser requests already send these exact JSON types, so no UI or stored-data migration is needed.

New HTTP regressions test both session consent fields with strings, numbers and null, confirm no session/events are created, reject string/float/bool action revisions without changing state, and reject coerced paid consent before provider validation is called. These checks strengthen consent boundaries; they do not establish the validity of a human's consent or provider billing availability.

Verification: the complete system/provider test selection passed 137 checks in 38.75 seconds, with the existing Starlette TestClient deprecation warning. This run includes the ownership and new strict-consent regressions plus mocked provider error/stream/schema cases. It does not include the voice-helper/runner suites in its count and does not claim a new real-provider or browser run.

## Explicit dialogue clarification and uncertainty actions

The session service now recognizes a small explicit set of standalone clarification/rephrase requests and uncertainty declarations, using the exact current-version answer event. Clarification selects `rephrase_current_question`; uncertainty selects `offer_narrower_question_or_skip`. Context retains the last completed same-stage question before that answer with its turn ID, plus the candidate request's event ID, utterance ID and source version. Application policy instructs neutral rewording without supplying an answer or changing topics, or a narrower question/explicit skip choice without judgment. No stage changes, correctness findings or semantic-resolution claims are inferred. Longer substantive answers containing uncertain wording remain ordinary adaptive follow-ups; this is intentionally an explicit-request recognizer, not a general intent or competence classifier. Existing review/coaching objective guards retain priority.

Eight focused dialogue/context regressions passed, including current question identity, exact source provenance, ordinary substantive answers, and correction replacing a help request with a substantive answer. Corrected text removes the obsolete request classification and uses the new event/version in memory. The checks inspect real session prompt construction; no real cloud response quality is established. Semantic resolved/unresolved-detail tracking and real-provider dialogue acceptance remain unfinished.

## Local Host-header boundary

HTTP middleware now rejects unrecognized request hostnames before serving either static pages or API routes. Allowed names are localhost, IPv4/IPv6 loopback, and the exact hostname in `FIELDNOTE_ORIGIN`; no wildcard or subdomain allowance is inferred. The origin check remains separate for mutations, and owner-cookie/CSRF checks remain required. This addresses requests reaching the local listener through an unrelated hostname, including DNS-rebinding-style Host values; it is not a substitute for loopback binding or HTTPS when intentionally deploying on a LAN. Configuration examples document the exact-host behavior.

Six focused host/authentication regressions passed. Unrelated, lookalike and suffix domains cannot read landing/auth/health/settings or mutate settings, and settings remain unchanged. Loopback names and an explicitly configured deployment name are accepted while its unconfigured subdomain is rejected. The test harness explicitly configures its synthetic `testserver` origin; production defaults do not accept that hostname. No DNS attack or real LAN deployment was performed.

Final combined API/provider, voice-helper and runner-source/content revalidation passed 177 checks in 56.55 seconds, with one existing Starlette TestClient deprecation warning. This includes ownership, strict consent, explicit dialogue-help and Host-boundary regressions. No runner service/candidate code or real-provider call ran in this suite.

## Received request-body bounds

Added a small pure ASGI middleware that caps actual received bytes for API writes at 11 MiB and applies a 30-second body-receive deadline. It runs inside the existing authentication/Host/CSRF middleware, so rejected requests do not reach the pre-read allocation. Accepted bodies are buffered within that bound before JSON or multipart parsing; overflow, timeout and disconnect cannot commit a partial action. Content-Length remains an early rejection optimization, not the source of truth. The existing 10 MiB file, page/text and parser limits remain enforced separately. This intentionally buffers bounded uploads at this single-user concurrency; it does not add streaming storage or a new dependency.

Pure ASGI tests cover missing and understated length headers, multi-chunk overflow before downstream invocation, exact-boundary replay once, timeout and abandoned requests. An HTTP regression sends a chunked resume without Content-Length, checks 413 plus no stored upload and no-store, then verifies a valid small upload still succeeds. Five focused body-boundary checks passed. Current FastAPI ASGI-middleware registration documentation was checked through Context7. No real slow-network attack or proxy behavior is claimed.

The system plus body-limit selection passed 103 checks in 41.00 seconds before adding the final HTTP chunked-upload regression. That regression and the four underlying ASGI cases then passed together. One existing Starlette TestClient warning remains. These runs execute no candidate code or real cloud provider.

## Runner job termination after budget breach

Source inspection confirmed stdout/stderr already share the 64 KiB captured-output budget. It also found that after a case timeout/output breach killed the case container, the suite could launch the next candidate case. The runner now stops the suite after container cleanup on either boundary. The terminating timeout/output outcome takes priority over earlier wrong-answer/runtime outcomes in the job summary. No subsequent hidden cases are counted as attempted.

Ten runner source/content checks passed, including an AST regression locating the timeout/output stop guard after the case's finally cleanup. No service, Docker, gVisor or candidate source was executed here. Dedicated-host acceptance now asserts first-case budget failures produce one public outcome and zero hidden attempts, and includes a finite combined 40,000-byte stdout plus 40,000-byte stderr probe. The acceptance script passed syntax compilation only; actual enforcement remains unverified until run on the owner's separate Ubuntu PC.

## Runner-result consistency before persistence

Remote job responses now pass through the strict public execution schema before storage, not only on the later HTTP response. Unknown outcome names, negative/inverted aggregate counts, missing completed outcomes, active jobs with final results, mismatched cancellation/infrastructure outcomes, inconsistent public totals and false passing summaries are rejected. Compiler failures require a nonzero exit; compiler timeout/output boundaries remain valid without fabricated test outcomes. Unknown remote fields are filtered before persistence. Existing transport-error handling converts rejected results to infrastructure failure and queues conservative remote cleanup, rather than publishing them as candidate failures.

The dedicated runner now marks returned infrastructure-error outcomes with infrastructure lifecycle status; restart records include that same explicit kind. This is a source change only on this computer. Twenty-seven focused application/runner source checks passed, including valid test/compiler outcomes, contradictory envelopes, and a mocked false-passing result that becomes infrastructure failure with retried remote cleanup. One existing Starlette TestClient warning remains. No runner service or candidate code executed, and no actual dedicated-host result is claimed.

## Browser execution cancellation

Added an opt-in held-task mode to the isolated synthetic browser harness (`ACCEPTANCE_HOLD_RUNNER=1`). It replaces only the harness's submission worker with a waiting application task; production startup does not import this harness. No runner service, remote dispatch or candidate execution occurs. `evals/browser-cancel-execution.cjs` uses real owner access, settings, session creation/progression, source persistence, UI submission, cancellation endpoint and report generation.

The Chrome check passed: the visible Cancel execution control cancels the held attempt, disappears after terminal status, preserves the immutable Python source, and produces a cancelled coding outcome plus exactly one cancellation event in the factual report. The 360 px document width equals viewport width and no page errors occurred. Evidence is in `docs/browser-cancel-execution-results.json` and `docs/screenshots/cancel-execution-mobile.png`; the screenshot was inspected. This completes application/browser cancellation-path proof for this harness, not dedicated-host termination or sandbox cleanup proof. Real dedicated Ubuntu cancellation remains required.

## Reachable exercise Stop/status/question controls

Coding and synthetic evidence stages now include a compact sticky toolbar showing the actual current interviewer text, existing lifecycle status and a Stop interviewer control wired to the same cancellation/playback action as the main voice controls. It does not create a timer-driven voice state or a separate generation path. The toolbar remains visible while scrolling the task workspace. Mobile coding headers wrap the problem title onto its own row and keep the Language label intact. The shell now uses overflow clipping rather than an unintended hidden-overflow scroll container, which browser verification identified as preventing sticky positioning.

The production build passed with the existing Monaco chunk advisory. Expanded browser cancellation acceptance scrolls to the actual Monaco editor at 360 px, asserts the toolbar is inside the viewport, compares its question with the main current question, activates Stop and verifies HTTP success, then submits/cancels the held application task. All checks passed, with no page errors or horizontal overflow. `coding-sticky-controls-mobile.png` was inspected; the full cancellation screenshot was refreshed. No cloud or runner execution occurred. Evidence-stage rendering shares the same toolbar, but this run specifically proves the coding scroll path.

## Question skips and clarification-aware topic scheduling

Consolidated standalone dialogue-request recognition into one session helper. Resume topic scheduling now counts substantive responses, preserves the current topic budget for explicit clarification/uncertainty, and rounds forward to the next objective on an explicit question skip. Later answers retain that new position. Request recognition uses current transcript text, so correction naturally changes subsequent scheduling rather than leaving stale intent state. These are conversation coverage rules, never correctness or competence findings.

In resume dialogue, a standalone question-skip request permits a spoken transition to the next supplied role objective without stage progression. In synthetic/coding contexts it instead permits pointing to the explicit stage-skip control; plain candidate text cannot unlock references, reveal evidence or change the stage. Review/coaching objective guards keep their existing priority. This remains a small explicit phrase recognizer, not general semantic resolution or an assertion that all natural phrasing is understood.

Seven focused dialogue/context checks passed. The new integrated session regression submits clarification, uncertainty, a substantive answer, question skip and another substantive answer, checking objective retention/progression and unchanged resume stage. It then enters the baseline, submits the same skip phrase, and verifies unchanged stage and undisclosed cards. Real-provider wording quality remains unverified; semantic resolved/unresolved details are still an open contract requirement.

## Typed and spoken repeat requests reuse saved questions

Explicit standalone repeat phrases now use the same saved-text generation path as the Repeat button. Typed and local-STT answer entry points share the generation selector, retaining the candidate request and its input provenance while making no new cloud wording request for the repeat. Repeat requests do not consume the substantive topic budget. The repeatable-question helper now requires a complete question in the current stage, so an earlier exercise's question cannot be replayed after a stage transition. A repeat with no current complete question rejects before mutating the session.

Eleven focused repeat/dialogue/voice-entry checks passed. New tests cover missing-question rollback, exact saved wording passed to the local generation route, duplicate typed-request idempotency, cross-stage repeat rejection, and the shared local-speech selector preserving `local_speech` provenance. Existing local-repeat generation tests ensure the provider is not called. These tests do not claim a new physical-microphone run or broad natural-language intent understanding; recognition remains explicit standalone phrases.

## Frontend sanitizer advisories and artifact secret scan

Current npm audit identified two low-severity findings from Monaco's DOMPurify 3.4.15 pin (GHSA-p98j-92pf-mc4p and GHSA-6688-9rhm-gjv2). Added a narrow npm override to patched DOMPurify 3.4.17 and updated the lockfile. Inspection then showed Monaco also vendors its own sanitizer source: an override alone cleared the package audit while leaving the old shipped code in the build. Added a narrowly matched Vite alias for Monaco's relative sanitizer import to the patched installed ESM package. The production editor chunk changed and now contains the 3.4.17 version marker with no 3.4.15 marker. This alias and override should be reviewed together when updating Monaco; no framework downgrade or broad forced upgrade was used. Current Vite 6 alias documentation was checked through Context7.

Production build passed with the existing Monaco size advisory; `npm ls dompurify` resolves 3.4.17 and `docs/frontend-dependency-audit.json` records zero known npm advisories. Browser acceptance again loaded the real Monaco editor, exercised sticky Stop, submitted/cancelled only a held application task, preserved immutable source and report state, and found no mobile overflow/page errors. No actual candidate execution occurred.

Added `evals/check_web_artifact.py` for repeatable post-build inspection. It scans known credential/private-key patterns plus any configured server secret values without printing values, and detects the obsolete vendored sanitizer marker. The current run scanned 19 production files, found no matches and confirmed the patched editor chunk. Zero configured secret values were available for exact matching, so this proves pattern absence in the frontend artifact only, not a complete secret scan of backend responses/logs or a guarantee of no secret formats. Evidence: `docs/public-artifact-secret-scan.json`. Re-run after rebuilding with `apps/api/.venv/Scripts/python.exe evals/check_web_artifact.py`.

## Request-aware factual conversation progress

The same current-version, event-linked request recognizer now owns question progress as well as topic scheduling. An explicit repeat, clarification, uncertainty or skip receives its own factual status rather than `reply_recorded`. These points remain in the report's conversationally open questions. A later substantive reply or transcript correction changes the derived status; nothing persists a stale intent. The live prompt distinguishes these statuses from substantive replies and explicitly forbids treating a recorded reply as technical resolution. No semantic-resolution or competence inference was added.

Five focused regression cases passed, including each request category, substantive replies and corrected-source replacement. The integrated Chrome keyboard journey was rerun against a fresh current-backend harness on port 8004: setup, evidence, Monaco editing and Tab exit, safe runner outage, coaching, fresh transfer, report correction/dispute and deletion passed, with zero page errors or horizontal overflow at 360/1440 px. It used a synthetic provider, no microphone and no candidate execution. Native dialogs were automated through Playwright, not a screen reader.

The technical evaluator/code-review ownership audit is complete for the current uncalibrated mode: factual source validation belongs to `assessment.py`; technical inference remains explicitly unavailable. Unconnected inference prompt files are not evidence of an executable calibrated assessor. Semantic dialogue tracking, latency improvement, real-provider checks and dedicated-host enforcement remain separate unfinished requirements.

Current combined API, voice-helper and runner-source suite: 203 passed, one existing Starlette TestClient deprecation warning. Runner tests did not start the service or execute candidate code.

## Background conversational memory and six injected repairs

`interviewer/dialogue_memory.py` now owns a bounded, provisional conversational
coverage cache. After two new substantive replies, the application may run one
structured request on the session's frozen selected assessment model/route. The
request starts after the live spoken/text response finishes, never before it.
The next live response cancels background work; pause, correction, disconnect,
deletion, expiry and shutdown share owned cancellation. Failure leaves recent
turns and extractive event memory available and cannot pause the interview or
create a technical finding.

The model selects groups of related question IDs and exact answer quotes rather
than inventing a prose summary. It may also select question excerpts to revisit.
Application validation enforces closed schemas, maximum six groups/six details,
current owned event IDs and source versions, verbatim quotes/excerpts, same-stage
sources and chronological source availability. Help-only replies cannot become
substantive answered points. A full transcript signature prevents late publication
after a new turn or correction; a prefix signature invalidates previously cached
coverage immediately when a source changes. The cache is versioned and private;
the report exposes only its typed selected-source projection. No raw audio,
private references, hidden tests, code execution or numeric assessment is involved.

Source validity does not prove semantic accuracy. Open details are presented as
provisional suggestions to revisit and may already have been covered. Live prompts
give recent turns and the latest answer precedence and ask the model to avoid
repeating information already supplied, including paraphrased questions. Actual
semantic grouping accuracy and real-model repeated-question avoidance remain
unverified without a configured real provider. The Settings snapshot continues to
select both models; Setup now discloses potentially paid background grouping calls.

Twenty focused memory checks passed, covering grouping of paraphrases, exact
source validation, extra/invented/foreign/stale sources, request-only replies,
cross-stage/chronological limits, correction invalidation, deletion/pause/new
generation/new answer races, failure fallback, bounded work and live preemption.

`evals/browser-dialogue-memory.cjs` completed against a fresh synthetic backend and
the production frontend. It observed available grouped coverage in the report,
then repaired six injected recognition-like mistakes: cache/cash, p50/p95,
milliseconds/seconds, validation/invalidation, primary/replica and a negation.
Each original remains preserved at version 1; the candidate correction becomes
version 2; original observations become stale; current factual observations use
the corrected text; dependent memory becomes unavailable; criterion ratings stay
null; deletion succeeds. The injections entered through the shared typed-answer
path, not through six real STT recordings. This is correction/recovery evidence,
not acoustic accuracy or human assessment calibration. Evidence:
`browser-dialogue-memory-results.json` and desktop/mobile conversation-memory
screenshots. Chrome reported no page errors or 360 px overflow.

Two additional HTTP canary regressions passed with HTTPX MockTransport: the
configured synthetic server credential was inserted into an upstream authentication
error body or malformed structured response. It remained absent from serialized
provider errors, settings/readiness/history responses and captured logs/stdout/
stderr. This tests those exact paths, not all possible log sinks or real keys.

Final verification for this change: combined suite 225 passed with one existing Starlette TestClient deprecation warning; TypeScript/Vite production build passed with the existing Monaco size advisory. The complete keyboard browser journey passed again with zero page errors and 360/1440 px overflow checks. Conversation-memory desktop/mobile screenshots were re-rendered after quote-attribution spacing changes and inspected. The rebuilt frontend scan checked 19 files, found no credential-pattern matches and confirmed patched DOMPurify; zero configured secret values were available for exact comparison. No runner service or candidate code ran on this computer.

## CPU synthesis alternatives and native pronunciation

Inspected the integrated latency markers before changing defaults: representative
warm turns spend roughly 0.6 seconds in endpoint silence, 0.6 in STT, about one
second waiting for the complete synthetic provider clause, and 1.7 in synthesis,
with transport/browser overhead afterward. The existing ten-turn integrated
target miss remains the production-path evidence; isolated timings do not replace it.

`evals/tts_precision_profiles.py` compared the existing FP32 Kokoro v1.0 model with
the upstream release's INT8 model on the same CPU, voice, speed and question. Each
profile had warmup and three measured synthesis samples, followed by six synthetic
technical prompts transcribed by local CUDA Whisper. Median synthesis was 1.326
seconds for FP32 and 4.931 seconds for INT8. INT8 is therefore not a latency
improvement on this machine, and the application/provisioning default remains
unchanged. The extra model is only an ignored local comparison asset. Its exact
upstream release URL, byte size and computed SHA-256 are in
`tts-int8-asset.json`; measured samples and round-trip transcripts are in
`tts-precision-profiles.json`. Checksums identify the downloaded bytes and are not
an independent signature/provenance attestation. No runner was installed or run.

`evals/speech_pronunciation_check.py` additionally compared native Kokoro
phonemization against manual letter-spacing of acronyms. All three original
technical prompts round-tripped through actual local TTS/STT with their terms
preserved (API/TTL, HTTP/HTTPS/SQL, and C++/JSON/UI). Manual letter-spacing changed
the first transcript to “How did you repeat I use a TTL?” and offered no demonstrated
improvement on the others. The experimental application mapping was removed;
native phonemization continues to own pronunciation and the original text is
unchanged. Reproducible comparisons remain in the evaluation script, with result
scope in `speech-pronunciation-results.json`. This small synthetic round trip is
not human listening review, natural microphone accuracy, or universal acronym
coverage.

## Hidden-page rendering and explicit media disconnection

Source audit found that hidden tabs skipped level sampling but still scheduled
the visual requestAnimationFrame loop. The application's existing page-visibility
handler already paused most sphere layers; its selector missed the animated
pseudo-element and it did not initialize the class for an initially hidden page.
That existing handler now initializes/cleans its class, and its CSS covers the
pseudo-element as well. The voice hook cancels its visual frame handle on
hide and resumes when visible, with listener/frame cleanup on disconnect. The
separate media-clock playback-credit timer remains active; it is transport
accounting, not decorative rendering.

The expanded real-model browser recovery run then found a genuine disconnect
gap: closing the native browser peer and releasing local audio did not promptly
pause the backend, which still reported a connected session after the test's
30-second wait. The fix uses an authenticated, revision-checked `disconnect`
session action rather than relying on ICE timeout. The session service owns its
pause/generation invalidation; the route cancels background/live generation and
closes voice resources. Local teardown remains immediate. Concurrent revision
changes permit one fetch-and-retry; cleanup failure preserves the committed
pause and returns a generic actionable error. A repeated action key retries
cleanup without duplicating the persisted event. Closed transport callbacks no
longer schedule recursive cleanup during an already-owned close.

Six focused disconnect checks passed, including exact idempotency, stale revision
rejection, an injected filesystem/transport cleanup failure with later retry,
interrupted generated text, and suppression of recursive close callbacks. The
current combined API/voice-helper/runner-source suite passed 228 checks, with one
existing Starlette TestClient deprecation warning. The production frontend build
passed with the existing Monaco chunk advisory. A focused 360 px browser check
also passed injected visibility events, paused sphere/pseudo-element animations,
visible restoration, reduced motion, keyboard navigation and no microphone/cloud
calls. These injected events test the application handlers, not an OS-level tab
visibility measurement.

The final expanded recovery rerun passed with actual Chrome/WebRTC, CUDA Whisper
and CPU Kokoro, synthetic cloud and browser-microphone input. It verified stopped
visual frame scheduling while hidden and resumption when visible, native peer
closure with an injected connection-state notification, local analysis-context
closure, authoritative pause, and removal of the server pipeline before Resume
was enabled. It also repeated the prior Stop/barge-in, bounded slow-client,
correction, reload/reconnect, injected TTS failure, held-input limit and abandoned
warmup paths. No page errors occurred. Stop samples were 30/46/31 ms to a muted
or paused HTML audio element, not physical acoustic silence. Evidence is
`browser-voice-recovery-results.json`; synthetic visibility/state events remain
explicitly distinguished from OS tab switches and physical network failures.

Recovery caught a second race while developing the fix: the backend could already
be paused by transport loss while the explicit disconnect cleanup was still
updating its revision. Resume could then submit a stale revision. The UI now
shows disconnect progress and disables Resume and the existing busy-guarded controls until owned
cleanup and authoritative refresh finish. This race passed in the final run.
The focused keyboard/reduced-motion check and rebuilt frontend artifact scan
also passed; the scan checked 19 files with no pattern findings and zero real
configured secret values available for exact matching.

## Serialized replacement offers and initialization ownership

Replaced the former allocate/register/close-prior ordering in `VoiceManager.offer`.
The manager now serializes offers, checks owned active state before side effects,
and completes shielded prior cleanup before allocating a new connection. Failed
prior cleanup remains in the registry for retry. Newly allocated connections are
registered with their initializing task before the first SDP-initialization await.
Failed or cancelled setup closes through the existing owned cleanup task; an
external close cancels initialization and waits for its cleanup. No separate
untracked connection owner was introduced.

Authoritative state is rechecked after warmup, SDP initialization and worker
registration. A changed generation, pause, completion or deletion rejects the
obsolete offer and releases resources before a pipeline can publish. An accepted
offer clears its initialization-task reference. Runtime/OS offer failures return
a fixed API error instead of native error details.

Ending/completing an interview now explicitly closes backend voice resources,
including retained interviews, rather than relying on the browser's peer closure
being noticed promptly. Delete-on-close completion enters the existing tombstone
and cleanup path first, preserving deletion even if voice cleanup fails. A failed
close of a retained interview leaves its committed completion intact and reports
cleanup pending.

Twenty-four fake-transport lifecycle tests prove prior-close-before-allocation,
failed cleanup ownership/retry, failures in SDP/answer/transport/recording/pipeline/
worker setup, cancellation of initialization, cancellation of the cleanup waiter,
external close, overlapping offers and late pause/completion/generation/deletion.
Six HTTP regressions additionally cover completion/retention/cleanup-failure
combinations and sanitized signaling errors. The combined API/voice-helper/runner-
source suite passed 258 checks with one existing Starlette TestClient warning.
These faults use fake transport primitives and no local speech or runner execution;
actual native signaling and real-model browser recovery are separate evidence.

Native testing found that the signaling library accepted malformed, audio-free
SDP and started an empty pipeline. The application now requires an offer with an
SDP version header and an active audio media port before closing any existing
connection or allocating another. Six regression cases cover malformed text,
header-only, invalid/disabled/out-of-range audio ports and data-only offers. This
is an application audio-capability check; the native library still parses SDP.

The expanded actual Chrome/WebRTC/local-model recovery rerun passed. Three
malformed offers returned 422 with no registered pipeline or voice generation.
Valid microphone signaling then succeeded. Repeated Stop reached muted/paused
state in 37/30/32 ms (not a measurement of acoustic silence); VAD interruption,
bounded playback credit, correction, reload/reconnect, injected TTS outage,
input-limit recovery, visibility suspension, peer-loss cleanup before Resume and
abandoned warmup passed with no recorded browser errors. Cloud output and browser
microphone input were synthetic. Evidence: `browser-voice-recovery-results.json`.

## Shared warmup ownership and standalone dialogue requests

Warmup previously held a lock only for the awaiting coroutine. Cancelling that
coroutine could release the lock while its native model-loading threads kept
running; an early failure in one loader could similarly leave its sibling alive.
Warmup now retains one shielded task shared by all callers and waits for both
loaders to settle before returning a failure. Models publish together. Threaded
tests cancel the first waiter, join a second waiter, and verify exactly one pair
of loads while a loader is held. They cover success, one failed sibling, retry
after failure, and reuse after success. These tests use fake models; they do not
claim physical GPU resource enforcement.

The dialogue audit confirmed existing provisional-memory guidance already tells
the live model to avoid paraphrased questions for supplied information, prefer
specific unresolved details, and defer to recent/current transcript versions.
No additional planner, mandatory model call or prompt layer was added. Explicit
standalone request recognition now accepts natural repeat/rephrase/skip variants,
polite prefixes/suffixes and typographic apostrophes. Mixed substantive answers
remain ordinary answers, so an uncertain clause does not discard supplied facts.
HTTP tests prove neutral clarification preserves the original question and source
event, correction replaces request intent, skip moves the dialogue topic without
changing stages or revealing evidence, and natural repeat reuses saved text once
without a cloud call. Real-provider conversation quality remains unavailable.

The full API/voice-helper/runner-source suite passed 265 tests, with one existing
Starlette TestClient deprecation warning. No runner service or candidate code
was run. Existing CPU-thread benchmarks were inspected rather than repeated:
default Kokoro threading already outperformed 1/2/4 threads in the recorded
three-sample comparison, so the runtime setting remains unchanged.

## Current requirement map and rendered contrast

`docs/acceptance-matrix.md` now maps every final acceptance-table area and delivery
artifact to current source/tests/results, with failures and external prerequisites
kept explicit. A bounded backend review inspected authentication/CSRF/Host,
untrusted context and backend authority, secret projections/errors, expiry,
abandoned uploads, tombstones, filesystem/remote cleanup and restart/late writes.
No additional concrete defect was found in those inspected paths. This is not a
general security certification.

Added HTTP proof for the same confirmed resume under backend/frontend roles and
two answer variants: four sessions retain identical claim context, distinct role
objectives, and exact current-answer/event links. This proves supplied context,
not actual provider follow-up quality. A separate expiry test removes an old
abandoned upload while preserving a recent upload and active session, and checks
that a consumed upload is removed from standalone storage. The combined
API/voice-helper/runner-source suite passed **267 tests** in 46.40 seconds, with
the existing Starlette TestClient deprecation warning.

The real-model warmup cancellation probe also passed with CUDA Whisper and CPU
Kokoro. It cancels the first waiter after native loading starts, joins the same
owned task from a replacement waiter and checks reuse after success. Exactly one
Whisper and one Kokoro constructor ran; warmup completed in 23.31 seconds.
`docs/warmup-cancellation-results.json` records the scope and actual result. Run:

```bash
SPEECH_CHECK_SCRIPT=evals/warmup_cancellation_check.py bash evals/run_speech_check.sh
```

Rendered contrast was checked using axe-core 4.14.0, installed only as a local
test tool under ignored `data/accessibility-tools`. It is not a production
dependency. The existing complete keyboard journey now optionally scans with
`AXE_CORE_SCRIPT` pointing to the local `axe.min.js`. Eighteen recorded screens
cover landing/example, authentication, settings/setup, dialogue/pause, reasoning,
coding outage, review/coaching/fresh, corrected/disputed report, and history,
including 360 px mobile and the desktop report.

Axe cannot resolve gradient backgrounds. Actual-render results are retained;
additional probes replace only the known decorative gradient surfaces with both
endpoint colors, then restore their original styles. The body endpoints include
the alpha composition of its radial overlay; panel/sample endpoints retain their
authored alpha. Guards reject changed gradients before reusing these bounds.
This approach preserves the shipped design and does not treat indeterminate
nodes as passing. The example speaker label failed the lighter endpoint at
4.37:1; its shared label color changed from `#88a0ba` to `#a4b8cd`.

After the change, the production TypeScript/Vite build and full keyboard journey
passed. All eighteen actual-render scans and both endpoint probes had zero
reported violations. Remaining indeterminate nodes are recorded: four landing
decorative/pseudo-element cases, seven example-dialog overlap/pseudo-element
cases, and six coding/Monaco overlap/hidden-input cases. The current mobile coding
and mobile/desktop report screenshots were visually inspected: the focused
controls, text and task hierarchy remain visible without horizontal overflow.
This is scoped contrast evidence, not full screen-reader conformance. Busy
controls are awaited through enabled/computed-opacity state before scanning so a
disabled-to-enabled mutation cannot be misreported as enabled low-contrast text.

To reproduce with the documented synthetic browser server on port 8002:

```powershell
npm install --prefix data/accessibility-tools --ignore-scripts --no-audit --no-fund axe-core@4.14.0
$env:AXE_CORE_SCRIPT=(Join-Path (Get-Location) 'data/accessibility-tools/node_modules/axe-core/axe.min.js')
node evals/browser-keyboard-journey.cjs
```

Set `PLAYWRIGHT_MODULE` and `CHROME_EXECUTABLE` as in README first. The current
production artifact scan again checked 19 files with no findings and the patched
DOMPurify 3.4.17 marker in `editor-Z60jWKMq.js`. Zero configured real secret values
were available for exact-value comparison. The existing Monaco bundle-size
advisory remains. No runner software or candidate code was installed/run here.

## WSL persistence cost and native-storage latency comparison

The streaming path durably saves generated text before publishing each delta.
Its existing default data directory is under the checkout, which is mounted from
Windows in this deployment. `evals/sqlite_storage_profiles.py` exercised that
same authoritative-read/transactional-recheck/save sequence using a synthetic
21,825-byte session and 60 growing deltas per filesystem. Median per-delta time
was 49.32 ms under the repository's `/mnt/c` data directory and 0.842 ms under
native `/tmp`; p95 was 55.78 versus 1.483 ms. Both temporary databases were
separate from existing user data. Evidence: `sqlite-storage-profiles.json`.

A separate actual Chrome/WebRTC/local-model benchmark then used a fresh native
WSL temporary data directory. The live backend process environment was checked
to confirm `FIELDNOTE_DATA=/tmp/fieldnote-native-latency.ICXlHP` before measurement.
No existing interview or owner-key file was moved. The same synthetic microphone,
synthetic cloud and browser-clock playback-marker method ran ten turns:

| Storage/run | Samples | p50 meaningful audio | p95 meaningful audio |
| --- | --- | --- | --- |
| Earlier Windows-mounted data run | 10 | 4.847 s | 5.302 s |
| Native WSL data comparison | 10 | 3.761 s | 4.819 s |
| Native comparison, subsequent warm turns | 9 | 3.722 s | 4.868 s |

The comparison still **misses** the 2/4-second targets. Its slowest turn was
5.257 s. Model warmup took 58.60 s and voice enable took 61.78 s; warmup was not
precompleted when Enable was clicked. The two runs were not randomized or
counterbalanced, so their entire timing difference cannot be causally assigned
to storage. The isolated persistence probe establishes the filesystem cost
directly; the integrated comparison shows a practical candidate improvement,
not a passed target or production-provider latency. Evidence:
`browser-latency-native-storage-results.json`, with server/STT/TTS/browser markers
and no recorded browser errors. The evaluation script accepts
`FIELDNOTE_LATENCY_RESULT_PATH` so comparisons do not overwrite the baseline.

README now recommends an explicitly chosen persistent native Linux data directory
for a **new** WSL deployment. `/tmp` was used only for synthetic acceptance and
must not hold retained interviews. The shipped data default and all existing
records remain unchanged; selecting a different directory is not a migration.

The synthetic server was stopped after the comparison and current hero/example
screenshots. Provider configuration preparation then created a previously absent
ignored `.env` from `.env.example`, with the built-site origin set to
`http://localhost:8000`, and started the actual single-worker speech backend via
`bash apps/api/run-local-speech.sh`. This is normal application startup, not the
synthetic provider harness. No provider keys were invented or printed and no
paid requests were authorized by this preparation. Real provider validation is
pending the owner's local credential/model/route/cost configuration.

## Real provider configuration and catalog compatibility

The owner saved both keys locally and approved synthetic tests with GPT-OSS
20B live/GPT-OSS 120B structured output on both providers, OpenRouter pinned to
Groq with fallback disabled. After restart, readiness reported both configured.
No credential values were printed or included in test artifacts.

Real OpenRouter catalog discovery exposed a compatibility defect: its catalog
now contains leading-tilde aliases that resolve dynamically to newer models. The
explicit-ID validator rejected the whole catalog because of those entries.
Context7's current OpenRouter latest-resolution documentation confirmed their
dynamic behavior. Catalog handling now omits these aliases and known automatic
routers while retaining strict validation of ordinary entries and rejection of
dynamic configured model IDs. Concrete `:free` variants remain selectable.
The real catalog then returned 446 eligible models. Five regressions cover mixed
catalog filtering and rejected dynamic selections.

Groq passed actual streamed live and strict structured-output requests using its
initial model pair. OpenRouter's approved Groq route returned 429. The owner then
approved advertised-free Liquid and Nvidia routes. The Nvidia structured route
returned 404; Liquid passed both live and structured smoke requests using
`liquid/lfm-2.5-2.6b:free` for both purposes. The application records the exact
explicit model and Liquid route; it does not enable automatic routing or fallback.
Current settings preserve Groq's separate GPT-OSS configuration.

An actual full interview prompt exposed a further issue hidden by the small
smoke request: Liquid's mandatory reasoning consumed the former 300-token live
budget and truncated its question. The API correctly saved an incomplete turn
and paused. A direct probe confirmed `finish_reason=length` at that bound. The
catalog marks reasoning mandatory; an attempt to disable it returned 400. A
bounded 1,200-token probe completed with `finish_reason=stop`. OpenRouter's live
budget is now 1,200, while Groq keeps 300 with its provider-specific low reasoning
settings. Structured output stays at 2,400. Routes, fallback prohibition and
application output bounds remain enforced. This is not a claim that all models
fit these bounds. Raw reasoning is never sent to the interview UI.

`docs/liquid-reasoning-budget-results.json` retains the synthetic paired probes.
`docs/real-provider-smoke-results.json` retains successful and failed real calls,
including tests after persisted settings and the budget correction. All inputs
were synthetic; local audio and real candidate data were not sent.

With real keys now present in `.env`, API tests explicitly clear inherited
provider/runner configuration per test. Individual tests then inject their own
synthetic credentials or transports. This prevents a developer's local
configuration from turning unit/HTTP tests into real integration requests.
The final combined suite passed **273 tests**, with one existing Starlette
TestClient deprecation warning. Runner tests execute no service or candidate
code. The frontend artifact scan checked both configured real key values across
19 files with no findings. A separate exact-value scan of the current application
log and named real-provider acceptance artifacts also found neither key.

## Real Groq dialogue and integrated browser journey

Four real Chrome/Groq sessions used one synthetic resume across backend/frontend
roles and TTL-only/explicit-invalidation answers. Opening questions followed the
supplied role objectives. Follow-ups differed with the answers: examples included
TTL selection, write-triggered invalidation, UI stale-data handling and refetching
after a write. The browser observed 12/45/30/46 distinct text updates in those
four recorded cases, including partial text before the final question. These
outputs establish recorded adaptive examples, not universal semantic quality or
avoidance of every possible repeated question.

The actual Groq browser journey also completed pause/resume, deterministic
baseline evidence/hypothesis/conclusion, both language editor starters, explicitly
skipped coding, authored review, a candidate-selected objective, coached hint,
fresh conclusion, completion, report, versioned transcript correction and a
finding dispute. All ten criteria remained without numeric ratings. Screenshots
were captured at desktop and 360 px widths. No microphone or runner request was
made by that typed journey. The script deletes only its own synthetic sessions;
it never clears another interview from history.

Evidence: `browser-real-provider-dialogue-results.json` and
`browser-real-provider-journey-results.json`. Reproduce against the approved,
configured real backend using `evals/browser-real-provider-dialogue.cjs`, adding
`--full-journey` for the integrated path. These are opt-in real-provider tests and
can incur cost. They must not be confused with the synthetic browser server.

## Free OpenRouter browser cases and real speech timing

After the provider-specific token-budget correction, all four actual
OpenRouter/Liquid browser cases completed with the same synthetic resume and
backend/frontend plus TTL/invalidation variants. Distinct browser text-update
counts were 30/27/57/30. Outputs asked about unresolved request persistence,
client state synchronization, stale cached UI data and invalidation triggers.
The successful run needed no retries. An earlier attempt encountered a real 429;
the driver now records at most two explicit Resume/Retry recoveries when a
numeric `Retry-After` is present, respecting that delay. It never changes routes
or providers automatically. This is test-driver behavior, not application
automatic retry. The app preserves partial/incomplete turns and pauses on error.
Evidence: `browser-real-openrouter-dialogue-results.json`.

Switching back to Groq preserved both provider-specific configurations. The
actual selected configuration remains Groq GPT-OSS 20B/120B; the separate
OpenRouter selection remains the explicit advertised-free Liquid model and
Liquid route. Both exclude fallback. Current catalogs and quotas can change;
these observations do not establish a permanent free default.

The latency driver now has an explicit `FIELDNOTE_REAL_PROVIDER` mode. It uses
the already-approved real backend configuration and local owner-key file without
printing it; it does not overwrite settings, grant cost consent, or delete other
sessions. Real mode runs three diagnostic turns with the existing synthetic
browser microphone. The normal ten-turn synthetic-server mode remains separate.
Only the session created by the driver is deleted in either mode.

The first actual Groq/Chrome/WebRTC/Whisper/Kokoro run completed three turns but
missed meaningful-audio targets substantially: p50 10.334 s / p95 11.734 s.
Persistence profiling and request/delivery markers identified synchronous
per-delta SQLite commits as an event-loop responsiveness problem. Generated text
now commits through `Sessions.update_generation_text` in a worker thread before
publication. That transaction rechecks owner, active generation, pause/completion
and the owned generating turn. A delayed write cannot publish after pause or
deletion; SQLite's transaction still owns the check and write. Usage-only chunks
retain metadata without an unnecessary text write. No uncommitted text is sent
to the browser or voice layer. Existing request revisions remain unchanged by
ordinary streaming.

Two held-commit regressions prove the event loop can run while persistence is
pending and that pause/deletion reject the delayed write without a delta or
session resurrection. The full API/voice-helper/runner-source suite then passed
**275 tests** in 89.48 s, with the same Starlette TestClient warning.

The first rerun exposed an instrumentation assumption: playback can now occur
before the provider request's final timing metadata is persisted. The driver
waits for that metadata before collecting the sample, while calculating latency
from the original browser playback timestamp. It does not substitute polling or
provider-completion time for playback.

The completed three-turn real-provider rerun measured p50 **5.201 s** / p95
**10.709 s**, with samples 11.321/4.296/5.201 s. All three local speech and real
Groq turns completed with no browser errors. The two subsequent warm samples
were 4.296/5.201 s; their n=2 distribution is diagnostic only. This small,
non-randomized comparison does not establish a causal performance improvement
or production p95. Both targets remain missed, including a large first-sample
outlier. The input is synthetic, not a physical microphone test. Recognition
mistakes remain preserved as original local-STT output, never silently repaired.

Evidence: `browser-real-provider-latency-before-async-storage.json` and
`browser-real-provider-latency-results.json`, including all milestone clocks,
sample counts, model state and provider configuration. Run the real test only
after selecting, saving and validating the approved configuration:

```powershell
$env:FIELDNOTE_REAL_PROVIDER='groq'
node evals/browser-latency.cjs
```

The latest exact-secret-value scan checked both configured keys across 47 saved
JSON artifacts/logs with no findings; the separate 19-file frontend scan also
found neither key. No key values were printed. These scans do not establish
absence of every possible sensitive value or log path. No dedicated runner or
candidate execution was installed/run on this computer.

## Minimal dedicated-runner distribution

`apps/runner/package_source.py` now creates an exclusive, allowlisted source
archive rather than asking the operator to transfer the whole application
checkout. The generated `data/fieldnote-runner-source.tar.gz` contains 18
regular files: required runner source, locks, image definitions, service,
installer, acceptance script, README, and coding/public-private JSON records.
It excludes `.env`, owner credentials, interview data, Python caches and
unrelated content. Private coding tests remain trusted-administrator material;
the archive must not be published to candidates. The installer copies only
coding and coding-private JSON content to the runner content directory.

An isolated distribution test planted synthetic secret/data/cache files both
inside and outside the runner directory, then verified exact archive membership,
absence of the planted contents, and refusal to overwrite an existing archive.
All 11 runner-source/distribution unit checks passed. `bash -n` accepted the
installer. Archive entries were compared byte-for-byte with current source;
`runner-source-bundle-results.json` records membership and archive SHA-256.
These checks execute neither the runner service nor candidate code and do not
establish actual Ubuntu installation or sandbox enforcement. The separate
Ubuntu host still needs installation and dedicated acceptance.

The user selected physical microphone acceptance next. The visible application
is currently at owner sign-in, which requires user action. No physical
microphone permission or recording was enabled, and no physical speech result
has been claimed.

## Streamed clause whitespace repair

Tracing the remaining latency path found a separate correctness defect in
`VoiceManager._take_complete_clauses`: after emitting a complete sentence,
the parser stripped the unfinished suffix. For provider deltas `Use Redis.
Then ` followed by `verify the key. Next`, this could synthesize `Thenverify`
although displayed provider text retained the space. The parser now preserves
the raw unfinished suffix; whitespace normalization still occurs only when
enqueueing a complete speech clause or flushing the final suffix.

A regression exercises this exact boundary and checks both emitted sentences
and the pending suffix. All 27 voice-manager tests passed. This is a text
preservation fix, not evidence of improved synthesis latency. The already-loaded
local speech process predates this source change; a normal backend restart is
required to load it. It was left running to preserve the prepared microphone
test and provider validations.

The backend was subsequently restarted normally to load the clause repair.
Local speech warmup succeeded in 40.661 seconds and direct Groq live/structured
revalidation returned HTTP 200. The saved OpenRouter configuration returned
HTTP 503 on this retest; it remains configured but currently unvalidated. Prior
successful OpenRouter evidence is historical and does not override current
availability. No route, model, provider or consent setting was changed to work
around this failure. `post-clause-fix-readiness.json` records this state. The
runner remains unconfigured and automatic ratings remain disabled.

## Interactive microphone check in progress

The user signed in and a synthetic backend-engineer context was prepared in the
visible in-app browser. Audio retention was off, and the displayed Groq text
processing disclosure was accepted for this synthetic check. The user then
operated microphone permission/connection. A subsequent browser observation
showed `Disconnect microphone`, `Listening`, and two recognized candidate turns:
`Hello, hello.` and `Hello, hello, testing, testing.` The transcript also showed
an assistant turn marked interrupted, followed by another generated response.
No synthetic browser microphone was injected by the agent for this check.

This is observed interactive connection/transcription evidence only. The user
has not yet confirmed audible output or Stop behavior, and no physical
speech-end/acoustic-stop latency was measured. An interrupted-delivery label
does not by itself prove audible playback stopped. The generated follow-up
included repeated wording and the later response said to move to the next
topic; this short greeting-only interaction is not evidence of complete
adaptive interview quality. The physical acceptance result remains pending
user observations and a substantive synthetic answer.

The user subsequently confirmed: **Heard speech; Stop worked**. This closes the
human-observed audible-output/Stop portion of this interactive check. Browser
state later showed additional recognized turns, estimated playback completion,
another interrupted response, and the interview paused. No measured acoustic
stop interval or latency percentile follows from this confirmation. Recording
remained off. Full substantive spoken-interview quality remains separate from
this short physical microphone/connectivity check.

Reviewing the observed dialogue traced two transition-only utterances to the
live prompt's underspecified `transition` instruction. The backend had stayed
in resume-role dialogue; model words had not advanced the stage. Application
prompt policy now explicitly requires a single question about the supplied
next objective in the same response, forbids a filler-only transition, and
distinguishes topic progression from a stage change. This is prompt guidance,
not a guarantee of universal model compliance.

One real Groq smoke sample used the application-built prompt in a temporary
database with the two synthetic greetings and the saved approved model
configuration. The selected action was `transition`, the objective was
`explain a confirmed storage or caching decision`, and the response asked:
`You mentioned using a cache invalidated after writes. What strategy did you
use to determine when and how to invalidate the cache?` It included the next
question rather than only a transition announcement.
`transition-question-smoke-results.json` records the exact bounded result.
This direct provider check did not mutate the user's active interview or
exercise playback. The live backend needs a normal restart to load this new
prompt-policy line; the existing physical microphone session was left intact.

## Latest integrated verification

The user reports the dedicated Ubuntu PC is not yet available. Its installation
and real isolation acceptance therefore remain external prerequisites; the
allowlisted source bundle is ready and no runner was installed here.

OpenRouter's unchanged approved configuration passed a subsequent synthetic
live/structured retest (HTTP 200), recorded in
`openrouter-revalidation-results.json`. After the final normal backend restart
to load the transition policy, it returned HTTP 503 again. This is intermittent
availability, not a stable pass or permission to switch routes automatically.
The latest runtime has Groq validated, OpenRouter configured but unvalidated,
local speech ready after 42.009 seconds of warmup, runner unconfigured and
automatic ratings disabled. `final-integrated-readiness.json` is authoritative
for this snapshot. The previously active browser tab was no longer available
when checking restart recovery; no browser recovery success is claimed here.

The combined API, voice-manager and runner-source/distribution suite passed
**277 tests in 66.08 seconds**, with the existing Starlette TestClient warning:

```powershell
apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests apps/api/interviewer/voice/test_manager.py apps/runner/tests -q --basetemp=apps/api/.pytest-final-integrated
```

`final-exact-secret-scan.json` records no exact matches for either configured
provider key in 59 production frontend and top-level JSON/log evidence files.
This scoped check does not prove absence of every sensitive value or log path.
The source bundle still matches its allowlisted runner/content sources; the
latest prompt policy and clause repair belong to the application backend and
are not runner files. Physical audible output and Stop are user-confirmed;
acoustic timing, full spoken quality, dedicated isolation and the previously
reported audio-latency misses remain distinct unresolved acceptance items.

## Dedicated installer account prerequisite

A source review found the installer relied on `useradd --system` implicitly
creating the identically named group, although subsequent directory ownership
and the service explicitly require `fieldnote-runner` as a group. That behavior
depends on host defaults. The installer now ensures the system group first and
passes `--gid fieldnote-runner` when creating the service user.

An unprivileged Bash check evaluated only the installer account-creation lines
with local mock functions replacing `getent`, `groupadd`, `id` and `useradd`.
It verified the group exists before user creation and that rerunning the lines
does not recreate the account. `bash -n` also passed. No actual system account,
Docker/gVisor installation, service, or candidate process was created. The
18-file source bundle was rebuilt, verified byte-for-byte against current
sources, and atomically replaced; its new digest is recorded in
`runner-source-bundle-results.json`. Real target installation remains untested
because the user reports the Ubuntu PC unavailable.
