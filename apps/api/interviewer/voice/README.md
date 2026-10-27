# Local speech adapter

This package exposes `VoiceManager` for the FastAPI backend. Create one manager
per API process (run one worker so model state is not duplicated). Its callbacks
may be set in the constructor or per offer:

```python
voice = VoiceManager()  # main.py supplies callbacks to offer()
await voice.warmup()    # run before enabling Start
```

`get_session(session_id)` must return the authoritative session object only
after checking caller ownership. `on_answer(session_id, text, metadata)` receives
final English transcripts and can be synchronous or asynchronous. The backend
offer handler calls `await voice.offer(session_id, sdp, type, on_answer,
get_session)`. The session store is the only source of `generation_id`; the offer
response echoes it and voice never creates a parallel ID. `send_text` receives
the accumulated durable assistant text, emits only the unsent suffix and sends
complete clauses to TTS. Saved-prefix catch-up and live output share a lock and
character offset so a persisted delta cannot be spoken twice at connection time.
The backend must call
`await voice.finish_text(session_id, generation_id)` when generation ends so the
last partial clause is spoken. `is_connected(session_id)` distinguishes typed
sessions from sessions with active voice. `interrupt` clears pending speech,
sends the Pipecat interruption frame and notifies the browser; it never invents
or persists a generation ID. `close` tears down the pipeline, peer connection
and recording handle.

Offers are serialized because the application supports one active interview.
Before allocating a replacement, `offer` awaits shielded cleanup of every prior
voice owner. A failed close remains registered for retry and prevents replacement
allocation. The new connection is registered before SDP initialization awaits;
failed or cancelled setup therefore uses the same owned close path. An external
close cancels in-flight initialization. Authoritative active/generation state is
checked before allocation, after SDP initialization and after worker registration,
so a pause, correction, completion or deletion cannot publish an obsolete offer.
Completion closes the interview's microphone connection. Once its current
practice review is saved, the report opens a playback-only connection with audio
input and recording disabled. The server reads only the validated saved rating,
summary and next practice focus, without another model request. Stale reviews
cannot be spoken. The delete-on-close path tombstones records before asynchronous
voice cleanup and does not retain a report for playback.

Voice starts automatically when the browser opens or resumes an active interview.
On the transport's client-connected event, the server catches up the current
saved greeting or question if none of that generation has been sent to speech.
This prevents model warmup and microphone permission delays from swallowing the
opening greeting. A denied microphone permission falls back to receive-only
audio and typed answers; browser autoplay restrictions expose a Play audio button.

The browser suspends sphere CSS animation and the visual audio-analysis frame
loop on `visibilitychange` while hidden. Playback acknowledgments remain on their
separate media-clock timer; hiding the page does not manufacture delivery credit
or stop otherwise-authorized audio. Becoming visible restarts the visual loop.
Disconnect releases its listener, frame handle, tracks and analysis context.

An explicit browser microphone disconnect or peer-loss notification also sends
the revision-checked `disconnect` session action over authenticated HTTP. This
pauses the authoritative session, invalidates/cancels generation and closes the
server transport rather than waiting for ICE timeout. The browser reloads state
and requires explicit Resume. A concurrent revision change permits one retry
after fetching current state. Repeating the same action idempotency key can retry
transport cleanup without duplicating the committed disconnect event. Ordinary
Pause remains distinct and may retain a muted voice connection for later Resume.

Optional `on_control(session_id, action, payload)` handles browser actions
`interrupt`, `stop`, `pause`, `done_speaking` and `keep_thinking`. It should
apply authoritative session mutations and cancel backend generation work; the
adapter stops local audio for interrupt, stop and pause. Do not call
`voice.interrupt` from this callback.

The browser data channel sends JSON messages of these forms:

```json
{"type":"interrupt"}
{"type":"pause"}
{"type":"done_speaking"}
{"type":"keep_thinking"}
{"type":"playback_ack","generation_id":"...","played_ms":640}
```

The server sends each `assistant_text` delta immediately with the authoritative
generation ID, and sends an `interrupt` message with the prior ID and the current
authoritative ID. The client appends only matching deltas to the live utterance.
Playback acknowledgments carry cumulative played milliseconds per generation;
the browser uses its media clock after actual audible playback begins, capped
by generated-audio progress, and resets accounting on every generation. The
server rejects malformed/stale acknowledgments and clamps credit to audio
already generated. Pipecat's audio guard runs in native direct mode so a blocked
guard cannot accumulate an unbounded queue ahead of itself. The application
transport window is about one second; one active synthesized clause is separate
from that window. These counters estimate delivery,
not proof the candidate heard it. On interruption, stop the active WebRTC audio
playback immediately and discard queued audio; resume only for a later
authoritative generation ID.

The server emits `audio_progress` with `generation_id` and cumulative
`generated_ms` for admitted audio. Native TTS frame `context_id` values bind
frames and completion signals to their immutable generation, including when
inference finishes late. A typed answer cancels prior voice output before the
next generation starts, even if the previous text stream already completed.

Decoded active utterances are bounded to 120 seconds at 16 kHz. Keep thinking
holds at most 32 completed segments and 12,000 characters, matching the answer
input bound. Hitting a limit does not submit a partial answer or create a failed
criterion: voice pauses and closes, completed text is saved as a local editable
draft (explicitly capped at 12,000 characters), and the candidate can resume by
typing or reconnecting. Pause also saves the current typed draft. Session
retention/deletion applies to drafts.

STT has a 15-second application wait limit. Cancellation cannot stop native CUDA
work; its actual task remains owned and readiness reports busy until completion,
so a reconnect cannot launch another inference alongside it. Late results cannot
create an answer in the closed connection. Done speaking collects the forced
endpoint before committing one answer, preserving a Keep thinking turn across
VAD segments.

