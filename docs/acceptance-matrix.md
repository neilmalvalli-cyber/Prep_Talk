# Integrated acceptance matrix

Reviewed 20 October 2026 against the final acceptance conditions in `agent.md`.
This is a requirement map, not a completion claim. A synthetic provider verifies
application integration, not model quality, cloud connectivity or billing.
Source-only runner tests do not prove sandbox enforcement. The chronological
`acceptance.md` records commands, changes and earlier superseded observations.

## Candidate experience and integrations

| Requirement | Current authoritative evidence | Result and remaining scope |
| --- | --- | --- |
| Hero and navigation without implicit microphone/cloud access | `browser-results.json`, `browser-accessibility-results.json`; landing/example/navigation code in `apps/web/src` | Passed recorded Chrome journey; primary action visible, synthetic example labeled, no external requests on recorded landing load. |
| Desktop/mobile visual design, 360 px controls and task hierarchy | `browser-keyboard-journey-results.json`, `docs/screenshots/`; recorded 360/1440 px layout widths | Passed recorded screenshot/browser scope. |
| Sphere tracks actual voice/playback, muted state and interruption | `browser-voice-recovery-results.json`, `apps/web/src/useVoice.ts` | Actual Chrome/WebRTC/local models passed with synthetic microphone and cloud. Muted microphone does not appear listening. Physical microphone behavior remains unverified. |
| Reduced motion, hidden rendering, static fallback | `browser-accessibility-results.json`, `browser-voice-recovery-results.json`; CSS/visibility/visual-loop ownership | Passed reduced-motion and injected visibility events. Physical OS backgrounding is not established by injected events. |
| Text contrast on actual foreground/background combinations | `browser-contrast-results.json`: axe-core 4.14.0, 18 screens, actual render plus guarded gradient-endpoint probes | Zero reported violations after lightening the example speaker label. Remaining indeterminate decorative/overlap/Monaco nodes are preserved; these do not count as passes. |
| Local resume extraction, review, bounds and provenance before consent | Real PDF-worker tests in `apps/api/tests/test_system.py`; `interviewer/extract.py`, `main.parse_pdf` and upload route | Passed valid text/two-page PDF, encrypted/malformed/image-only/oversize cases, offsets and parser timeout/cancellation tests. Linux worker has CPU/address-space bounds; adversarial Linux memory exhaustion was not executed. Redaction remains explicitly incomplete and editable. |
| Same resume personalized for Backend/Frontend; answer-dependent context | Role/answer context regression; `browser-real-provider-dialogue-results.json`, `browser-real-openrouter-dialogue-results.json` | Four actual browser sessions per provider use one synthetic resume across two roles and answer variants. Distinct openings, answer/context-linked follow-ups and incremental text were observed. This does not establish universal semantic quality. |
| Multi-turn clarification, repeat, skip, pause, typed continuation and wrap-up | `browser-journey-results.json`, `browser-keyboard-journey-results.json`; explicit-help, natural-repeat, skip and memory tests | Complete recorded synthetic journey passed. Standalone requests preserve source ownership and topic budget; skip cannot change stages. Real-provider paraphrase avoidance remains unverified. |
| Provider defaults, switching, persistence and frozen session configuration | Settings/session snapshot tests in `test_system.py`; `browser-recovery-results.json`; `interviewer/store.py` | Groq default, separate selections, revision conflicts and frozen content/provider snapshots passed locally. |
| Missing inactive key, invalid active configuration, selected-provider ownership | Provider/configuration regressions; real smoke and browser artifacts | Mocked failure/control contracts passed. Both configured providers passed real live/structured smoke tests. Catalog availability and quotas remain time-sensitive. |
| Approved OpenRouter routes, disabled fallback, capability/paid consent | Provider request and strict-consent regressions; `interviewer/providers.py` | Local request/schema boundaries passed. Actual downstream routing and account billing controls require the configured provider. |
| Distinct cloud failures, partial stream preservation and explicit retry | Provider/system regressions; `real-provider-smoke-results.json`, reasoning-budget probe | Mocked cases passed. Actual OpenRouter routes returned 429/404, and a mandatory-reasoning model exhausted the former token bound; incomplete text persisted and the session paused. No automatic provider fallback was enabled. Physical network-disconnection behavior remains separate. |
| Both providers: real synthetic live and structured smoke | `real-provider-smoke-results.json` | **Passed recorded smoke scope:** Groq GPT-OSS 20B/120B; OpenRouter explicit Liquid free model through Liquid for both purposes, approved by the owner. Failed Groq/Nvidia OpenRouter routes remain recorded. No general availability or billing guarantee. |
| Deterministic baseline/coached/fresh reasoning and hidden-answer boundaries | Authored content, evidence/snapshot tests; synthetic keyboard and actual Groq full journey | Complete recorded workflow passed with real Groq using synthetic candidate data and skipped coding. Backend reveal/stage gates own authority; private references stay out of live/browser projections. |
| Both languages: correct/wrong, compiler/runtime/output/timeout/process/network/cancel cases | Runner source/image/service, `apps/runner/acceptance_dedicated.py`, static tests; application outage/cancellation browser checks | **Unavailable for actual execution:** run dedicated acceptance on the separate Ubuntu PC. No runner or candidate code was installed/run on this computer. |
| gVisor/resource/network enforcement; no local fallback | `apps/runner/runner_service/main.py`, image definitions and installer; static contract tests | Actual enforcement **unverified** until separate-host acceptance. Application outage path preserves immutable source and reports infrastructure failure without candidate failure. |
| Incremental text and clause audio before whole response finishes | `voice-pipeline-results.json`, `webrtc-transport-results.json`, streaming tests and browser latency markers | Actual local-model transport observed audio before final text/finish; cloud stream integration also has mocked boundaries. No sample-level TTS model streaming claim. |
| Repeated interruption clears prior generation/audio | `browser-voice-recovery-results.json`; generation/STT/TTS cancellation tests | Actual browser repeated Stop and VAD interruption passed. Recorded Stop-to-muted/paused 37/30/32 ms is not acoustic silence. |
| Slow client, disconnect/reload, restart and model/runner outage | Voice recovery, typed recovery, runner cancellation browser artifacts; owned-offer, restart and cleanup regressions | Passed recorded paths with scoped fault injection. Native offers reject audio-free SDP. Shared native warmup cancellation has real-model proof in `warmup-cancellation-results.json`. Physical network loss and real runner recovery remain unverified. |
| Versioned corrections, disputes and stale-result exclusion | `browser-dialogue-memory-results.json`, `browser-recovery-results.json`; correction/source/memory tests | Six injected transcript repairs passed. Original/corrected versions stay distinct, memory invalidates, unresolved disputes are excluded. These are text injections, not six acoustic recognition tests. |
| Privacy/authentication/injection and secret boundaries | Auth/CSRF/Host/body/ownership/hidden-content/canary/public-output tests; frontend and real-provider secret scans | Passed named local boundaries. Both configured real key values were absent from 19 frontend files and 47 saved JSON/log files. No universal absence-of-leaks claim. Raw microphone samples go to local STT/optional recording, not provider payloads. |
| Retention, expiry, abandoned uploads and late-write safety | `test_abandoned_upload_expiry_keeps_recent_upload_and_consumed_session`, expiry/tombstone/delete/restart/cleanup tests | Old abandoned uploads removed while recent upload and active session survive. Consumed upload leaves its standalone table. Session records cascade; filesystem/remote cleanup failure remains pending and retries. No forensic-erasure or cloud-deletion claim. |
| Keyboard setup/settings/interview/report and complete typed path | `browser-keyboard-journey-results.json`, `browser-accessibility-results.json` | Chrome keyboard journey passed with no microphone calls; labels/focus, Monaco Tab exit, report links and mobile width checked. Native dialogs used Playwright responses. Screen-reader/native-dialog physical keyboard review remains unverified. |

