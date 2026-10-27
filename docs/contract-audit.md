# Current contract audit

Audited 20 October 2026 against `agent.md`, application source, authored records,
test output, and saved browser evidence. The overall build remains active. A
passed narrow check below does not establish completion of a broader requirement.

## Current evidence

| Area | Evidence and scope | Status |
| --- | --- | --- |
| Web production artifact | TypeScript/Vite production build passed. Local font, Monaco worker, and editor assets are bundled. Monaco produces a size advisory. | Pass for compilation/bundling |
| API, voice helpers, runner source contracts | Combined pytest suite: 277 passed after off-loop durable generation writes and retired-generation rejection, live-catalog alias filtering, provider-specific reasoning budgets, external test isolation, role/answer context and abandoned-upload expiry proof, shared native-model warmup ownership, natural standalone request handling, serialized voice-offer ownership, active-audio signaling validation, completion cleanup, explicit media disconnection/cleanup retry, background conversational memory, API secret canaries, request-aware question progress, received-body bounds, runner-result validation, ownership, strict consent and Host-boundary changes. One Starlette TestClient deprecation warning remains. Runner checks inspect source and the extracted JSON loader; they execute no service or candidate code. | Pass within test scope |
| Landing/setup/navigation | `browser-results.json`, `browser-journey-results.json`, and desktop/mobile screenshots exercise owner access, synthetic example, local pasted resume, confirmed context, and role setup. | Pass for recorded synthetic journey |
| Typed integrated journey | `browser-journey-results.json`: streamed answer-dependent follow-up, baseline cards/conclusion, explicitly skipped coding, reference review, coaching, fresh variant, completion/report. | Pass with synthetic cloud and skipped execution |
| Mobile correction/settings/deletion | `browser-recovery-results.json` and 360 px screenshots cover the recorded correction/dispute/settings/deletion path. | Pass within recorded scope |
| Local speech models | `local-speech-results.json` and `local-speech-offline-results.json`: real CUDA Whisper and CPU Kokoro, three synthetic utterances, offline run in an isolated network namespace. | Pass for synthetic local-model smoke |
| WebRTC transport/pipeline | `webrtc-transport-results.json`, `voice-pipeline-results.json`: actual transport, data channel, synthesized downlink, and local STT uplink. | Pass for recorded synthetic transport checks |
| Browser voice/recovery | `browser-voice-recovery-results.json`: real Chrome/WebRTC/local models, synthetic browser mic and cloud; repeated Stop, VAD barge-in, versioned correction, reload/reconnect without replay, injected TTS outage with typed continuation, media-only disconnect pause, and abandoned warmup without mic acquisition. | Pass within recorded scope |
| Hidden rendering and media-loss cleanup | Injected visibility events pause CSS layers/pseudo-element and cancel the visual RAF loop; media-clock delivery acknowledgments stay separate. The explicit revision-checked disconnect action pauses/cancels and closes server voice; cleanup retries preserve idempotency. Focused API/source and actual local-model browser checks cover these paths. | Pass within injected-event/browser scope; OS visibility/physical network-loss behavior unverified |
| CPU synthesis alternatives | FP32 versus upstream INT8: three warm synthesis samples each and six synthetic local Whisper round trips. Median 1.326 versus 4.931 seconds; INT8 rejected. Native technical-term phonemization outperformed manual letter spacing in the API/TTL prompt. | Existing runtime model/pronunciation defaults retained; no integrated target improvement claimed |
| Retention and owned cleanup | Delete-on-close crash recovery, consumed uploads, cascading transcript/event/idempotency/job deletion, undispatched-job handling, transient media/filesystem retry, path alias rejection and cancellation-safe recording/transport cleanup have regression proof. Real local-model/WebRTC recovery rerun passed after these changes. | Pass within recorded paths; complete security audit remains open |
| Ownership and cross-session references | Focused HTTP regressions reject foreign-owner session/upload access across 13 read/write paths and reject another owned session's utterance/finding/job IDs. Exact stored-state comparisons show no rejected-request mutation or queued cleanup. | Pass for tested application routes; dedicated-host authorization remains separate |
| Consent input types | Strict request validation rejects string/numeric/null consent and coerced revision values. HTTP tests prove no session/events or provider validation call occurs for malformed consent. Complete system/provider selection passed 137 checks after this change. | Pass for JSON type boundaries; real consent/billing checks remain separate |
| Local hostname protection | Unknown and lookalike Host values reject before static/API handling; loopback and the exact configured origin hostname remain accepted. Focused tests verify rejected reads/writes and unchanged settings. | Pass for application HTTP tests; no actual DNS-rebinding/LAN test claim |
| Received upload bounds | API writes pre-read at most 11 MiB within 30 seconds after access checks. ASGI tests reject chunked/understated overflow before parsing, timeout and disconnect; an HTTP chunked-resume check confirms no upload persistence. Existing file/parser limits remain separate. | Pass within local ASGI/HTTP tests; real proxy/network behavior unverified |
| Real provider connectivity | `real-provider-smoke-results.json`: actual live/strict structured smoke passed on Groq GPT-OSS 20B/120B and OpenRouter's approved explicit Liquid free route. Both providers also completed four actual browser role/answer cases; Groq completed the integrated typed practice/report journey with coding skipped. OpenRouter Groq/Nvidia route failures remain recorded. | Pass for recorded synthetic-input calls; no general availability or sustained-quota guarantee |
| Dedicated runner enforcement | Ubuntu installer, images, service, authenticated runner, static contracts, and dedicated-host acceptance script exist. No runner software or candidate execution was installed/run on this computer. | Separate Ubuntu PC acceptance required |
| Automatic assessment safety | Numeric ratings/adverse labels remain disabled. Factual statements, original/corrected transcripts, disputes, authored references, and support labels remain available. | Safe mode active; no human calibration claim |
| Structured provider validation | Draft 2020-12 rejects invalid schemas/content without remote references; mocked faults and actual strict structured smoke on both configured providers passed. | Pass for tested schema boundaries and real smoke; no calibrated technical-inference claim |
| Public response boundaries | Every JSON API route declares a Pydantic output model; nested public models filter unknown fields and reject invalid declared types. Canary tests cover session/mutation/report/job fields, aggregate-only hidden outcomes, model/route metadata and signaling. Application notifications validate their payload and session channel. Request errors omit rejected input; response validation errors expose no stored values. | Pass for tested HTTP/application-notification boundaries; not a complete security audit |
| Factual report coverage | All ten authored criteria show opportunity/abstention with null ratings. Owned statement events and exact preserved transcript versions validate observations; unsupported records are excluded. Corrections/disputes invalidate conclusions. Reading a report no longer creates database records. Legacy observations are derived read-only and remain challengeable. | Pass for safe factual mode |
| Conversational memory | An optional structured call after each two new substantive replies groups semantically related questions using exact answer quotes and selects question excerpts to revisit. It uses the frozen selected assessment model/route, runs after live delivery, and yields to live generation. Closed schemas, source/event/version checks, prefix signatures, cancellation, deletion and late-result guards have regression proof. | Pass for mocked mechanism/source boundaries; real-model grouping accuracy and paraphrase avoidance unverified |
| Six transcript repairs | `browser-dialogue-memory-results.json`: six synthetic recognition-like mistakes entered through the typed-answer path, then repaired through report dialogs. Original text/version persists, current factual observations update, dependent memory invalidates, all criterion ratings remain null, deletion succeeds. | Pass for six injected correction workflows; no six-case acoustic STT or human-calibration claim |
| Secret canaries | API regressions inject a synthetic server key into upstream error bodies and invalid structured content, then check serialized provider errors, settings/readiness/history responses and captured logs. Frontend pattern scan remains separate. | Pass for these injected paths; not an exhaustive backend/log audit |
| Voice bounds and slow client | Browser test withheld playback acknowledgments: pending transport audio stopped at 1,000 ms, with one 20 ms frame waiting before the direct guard. Restoring acknowledgments resumed speech without Repeat. Unit tests cover stale/invalid/future credits, bounded input, held drafts, single owned cancelled STT work, and readiness while busy. | Pass within recorded paths |
| Input-limit recovery | Near-limit held draft was injected, followed by real browser/VAD/STT input. The session paused, saved a bounded 12,000-character draft, closed voice, and created no partial answer. Reviewed typed continuation succeeded. | Pass for injected held-draft limit; continuous two-minute boundary has unit coverage |
| Incremental clause audio | Actual local-model/WebRTC check observed audio before `finish_text` or later clause delivery, 1.285 seconds after the first complete clause (n=1). | Pass for incremental transport; not end-to-end interview latency |
| Keyboard/motion | `browser-accessibility-results.json` covers trapped sample focus, owner sign-in, navigation and reduced motion. `browser-keyboard-journey-results.json` adds keyboard setup/claim editing, dialogue/pause, evidence/hypothesis/conclusion, Monaco editing/Tab exit, safe runner outage, coaching/fresh completion, report links/correction/dispute and deletion. Screenshots reviewed at 360/1440 px without overflow. Native dialogs use Playwright dialog automation. | Pass within recorded Chrome scope; screen-reader/native-dialog keyboard review remains unverified |