TTS likewise owns one public Kokoro `create` call per clause, with a shielded
native task and a 15-second application wait. An interrupted call may finish in
its worker, but the next inference waits and old audio is discarded. Complete
clauses stream independently; an individual long clause is synthesized before
its frames are sent. This is not sample-level model streaming.

Delivery snapshots persist generated/displayed text counts, admitted audio and
estimated playback plus latency milestones. Browser acknowledgments are unscored
diagnostics, never proof of hearing. Client milliseconds and server Unix seconds
are kept separate. Run `node evals/browser-latency.cjs` against the isolated
acceptance server to collect ten real-local-model/synthetic-input turns. The
current measured p50/p95 miss the initial targets; see `docs/browser-latency-results.json`.

## Runtime assets

Python 3.11 is required. Install the optional dependency group from this
directory with `python -m pip install -r requirements.lock`. `uv.lock` is the
canonical resolver lock; `requirements.lock` is its hash-pinned pip export.
CUDA-enabled CTranslate2 and the
matching CUDA/cuDNN runtime must be installed in the host environment. This
adapter never provisions or downloads weights. Place the CTranslate2
`large-v3-turbo` model directory at
`$VOICE_MODEL_DIR/faster-whisper-large-v3-turbo`, and Kokoro files at
`$VOICE_MODEL_DIR/kokoro-v1.0.onnx` and `$VOICE_MODEL_DIR/voices-v1.0.bin`.
Default `VOICE_MODEL_DIR` is `data/models`. `readiness()` fails closed when
dependencies or any asset are missing. Model licenses and the provenance of
locally provisioned weights must be reviewed by the deployer.

For build-time provisioning on Ubuntu, run `bash provision_models.sh
[VOICE_MODEL_DIR]` after installing the Hugging Face CLI (`huggingface_hub`).
It downloads `dropbox-dash/faster-whisper-large-v3-turbo` from Hugging Face at
revision `0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf` and the
Kokoro ONNX files from the upstream GitHub release. Preserve the downloaded
model card/license metadata and review each upstream license and attribution
terms before use or redistribution. The API process itself has no model
download path.

The supported speech profile is English, local faster-whisper large-v3-turbo
on CUDA using `int8_float16`, Silero VAD with a 600 ms stop interval, and Kokoro
voice `af_heart` on CPU. Current Pipecat docs document the Whisper model,
language, device and compute type. The adapter uses faster-whisper directly
with `beam_size=1`, word timestamps and `condition_on_previous_text=False`.
Silero VAD ends a turn after 600 ms silence. The Pipecat pipeline transports
mono audio at a 16 kHz STT boundary and locally resamples unexpected input
rates. Raw microphone audio is not sent to cloud providers.

The locked Pipecat 1.13 runtime uses `PipelineWorker` / `WorkerRunner`;
the adapter uses those APIs, the synchronous `SmallWebRTCConnection.get_answer`,
and positional `TTSSpeakFrame(text, append_to_context=False)`.

`readiness()` reports `warming` until `warmup()` loads the CUDA Whisper model,
consumes a silent transcription result, loads Kokoro on CPU and synthesizes a
short phrase. Missing assets, CUDA setup failures or warmup errors fail
readiness closed. Server startup begins warmup in the background, with runtime
imports and model loading off the HTTP event loop. `offer()` calls `warmup()` as
a fallback and shares any startup load already in progress. Audio transports
remain per interview; startup does not request microphone access.
Warmup uses one shared, shielded task: cancelling a request does not abandon
native model loads or let reconnect start duplicate copies. Both loaders settle
before a failed attempt can be retried. Models publish together after success;
a failed attempt leaves voice unavailable and typed operation intact.

Recording is written only when the authoritative session has
`record_audio: true`. The file is 16 kHz mono PCM WAV at
`$FIELDNOTE_DATA/sessions/<session-id>/microphone-<connection-timestamp>.wav` (default
`data/sessions`) and is capped at session duration plus five minutes, up to
125 minutes. No file is created for the default opt-out. The main API owns
deleting that directory under its retention and deletion lifecycle.

The parent API owns authentication, persistence, cloud generation, consent,
session event versions and browser playback. Signaling must be authenticated
before `offer`; reconnects should create a new generation and must never replay
old audio. Do not run this service on an unauthenticated LAN interface.

## Browser recovery acceptance

`evals/browser-voice-recovery.cjs` exercises the actual Chrome/WebRTC/VAD/STT/TTS
path against the explicitly synthetic cloud server in `evals/browser_server.py`.
The synthetic microphone is a Web Audio stream with a locally generated Kokoro
utterance; it does not establish physical microphone performance or natural
speech accuracy. Run `SPEECH_CHECK_SCRIPT=evals/make_browser_speech.py bash
evals/run_speech_check.sh` from the repository root to generate that fixture.

Start the acceptance server in a separate WSL terminal:

```bash
FIELDNOTE_DATA="$PWD/data/voice-browser-acceptance" \
VOICE_MODEL_DIR="$PWD/data/models" \
FIELDNOTE_ORIGIN=http://127.0.0.1:8001 ACCEPTANCE_PORT=8001 \
SPEECH_CHECK_SCRIPT=evals/browser_server.py bash evals/run_speech_check.sh
```

From the Windows repository root, set `PLAYWRIGHT_MODULE` to an installed
Playwright module directory and `CHROME_EXECUTABLE` to the Chrome executable,
then run `node evals/browser-voice-recovery.cjs`. The script deletes only sessions
in that isolated acceptance server's database. Do not point it at normal data.
Its model-fault endpoints exist only in the acceptance harness and are protected
by the normal owner/CSRF middleware. Normal application startup does not expose
those endpoints or substitute synthetic provider responses.