## Timing, offline speech and safe assessment

| Requirement | Evidence | Result |
| --- | --- | --- |
| Meaningful audio p50 <=2 s, p95 <=4 s, with milestone/sample reporting | `browser-latency-results.json`: actual local models/Chrome, synthetic mic/cloud, n=10; marker clocks/bases included | **Target missed:** p50 4.847 s, p95 5.302 s. Cold/first-measured and subsequent warm samples are identified. This is a measured product limitation, not a passed target or an external prerequisite. |
| Native WSL persistence comparison | `sqlite-storage-profiles.json`; `browser-latency-native-storage-results.json`, n=10, same synthetic method | Native-store p50 3.761 s / p95 4.819 s; **targets still missed**. Per-delta persistence median 0.842 ms native versus 49.32 ms mounted. Comparison is not randomized; defaults/user data unchanged. |
| Actual cloud plus local speech | `browser-real-provider-latency-results.json`: actual Groq/Chrome/WebRTC/local models, synthetic microphone, n=3 | All three turns completed. **Targets missed:** p50 5.201 s / p95 10.709 s, including a large first-sample outlier. Earlier synchronous-storage diagnostic was 10.334/11.734 s. Small unrandomized samples do not establish production p95 or physical microphone behavior. |
| Measured alternatives before changing speech defaults | `tts-cpu-profiles.json`, `tts-precision-profiles.json`, `speech-pronunciation-results.json` | Default CPU threads beat tested 1/2/4; FP32 beat INT8; manual letter spacing worsened API/TTL round trip. Defaults retained. These model-only samples do not replace integrated latency. |
| Local speech after provisioning with internet blocked | `local-speech-offline-results.json`; `evals/local_speech_check.py --network-isolated` | Real CUDA Whisper/CPU Kokoro passed recorded network-namespace check. Cloud interviewing still requires the selected provider and cannot claim offline AI dialogue. |
| At least 24 held-out traces/two independent human reviews before adverse/numeric assessment | No human calibration result exists | **Unavailable calibration; defined safe mode implemented:** all numeric ratings/adverse technical judgments disabled. Factual reports, references, practice objective, coaching, corrections and disputes remain available. No human review is impersonated. |
| Ten criterion anchors, evidence/version validation and no global competence/hiring score | `content/rubrics/criteria.json`, `interviewer/assessment.py`, report/source/dispute tests | Passed safe factual-mode coverage. Technical evaluator and automatic code review explicitly unavailable; valid quotes are not represented as validated technical inference. |