## Requirement review and unresolved acceptance

The requirement map is in [acceptance-matrix.md](acceptance-matrix.md). The
following distinguishes implemented mechanisms from unresolved acceptance;
neither scoped tests nor unavailable credentials establish full completion.

- Technical evaluator/code-review ownership audit completed against the current
  safe-mode contract. Safe factual
  coverage and source validation now execute in `interviewer/assessment.py`,
  but are not a calibrated technical-inference service. Technical assessment and
  automatic code review explicitly report unavailable. Live and coach prompts
  now load in production; evaluator/code-review prompts remain unconnected.
  Their execution remains intentionally unavailable without calibration.
  Preserve the contract's safe mode; do not silently claim that document
  files are executable services or enable adverse labels to satisfy a checklist.
- Local schema validation is now implemented independently of provider strict
  output. It does not establish that a schema-valid technical inference is sound.
  Real provider smoke checks and any future inference validation remain separate.
- Dialogue ownership review confirms current
  context includes confirmed claims, role objectives, recent turns, disclosed
  facts, reasoning events, and extractive event-linked memory. The application
  explicitly selects a confirmed claim, cycles role objectives, supplies the
  public coding contract, and uses live/coach prompt files. It also
  recognizes explicit standalone clarification/uncertainty/skip/repeat requests,
  including polite natural variants and typographic apostrophes, with their
  current source event and prior question. A bounded provisional semantic memory
  now groups related questions and exact quoted answers, with question excerpts
  to revisit. It runs after topic-boundary responses, never as a prerequisite to
  speaking. Real-model grouping quality, broader clarification/skip behavior and
  avoiding repeated resolved questions under real provider output remain unverified.
- Latency milestones and a ten-turn integrated synthetic benchmark now exist.
  Browser-clock speech-end-to-playback p50/p95 are 4.847/5.302 seconds (n=10),
  missing the 2/4-second targets. Actual Groq plus local speech was subsequently
  measured with a synthetic browser microphone: p50 5.201 s / p95 10.709 s
  (n=3), with samples 11.321/4.296/5.201 s. These small diagnostic samples
  still miss both targets and do not establish production p95. Physical-microphone
  performance remains unverified. Improve measured bottlenecks without treating model-only
  timings or diagnostic polling runs as production latency.
  A native WSL storage comparison now measures 3.761/4.819 seconds (n=10),
  still missing both targets. A synthetic 60-write persistence probe isolates
  median per-delta cost at 49.32 ms on `/mnt/c` versus 0.842 ms natively. The
  comparison does not change defaults or migrate user data; see the matrix.
- Input and held-segment bounds, slow-client transport backpressure, generation
  frame IDs and single owned STT cancellation now have focused proof. TTS calls
  are now serialized across cancellation, and generation-bound delivery estimates
  persist as validated diagnostic events. Continue auditing recovery and ensure
  delivery diagnostics never become hearing/competence evidence. The measured transport window does not include all model,
  native transport or browser buffers and does not prove acoustic delivery.
- Replacement-offer ownership now uses serialized offers, shielded prior cleanup
  before allocation and registration before SDP initialization. Failed cleanup
  retains its owner for retry; failed/cancelled setup and external close share
  owned cleanup. State is rechecked before publishing a pipeline. Twenty-four
  fake-transport tests cover lifecycle failures, cancellation, overlapping offers,
  late state changes and invalid/audio-free SDP. Six HTTP regressions cover
  completion cleanup and sanitized signaling errors. These checks do not prove
  every native transport failure or physical network-loss behavior.
- The bounded security, resume/PDF, ownership, retention, restart, keyboard,
  reduced-motion and privacy source/test review is mapped in the acceptance
  matrix. No additional concrete backend defect was found in the inspected
  paths. Added same-resume role/answer context and abandoned-upload expiry
  regressions close two feasible proof gaps. Existing results establish only
  their covered paths, not universal security or accessibility conformance.
  Six injected transcript-repair workflows now have observed browser results;
  they are synthetic text injections, not six measured transcription errors or
  human calibration. Existing recovery evidence has its own recorded scope.

## Additional current-source findings