## Delivery artifacts

| Deliverable | Current source |
| --- | --- |
| Integrated browser/API source and public schemas | `apps/web/src`, `apps/api/interviewer`, especially `responses.py` and request models in `sessions.py` |
| Authored roles/scenarios/coding/private references/rubrics and versioned prompts | `content/roles`, `content/scenarios`, `content/scenario-private`, `content/coding`, `content/coding-private`, `content/rubrics`, `prompts` |
| Dependency locks | `apps/web/package-lock.json`; API/voice/runner `uv.lock` and applicable `requirements.lock` |
| Non-secret configuration and startup/troubleshooting | `.env.example`, `README.md`, `apps/api/interviewer/voice/README.md`, `apps/runner/README.md` |
| Storage schema/migration and restart behavior | `interviewer/store.py`: transactional schema version 1, ownership/foreign keys, tombstones, active-session constraint and restart recovery |
| Windows/WSL speech provisioning/offline verification | `apps/api/run-local-speech.sh`, speech README, provisioning/evaluation scripts in `evals` |
| Dedicated Ubuntu installer, images and service | `apps/runner/install-dedicated-ubuntu.sh`, three Dockerfiles, `fieldnote-runner.service`, dedicated acceptance script; prepared only |
| Build and acceptance evidence | `acceptance.md`, `contract-audit.md`, this matrix, named JSON results and screenshots |

The supplied deployment is loopback-only. LAN secure-context microphone operation
is not shipped as verified functionality; README documents HTTPS/origin/secure
cookie prerequisites and the unverified scope. No backups are created by the
application. Local deletion cannot promise provider-side deletion or forensic
storage erasure.

Full completion remains unproven: dedicated-host execution/isolation is not
established, and the user reports that the Ubuntu PC is not yet available.
The interactive microphone check captured real user speech; the user confirmed
audible interviewer output and working Stop. Physical acoustic timing and a
complete substantive spoken interview remain unmeasured. Real provider smoke and
bounded adaptive browser examples now pass; they do not prove every possible
conversation or sustained free-route quota. Latency targets remain missed.
Continue using the defined safe
assessment mode unless genuine independent calibration meets every gate.