- Resume parsing review found an existing subprocess boundary with one parser
  slot, a one-second admission timeout and ten-second wall timeout. On the
  production Ubuntu backend, the worker applies 512 MiB address-space and
  eight-second CPU limits before importing the parser. Input is bounded to
  10 MiB, 20 pages and 50,000 extracted characters; encrypted, malformed and
  image-only documents have actionable errors. Existing real-worker tests cover
  page provenance and these document cases; timeout/cancellation tests verify
  child termination and slot release. Windows test execution does not establish
  Linux resource enforcement. Extraction receives bytes through stdin and stores
  generated IDs, not user-selected filesystem paths. The raw extraction remains
  local; proposed context removes common contact details and explicitly requires
  review because redaction is incomplete. No new parser implementation was
  needed. Adversarial parser-memory exhaustion and comprehensive personal-data
  detection remain outside the recorded proof.

The following gaps were identified directly in current source and must not be
hidden behind passing browser examples:

- New sessions privately capture role, scenario, causal reference, coding,
  rubric and live/coach prompt content with a digest. Public projections omit
  private snapshots. Execution requests pin the full public problem and hidden
  test record using a canonical SHA-256 digest; the dedicated runner rejects
  changed content before creating candidate containers. Legacy sessions disclose
  unpinned provenance and cannot start code execution without a captured digest.
  Real dedicated-host validation remains unavailable.
- The report derives completed questions without a substantive recorded reply
  from persisted turns and current-version answer events. Provisional semantic
  memory additionally groups addressed points and question excerpts to revisit.
  Neither a recorded reply nor a valid quote establishes technical correctness;
  model-selected open details can be mistaken and are labeled accordingly.
- Question progress now distinguishes explicit repeat, clarification, uncertainty,
  and skip replies from substantive recorded replies. Reports retain those
  questions as conversationally open, and live context consumes their factual
  status. Status is derived from the full current-version, event-linked text;
  transcript corrections replace the prior intent. This does not infer semantic
  resolution, technical correctness, or failure from uncertainty or skipping.
- JSON responses now use explicit Pydantic models, including nested public
  session/report/provider/execution fields. Session projection selects public
  fields and validates factual observations. App-originated SSE/WebRTC
  notifications use a typed, session-bound envelope. Invalid declared output
  types fail closed without echoing stored/provider content; unknown fields are
  filtered. Private-field canaries and the integrated browser journey pass.
  Remaining security/ownership/retention and voice-specific message review must
  still be completed; these checks do not establish general conformance.
- Candidate-controlled execution cancellation, restart cancellation queues, and
  malformed remote-result handling now exist, with mocked transport/state tests.
  Remote results also validate outcome types, count consistency, compiler exits
  and lifecycle agreement before persistence; contradictory results become
  infrastructure failure and require cleanup. Twenty-seven focused application
  and runner-source checks passed after these changes.
  The browser cancellation path now passes against a held application task with
  no remote dispatch: immutable source, terminal state, one cancellation event,
  factual report and 360 px layout are verified. Real dedicated-host job
  enforcement remains unproved. The expanded dedicated acceptance probes are prepared,
  not executed.
- Six transcript-repair injections run in the system suite, and multiple real
  browser recovery paths have recorded evidence. This does not replace the
  independent two-human calibration gate, which remains unavailable and keeps
  automatic adverse/numeric assessment disabled.

Use the matrix and named artifacts when choosing the next required verification.
Bounded real-provider adaptive wording now has observed browser evidence;
physical microphone use and dedicated-host enforcement remain unverified, and
integrated latency remains above target. Do not
add unrelated polish or promote a narrow result to full completion.

## External prerequisites and limitations

- Both keys are now configured locally, with explicit paid/free-route consent.
  Keep them only in the protected backend environment. Current real smoke and
  browser results do not establish future model, route or quota availability.
  Never send keys in chat or put them in frontend configuration.
- Run installation and actual isolation/resource/network/process/cancellation
  acceptance on the owner's separate Ubuntu PC. Development/application-host
  runner installation remains prohibited.
- Physical microphone/natural speech acceptance requires a human-operated mic.
  Synthetic speech has already produced the homophone error “cash” for “cache”;
  the browser check preserved it and explicitly corrected the transcript.
- Independent technically competent human review and adjudication remain
  unavailable. Keep automatic adverse labels/numeric ratings disabled unless the
  specified calibration gates are genuinely met.

The chronological `acceptance.md` retains earlier findings and superseded
limitations. Consult the actual named result artifacts and current source before
promoting any item to complete.
