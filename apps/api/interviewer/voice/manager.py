"""Pipecat SmallWebRTC voice adapter.

Speech models are provisioned locally and never downloaded by this module.
The heavy runtime dependencies are imported lazily so the rest of the API can
start and report a useful unavailable state when voice extras are absent.
"""
from __future__ import annotations

import asyncio
import math
import importlib.util
import inspect
import json
import os
import re
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable


AnswerCallback = Callable[[str, str, dict[str, Any]], Any | Awaitable[Any]]
SessionLookup = Callable[[str], Any | Awaitable[Any]]
ControlCallback = Callable[[str, str, dict[str, Any]], Any | Awaitable[Any]]


@dataclass
class _UtteranceAudio:
    """Bound decoded input independently of whether VAD ever finds silence."""
    max_samples: int = 120 * 16000
    chunks: list[Any] = field(default_factory=list)
    num_samples: int = 0

    def append(self, samples: Any) -> bool:
        if self.num_samples + len(samples) > self.max_samples:
            self.take()
            return False
        self.chunks.append(samples)
        self.num_samples += len(samples)
        return True

    def take(self) -> list[Any]:
        chunks, self.chunks = self.chunks, []
        self.num_samples = 0
        return chunks


@dataclass(frozen=True)
class VoiceReadiness:
    ready: bool
    status: str
    detail: str
    missing: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"ready": self.ready, "status": self.status, "detail": self.detail,
                "missing": list(self.missing)}


@dataclass
class _Session:
    session_id: str
    generation_id: str
    task: Any
    transport: Any
    connection: Any
    lock: asyncio.Lock
    text_queue: asyncio.Queue[tuple[str, str] | None]
    audio_condition: asyncio.Condition
    on_answer: AnswerCallback | None = None
    on_control: ControlCallback | None = None
    text_buffer: str = ""
    synth_generation: str | None = None
    tts_done: asyncio.Event | None = None
    waiting_tts_generation: str | None = None
    recording: Any = None
    recording_name: str | None = None
    recorded_samples: int = 0
    recording_sample_limit: int = 0
    recording_limit_notified: bool = False
    generation_active: bool = False
    pending_audio_ms: float = 0.0
    generated_audio_ms: float = 0.0
    offered_audio_ms: float = 0.0
    audio_progress_ms: int = 0
    peak_pending_audio_ms: float = 0.0
    last_ack_played_ms: int = 0
    sender_task: asyncio.Task[Any] | None = None
    pipeline_task: asyncio.Task[Any] | None = None
    interrupted: bool = False
    closed: bool = False
    client_ready: bool = False
    text_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    cleanup_complete: bool = False
    cleanup_task: asyncio.Task[Any] | None = None
    offer_task: asyncio.Task[Any] | None = None
    playback_acked_ms: int = 0
    defer_answers: bool = False
    held_answers: list[tuple[str, dict[str, Any]]] | None = None
    force_endpoint: Callable[[], Awaitable[None]] | None = None
    interruption_done: asyncio.Event | None = None
    callback_tasks: set[asyncio.Task[Any]] | None = None
    speech_failed: bool = False
    input_failed: bool = False
    generated_text_chars: int = 0
    displayed_text_chars: int = 0
    text_finished: bool = False
    delivery_complete: bool = False
    timings: dict[str, float] = field(default_factory=dict)


class VoiceManager:
    """One-process voice model owner and per-session WebRTC pipeline manager.

    `on_answer(session_id, transcript, metadata)` receives finalized local STT.
    `get_session(session_id)` must verify ownership and return the authoritative
    session (or a falsey value). It is checked before signaling and text output.
    """

    def __init__(self, on_answer: AnswerCallback | None = None, get_session: SessionLookup | None = None,
                 on_control: ControlCallback | None = None,
                 *, model_dir: str | Path | None = None, data_dir: str | Path | None = None,
                 queue_chunks: int = 2, max_audio_seconds: float = 1.0,
                 on_event: ControlCallback | None = None):
        self._on_answer = on_answer
        self._get_session = get_session
        self._on_control = on_control
        self._on_event = on_event
        self._data_dir = Path(data_dir or os.getenv(
            "FIELDNOTE_DATA", str(Path(__file__).resolve().parents[4] / "data")))
        self._model_dir = Path(model_dir or os.getenv("VOICE_MODEL_DIR", str(self._data_dir / "models")))
        self._queue_chunks = max(1, min(int(queue_chunks), 2))
        self._max_audio_seconds = max(0.25, min(float(max_audio_seconds), 1.0))
        self._sessions: dict[str, _Session] = {}
        self._imports: dict[str, Any] | None = None
        self._whisper_model: Any = None
        self._kokoro_model: Any = None
        self._warmup_lock = asyncio.Lock()
        self._warmup_task: asyncio.Task[Any] | None = None
        self._offer_lock = asyncio.Lock()
        self._warmup_error: str | None = None
        self._stt_task: asyncio.Task[Any] | None = None
        self._tts_task: asyncio.Task[Any] | None = None
        self._tts_lock = asyncio.Lock()
        self._warmup_seconds: float | None = None

    def readiness(self) -> dict[str, Any]:
        """Return fail-closed provisioning and dependency status; never fetch assets."""
        required = {
            "faster-whisper": "faster_whisper",
            "pipecat-ai": "pipecat",
            "onnxruntime": "onnxruntime",
            "kokoro-onnx": "kokoro_onnx",
            "numpy": "numpy",
            "scipy": "scipy",
        }
        missing = [name for name, module in required.items() if importlib.util.find_spec(module) is None]
        model = self._model_dir / "faster-whisper-large-v3-turbo"
        kokoro_model = self._model_dir / "kokoro-v1.0.onnx"
        voices = self._model_dir / "voices-v1.0.bin"
        if not model.is_dir() or not (model / "model.bin").is_file() or not (model / "config.json").is_file():
            missing.append(f"complete faster-whisper large-v3-turbo CTranslate2 model at {model}")
        for label, path in (("Kokoro ONNX", kokoro_model), ("Kokoro voice data", voices)):
            if not path.is_file():
                missing.append(f"{label} at {path}")
        if missing:
            result = VoiceReadiness(False, "unavailable", "Local speech dependencies or model assets are missing; provision them before starting voice.", tuple(missing))
        elif self._warmup_error:
            result = VoiceReadiness(False, "unavailable", "Local speech model warmup failed.", (self._warmup_error,))
        elif self._whisper_model is None or self._kokoro_model is None:
            result = VoiceReadiness(False, "warming", "Local speech models have not completed warmup.")
        elif self._stt_task and not self._stt_task.done():
            result = VoiceReadiness(False, "busy", "A previous local transcription is still finishing. Wait before reconnecting voice, or continue by typing.")
        elif self._tts_task and not self._tts_task.done():
            result = VoiceReadiness(False, "busy", "A previous local synthesis is still finishing. Wait before reconnecting voice, or continue by typing.")
        else:
            result = VoiceReadiness(True, "ready", "Local Whisper and Kokoro models loaded and passed warmup.")
        return {**result.as_dict(), "warmup_seconds": self._warmup_seconds}

    async def _authorized(self, session_id: str) -> bool:
        if not self._get_session:
            return False
        value = self._get_session(session_id)
        if inspect.isawaitable(value):
            value = await value
        return bool(value)

    def _load_runtime(self) -> dict[str, Any]:
        if self._imports is not None:
            return self._imports
        from pipecat.frames.frames import (InputAudioRawFrame, UserStartedSpeakingFrame,
            VADUserStartedSpeakingFrame, VADUserStoppedSpeakingFrame,
            UserStoppedSpeakingFrame, TTSSpeakFrame, TTSAudioRawFrame, TTSStartedFrame,
            TTSStoppedFrame, InterruptionWorkerFrame, InterruptionFrame, OutputTransportMessageUrgentFrame)
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.worker import PipelineWorker, PipelineParams
        from pipecat.workers.runner import WorkerRunner
        from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
        from pipecat.processors.audio.vad_processor import VADProcessor
        from pipecat.audio.vad.silero import SileroVADAnalyzer
        from pipecat.audio.vad.vad_analyzer import VADParams
        from pipecat.transports.base_transport import TransportParams
        from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
        import numpy as np
        from scipy.signal import resample_poly
        self._imports = {key: value for key, value in locals().items() if key != "self"}
        return self._imports

    async def warmup(self) -> dict[str, Any]:
        """Keep native model loading owned if an HTTP/offer waiter is cancelled."""
        if self._warmup_task is None or self._warmup_task.done():
            self._warmup_task = asyncio.create_task(self._warmup())
            self._warmup_task.add_done_callback(
                lambda finished: None if finished.cancelled() else finished.exception())
        return await asyncio.shield(self._warmup_task)

    async def _warmup(self) -> dict[str, Any]:
        """Load and exercise both local models; readiness stays false until success."""
        if self._whisper_model is not None and self._kokoro_model is not None:
            return self.readiness()
        async with self._warmup_lock:
            if self._whisper_model is not None and self._kokoro_model is not None:
                return self.readiness()
            self._warmup_error = None
            base = self.readiness()
            if base["status"] == "unavailable":
                return base
            try:
                warmup_started = time.monotonic()
                # Validate the installed Pipecat frame/transport API during
                # warmup so readiness means the real pipeline can be built.
                await asyncio.to_thread(self._load_runtime)
                import numpy as np

                def load_whisper():
                    from faster_whisper import WhisperModel
                    model = WhisperModel(
                        str(self._model_dir / "faster-whisper-large-v3-turbo"),
                        device="cuda", compute_type="int8_float16",
                    )
                    # Exercise CUDA initialization and consume the lazy iterator.
                    segments, _ = model.transcribe(
                        np.zeros(16000, dtype=np.float32), language="en", beam_size=1,
                        word_timestamps=True, condition_on_previous_text=False,
                    )
                    list(segments)
                    return model

                def load_kokoro():
                    from kokoro_onnx import Kokoro
                    model = Kokoro(str(self._model_dir / "kokoro-v1.0.onnx"),
                                   str(self._model_dir / "voices-v1.0.bin"))
                    samples, sample_rate = model.create("Ready.", voice="af_heart",
                                                        speed=1.0, lang="en-us")
                    if not sample_rate or len(samples) == 0:
                        raise RuntimeError("Kokoro warmup returned no audio")
                    return model

                # A failed loader must not release ownership while its sibling
                # is still allocating a native model in another thread.
                models = await asyncio.gather(
                    asyncio.to_thread(load_whisper), asyncio.to_thread(load_kokoro),
                    return_exceptions=True)
                for model in models:
                    if isinstance(model, BaseException):
                        raise model
                self._whisper_model, self._kokoro_model = models
                self._warmup_error = None
            except Exception as exc:
                self._whisper_model = self._kokoro_model = None
                self._warmup_error = f"{type(exc).__name__}: {exc}"
            finally:
                self._warmup_seconds = time.monotonic()-warmup_started
            return self.readiness()

    async def offer(self, session_id: str, sdp: str, type: str,
                    on_answer: AnswerCallback | None = None,
                    get_session: SessionLookup | None = None,
                    on_control: ControlCallback | None = None) -> dict[str, Any]:
        """Create one SmallWebRTC connection and return its SDP answer."""
        async with self._offer_lock:
            succeeded = False
            try:
                answer = await self._create_offer(session_id, sdp, type, on_answer, get_session, on_control)
                succeeded = True
                return answer
            finally:
                session = self._sessions.get(session_id)
                if session and getattr(session, "offer_task", None) is asyncio.current_task():
                    if not succeeded:
                        await self.close(session_id)
                    session.offer_task = None

    async def _active_voice_state(self, session_id: str, lookup: SessionLookup,
                                  generation: str | None = None) -> dict[str, Any]:
        state = lookup(session_id)
        if inspect.isawaitable(state): state = await state
        if (not state or state.get("paused")
                or (state.get("stage") == "COMPLETED" and not state.get("_practice_review"))
                or not state.get("generation_id")
                or (generation is not None and state["generation_id"] != generation)):
            raise RuntimeError("Session changed or paused. Reload state and resume explicitly before enabling voice.")
        return state

    async def _create_offer(self, session_id: str, sdp: str, type: str,
                            on_answer: AnswerCallback | None, get_session: SessionLookup | None,
                            on_control: ControlCallback | None) -> dict[str, Any]:
        if get_session:
            value = get_session(session_id)
            if inspect.isawaitable(value): value = await value
            if not value: raise PermissionError("Session not found or not owned by caller")
        elif not await self._authorized(session_id):
            raise PermissionError("Session not found or not owned by caller")
        audio_lines = re.finditer(r"(?m)^m=audio ([0-9]{1,5}) \S+ [0-9]+(?: +[0-9]+)*\r?$", sdp)
        if (type != "offer" or not sdp.startswith(("v=0\r\n", "v=0\n"))
                or not any(0 < int(line[1]) <= 65535 for line in audio_lines)):
            raise ValueError("Voice needs a WebRTC offer with active audio. Reconnect the microphone or continue by typing.")
        lookup = get_session or self._get_session
        await self._active_voice_state(session_id, lookup)
        # The application permits one active interview. Retain each prior owner
        # until its shielded cleanup succeeds, before allocating a replacement.
        for prior_id in tuple(self._sessions):
            await self.close(prior_id)
        r = await self.warmup()
        if not r["ready"]:
            raise RuntimeError(r["detail"] + " Missing: " + ", ".join(r["missing"]))
        libs = self._load_runtime()
        from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
        if get_session:
            self._get_session = get_session
        if on_control:
            self._on_control = on_control
        state = await self._active_voice_state(session_id, lookup)
        authoritative_generation = state["generation_id"]
        connection = SmallWebRTCConnection()
        session = _Session(session_id, authoritative_generation, None, None, connection,
                           asyncio.Lock(), asyncio.Queue(maxsize=self._queue_chunks),
                           asyncio.Condition(), on_answer=on_answer or self._on_answer,
                           on_control=on_control or self._on_control,
                           tts_done=asyncio.Event(), offer_task=asyncio.current_task())
        self._sessions[session_id] = session
        await connection.initialize(sdp=sdp, type=type)
        answer = connection.get_answer()
        await self._active_voice_state(session_id, lookup, authoritative_generation)
        transport = libs["SmallWebRTCTransport"](
            webrtc_connection=connection,
            params=libs["TransportParams"](audio_in_enabled=state["stage"] != "COMPLETED", audio_out_enabled=True,
                                            audio_in_sample_rate=16000),
        )
        session.transport = transport
        owner = self

        class TranscriptProcessor(libs["FrameProcessor"]):
            def __init__(self):
                super().__init__()
                self._active = False
                self._preroll: list[Any] = []
                self._audio = _UtteranceAudio()
                self._preroll_samples = 0
                self._received_samples = 0
                self._turn_start_samples = 0
                self._clock_offset = max(0.0, time.time() - float(state["created"]))

            async def process_frame(self, frame: Any, direction: Any) -> None:
                await super().process_frame(frame, direction)
                if isinstance(frame, libs["InputAudioRawFrame"]):
                    if session.input_failed:
                        return
                    samples = owner._input_samples(frame, libs)
                    self._received_samples += len(samples)
                    owner._record_samples(session, samples, libs)
                    if self._active:
                        if not self._audio.append(samples):
                            self._active = False
                            session.input_failed = True
                            owner._schedule_callback(session, lambda: owner._input_failed(session,
                                "Continuous speech exceeded two minutes and was not submitted. Any completed draft was saved. Resume with a shorter typed answer, or reconnect voice."))
                    else:
                        self._preroll.append(samples)
                        self._preroll_samples += len(samples)
                        while self._preroll and self._preroll_samples > 4800:
                            self._preroll_samples -= len(self._preroll.pop(0))
                    return
                if isinstance(frame, (libs["UserStartedSpeakingFrame"], libs["VADUserStartedSpeakingFrame"])):
                    if session.input_failed:
                        return
                    self._turn_start_samples = max(0, self._received_samples - self._preroll_samples)
                    self._active = True
                    self._audio = _UtteranceAudio()
                    for samples in self._preroll:
                        self._audio.append(samples)
                    self._preroll.clear()
                    self._preroll_samples = 0
                    if (session.generation_active or session.pending_audio_ms > 0
                            or not session.text_queue.empty()
                            or (session.tts_done is not None and not session.tts_done.is_set())):
                        # Application cancellation waits for an interruption to
                        # traverse this processor. Never await it in the frame loop.
                        owner._schedule_callback(session, lambda: owner._dispatch_control(
                            session, "interrupt", {"source": "silero_vad"}))
                    await self.push_frame(frame, direction)
                    return
                if isinstance(frame, (libs["UserStoppedSpeakingFrame"], libs["VADUserStoppedSpeakingFrame"])):
                    await self._finish_turn(frame, direction)
                    return
                await self.push_frame(frame, direction)

            async def _finish_turn(self, frame: Any, direction: Any, *, schedule_callback: bool = True) -> None:
                self._active = False
                audio = self._audio.take()
                endpoint_at = float(getattr(frame, "timestamp", time.time()))
                stop_seconds = float(getattr(frame, "stop_secs", 0.0))
                await self.push_frame(frame, direction)
                if audio and owner._whisper_model is not None:
                    segment_start = self._clock_offset + self._turn_start_samples / 16000
                    samples = libs["np"].concatenate(audio).astype(libs["np"].float32, copy=False)
                    try:
                        stt_started_at = time.time()
                        text, words = await owner._transcribe_async(samples)
                        stt_completed_at = time.time()
                    except Exception:
                        session.input_failed = True
                        owner._schedule_callback(session, lambda: owner._input_failed(session,
                            "Local transcription failed, timed out, or is still busy. This answer was not submitted. Resume by typing, or reconnect voice when the model is ready."))
                        return
                    if text:
                        metadata = {
                            "source": "local-faster-whisper", "language": "en",
                            "received_at": time.time(), "final": True,
                            "audio_duration_seconds": len(samples) / 16000,
                            "words": words,
                            "word_timestamp_basis": "relative_to_transcribed_segment",
                            "timing": {"clock": "server_unix_seconds", "endpoint_decision": endpoint_at,
                                "speech_end_estimate": endpoint_at-stop_seconds,
                                "speech_end_basis": "vad_endpoint_minus_silence" if stop_seconds else "explicit_endpoint",
                                "configured_silence_seconds": stop_seconds,
                                "stt_started": stt_started_at, "stt_completed": stt_completed_at},
                        }
                        metadata.update(owner._align_segment(
                            words, segment_start,
                            len(samples) / 16000))
                        metadata["recording_artifact"] = session.recording_name
                        if schedule_callback:
                            owner._schedule_callback(session, lambda: owner._accept_transcript(session, text, metadata))
                        else:
                            await owner._accept_transcript(session, text, metadata)

            async def force_endpoint(self) -> None:
                if self._active or self._audio.num_samples:
                    await self._finish_turn(libs["UserStoppedSpeakingFrame"](),
                                            libs["FrameDirection"].DOWNSTREAM, schedule_callback=False)

        session.interruption_done = asyncio.Event()
        session.tts_done.set()
        if state["stage"] != "COMPLETED":
            self._start_recording(session, state)
        else:
            session.input_failed = True

        class AudioBackpressureProcessor(libs["FrameProcessor"]):
            def __init__(self):
                # A queued processor cannot backpressure its producer: push_frame
                # otherwise just enqueues more audio in front of this guard.
                super().__init__(enable_direct_mode=True)

            async def process_frame(self, frame: Any, direction: Any) -> None:
                await super().process_frame(frame, direction)
                if isinstance(frame, libs["TTSStoppedFrame"]):
                    generation = getattr(frame, "context_id", None)
                    if session.interrupted or generation != session.generation_id:
                        return
                    await owner._send_audio_progress(session)
                    if (session.tts_done and generation == session.waiting_tts_generation
                            and generation == session.generation_id and not session.interrupted):
                        session.tts_done.set()
                    await self.push_frame(frame, direction)
                    return
                if frame.__class__.__name__ in {"OutputAudioRawFrame", "TTSAudioRawFrame"}:
                    generation = getattr(frame, "context_id", None)
                    if (session.interrupted or session.speech_failed or
                            generation != session.generation_id):
                        return
                    audio = getattr(frame, "audio", b"")
                    rate = int(getattr(frame, "sample_rate", 0) or 0)
                    channels = int(getattr(frame, "num_channels", 1) or 1)
                    duration = (len(audio) / (2 * rate * channels) * 1000) if rate else 0.0
                    async with session.audio_condition:
                        while (not session.closed and not session.interrupted
                               and generation == session.generation_id and
                               session.pending_audio_ms + duration > owner._max_audio_seconds * 1000):
                            await session.audio_condition.wait()
                        if (session.closed or session.interrupted or session.speech_failed or
                                generation != session.generation_id):
                            return
                        session.pending_audio_ms += duration
                        if session.generated_audio_ms == 0:
                            session.timings.setdefault("first_audio_admitted_server", time.time())
                        session.generated_audio_ms += duration
                        session.peak_pending_audio_ms = max(session.peak_pending_audio_ms, session.pending_audio_ms)
                    if int(session.generated_audio_ms)-session.audio_progress_ms >= 100 or session.audio_progress_ms == 0:
                        await owner._send_audio_progress(session)
                await self.push_frame(frame, direction)

        processor = TranscriptProcessor()
        session.force_endpoint = processor.force_endpoint
        audio_guard = AudioBackpressureProcessor()
        vad = libs["VADProcessor"](vad_analyzer=libs["SileroVADAnalyzer"](
            sample_rate=16000, params=libs["VADParams"](stop_secs=0.6)))
        tts = self._tts_processor(libs, session)
        class InterruptionBarrier(libs["FrameProcessor"]):
            async def process_frame(self, frame: Any, direction: Any) -> None:
                await super().process_frame(frame, direction)
                await self.push_frame(frame, direction)
                if isinstance(frame, libs["InterruptionFrame"]) and session.interruption_done:
                    session.interruption_done.set()

        pipeline = libs["Pipeline"]([transport.input(), vad, processor, tts, audio_guard, transport.output(), InterruptionBarrier()])
        task = libs["PipelineWorker"](pipeline, params=libs["PipelineParams"](), enable_rtvi=False)
        # Uvicorn owns process signals. Per-interview runners must not replace
        # its Ctrl+C handler or leave a finished runner handling server shutdown.
        runner = libs["WorkerRunner"](handle_sigint=False, handle_sigterm=False)
        session.task = task
        await runner.add_workers(task)
        await self._active_voice_state(session_id, lookup, authoritative_generation)
        session.pipeline_task = asyncio.create_task(runner.run(), name=f"voice-pipeline-{session_id}")
        session.sender_task = asyncio.create_task(self._send_text(session), name=f"voice-tts-{session_id}")
        self._bind_data_channel(session)
        return {"sdp": answer["sdp"] if isinstance(answer, dict) else answer.sdp,
                "type": answer["type"] if isinstance(answer, dict) else answer.type,
                "session_id": session_id, "generation_id": session.generation_id}

    def _input_samples(self, frame: Any, libs: dict[str, Any]) -> Any:
        np = libs["np"]
        pcm = np.frombuffer(frame.audio, dtype=np.int16)
        channels = int(getattr(frame, "num_channels", 1) or 1)
        if channels > 1:
            pcm = pcm.reshape(-1, channels).astype(np.float32).mean(axis=1)
        samples = pcm.astype(np.float32) / 32768.0
        rate = int(getattr(frame, "sample_rate", 16000) or 16000)
        if rate != 16000:
            divisor = math.gcd(rate, 16000)
            samples = libs["resample_poly"](samples, 16000 // divisor, rate // divisor)
        return samples.astype(np.float32, copy=False)

    @staticmethod
    def _align_segment(words: list[dict[str, Any]], start: float, duration: float) -> dict[str, Any]:
        """Align sample-derived offsets to session time, retaining original offsets."""
        return {"audio_interval": {"start": start, "end": start + duration},
                "session_words": [{**word, "start": start + float(word["start"]),
                                   "end": start + float(word["end"])} for word in words],
                "session_timestamp_basis": "seconds_since_session_creation",
                "clock_note": "Server connection offset plus decoded sample clock; transport delay is not measured."}

    def _start_recording(self, session: _Session, state: dict[str, Any]) -> None:
        if state.get("record_audio") is not True:
            return
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", session.session_id):
            raise ValueError("Session ID cannot be used as a local recording path")
        minutes = max(5, min(int(state.get("duration_minutes", 25)), 120)) + 5
        session.recording_sample_limit = minutes * 60 * 16000
        directory = self._data_dir / "sessions" / session.session_id
        directory.mkdir(parents=True, exist_ok=True)
        # Each connection gets a separate artifact so reconnect never overwrites
        # an earlier retained recording or invalidates its transcript provenance.
        session.recording_name = f"microphone-{time.time_ns()}.wav"
        writer = wave.open(str(directory / session.recording_name), "wb")
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(16000)
        session.recording = writer

    def _record_samples(self, session: _Session, samples: Any, libs: dict[str, Any]) -> None:
        if session.recording is None:
            return
        remaining = session.recording_sample_limit - session.recorded_samples
        if remaining <= 0:
            return
        count = min(remaining, len(samples))
        pcm = (libs["np"].clip(samples[:count], -1.0, 1.0) * 32767.0).astype(libs["np"].int16)
        session.recording.writeframesraw(pcm.tobytes())
        session.recorded_samples += count
        if count < len(samples) and not session.recording_limit_notified:
            session.recording_limit_notified = True
            asyncio.create_task(self._send_message(session, {
                "type": "recording_limit", "max_seconds": session.recording_sample_limit / 16000,
            }))

    def _transcribe(self, samples: Any) -> tuple[str, list[dict[str, Any]]]:
        segments, _info = self._whisper_model.transcribe(
            samples, language="en", beam_size=1, word_timestamps=True,
            condition_on_previous_text=False,
        )
        resolved = list(segments)
        text = " ".join(str(segment.text).strip() for segment in resolved).strip()
        words = [{"text": word.word, "start": word.start, "end": word.end}
                 for segment in resolved for word in (segment.words or [])]
        return text, words

    async def _transcribe_async(self, samples: Any) -> tuple[str, list[dict[str, Any]]]:
        # Cancelling an asyncio wrapper does not stop CUDA inference. Keep the
        # actual task owned until it finishes; reconnect cannot spawn copies.
        if self._stt_task and not self._stt_task.done():
            raise RuntimeError("Local transcription is still running")
        task = asyncio.create_task(asyncio.to_thread(self._transcribe, samples))
        self._stt_task = task
        task.add_done_callback(lambda finished: None if finished.cancelled() else finished.exception())
        return await asyncio.wait_for(asyncio.shield(task), 15)

    async def _synthesize_clause(self, text: str) -> Any:
        """Own one public Kokoro call even when its cancelled caller has left."""
        async with self._tts_lock:
            if self._tts_task and not self._tts_task.done():
                await asyncio.wait_for(asyncio.shield(self._tts_task), 15)
            task = asyncio.create_task(asyncio.to_thread(self._kokoro_model.create,
                text, voice="af_heart", speed=1.0, lang="en-us"))
            self._tts_task = task
            task.add_done_callback(lambda finished: None if finished.cancelled() else finished.exception())
            return await asyncio.wait_for(asyncio.shield(task), 15)

    def _tts_processor(self, libs: dict[str, Any], session: _Session) -> Any:
        owner = self

        class LocalKokoroProcessor(libs["FrameProcessor"]):
            async def process_frame(self, frame: Any, direction: Any) -> None:
                await super().process_frame(frame, direction)
                if isinstance(frame, libs["InterruptionWorkerFrame"]):
                    await self.push_frame(frame, direction)
                    return
                if not isinstance(frame, libs["TTSSpeakFrame"]):
                    await self.push_frame(frame, direction)
                    return
                generation = frame.metadata.get("generation_id")
                if (session.closed or session.interrupted or session.speech_failed or
                        generation != session.generation_id):
                    if session.tts_done: session.tts_done.set()
                    return
                await self.push_frame(libs["TTSStartedFrame"](context_id=generation), direction)
                try:
                    samples, rate = await owner._synthesize_clause(frame.text)
                    if session.closed or session.interrupted or generation != session.generation_id:
                        return
                    if not len(samples) or int(rate) <= 0:
                        raise RuntimeError("Kokoro returned no usable audio")
                    session.timings.setdefault("first_tts_chunk_server", time.time())
                    pcm = (libs["np"].clip(libs["np"].asarray(samples), -1.0, 1.0)
                           * 32767.0).astype(libs["np"].int16)
                    frame_samples = max(1, int(rate) // 50)
                    for offset in range(0, len(pcm), frame_samples):
                        if session.closed or session.interrupted or generation != session.generation_id:
                            break
                        chunk = pcm[offset:offset + frame_samples]
                        session.offered_audio_ms += len(chunk)/int(rate)*1000
                        await self.push_frame(libs["TTSAudioRawFrame"](
                            audio=chunk.tobytes(), sample_rate=int(rate), num_channels=1,
                            context_id=generation), direction)
                except Exception:
                    if session.closed or session.interrupted or generation != session.generation_id:
                        return
                    session.speech_failed = True
                    if session.tts_done:
                        session.tts_done.set()
                    owner._schedule_callback(session, lambda: owner._tts_failed(session))
                await self.push_frame(libs["TTSStoppedFrame"](context_id=generation), direction)

        return LocalKokoroProcessor()

    async def _tts_failed(self, session: _Session) -> None:
        try:
            await self.interrupt(session.session_id)
        finally:
            await self._send_message(session, {
                "type": "voice_error",
                "message": "Local speech synthesis failed. Continue with the displayed text; reconnect voice to retry speech.",
            })

    def is_connected(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        return bool(session and session.client_ready and not session.closed and session.pipeline_task and
                    not session.pipeline_task.done())

    def _bind_data_channel(self, session: _Session) -> None:
        @session.transport.event_handler("on_client_connected")
        async def on_client_connected(transport: Any, client: Any) -> None:
            if self._sessions.get(session.session_id) is session and not session.closed:
                async def ready():
                    await self._dispatch_control(session, "ready", {})
                    if not session.closed:
                        session.client_ready = True
                self._schedule_callback(session, ready)

        @session.transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport: Any, client: Any) -> None:
            # Return before cleanup: Pipecat joins transport event handlers while
            # shutting down the pipeline. Awaiting cleanup here would join itself.
            if self._sessions.get(session.session_id) is session and not session.closed:
                self._schedule_callback(session, lambda: self._client_disconnected(session))

        @session.transport.event_handler("on_app_message")
        async def on_app_message(transport: Any, message: Any, sender: Any) -> None:
            if isinstance(message, str):
                try: message = json.loads(message)
                except (TypeError, ValueError): return
            if not isinstance(message, dict): return
            kind = message.get("type")
            if kind == "playback_ack":
                await self.acknowledge_playback(session, message.get("generation_id"), message.get("played_ms"))
            elif kind in {"text_received", "text_displayed", "playback_started"}:
                await self._browser_milestone(session, message)
            elif kind in {"interrupt", "stop"}:
                await self._dispatch_control(session, kind, message)
            elif kind in {"pause", "done_speaking", "keep_thinking"}:
                await self._dispatch_control(session, kind, message)

    async def _client_disconnected(self, session: _Session) -> None:
        if self._sessions.get(session.session_id) is not session:
            return
        session.closed = True
        try:
            if session.on_control:
                result = session.on_control(session.session_id, "disconnect", {})
                if inspect.isawaitable(result):
                    await result
        finally:
            await self.close(session.session_id)

    async def _send_audio_progress(self, session: _Session) -> None:
        if session.closed or session.interrupted:
            return
        session.audio_progress_ms = int(session.generated_audio_ms)
        await self._send_message(session, {"type": "audio_progress", "generation_id": session.generation_id,
                                           "generated_ms": session.audio_progress_ms})

    async def acknowledge_playback(self, session: _Session, generation_id: Any, played_ms: Any) -> None:
        # Browser delivery is an estimate, never proof of hearing. Invalid,
        # duplicate, stale, or future credit must not corrupt backpressure state.
        if (session.closed or session.interrupted or generation_id != session.generation_id
                or type(played_ms) is not int or played_ms < 0):
            return
        async with session.audio_condition:
            played = min(played_ms, int(session.generated_audio_ms))
            delta = max(0, played-session.last_ack_played_ms)
            session.last_ack_played_ms = max(session.last_ack_played_ms, played)
            session.pending_audio_ms = max(0.0, session.pending_audio_ms-delta)
            session.playback_acked_ms = session.last_ack_played_ms
            session.audio_condition.notify_all()
        await self._maybe_delivery_complete(session)

    async def _browser_milestone(self, session: _Session, message: dict[str, Any]) -> None:
        if session.closed or session.interrupted or message.get("generation_id") != session.generation_id:
            return
        timestamp = message.get("client_time_ms")
        if type(timestamp) not in {int, float} or not 0 < timestamp < 2**53:
            return
        kind = message["type"]
        prior_displayed = session.displayed_text_chars
        key = {"text_received": "first_text_received_client_ms", "text_displayed": "first_text_displayed_client_ms",
               "playback_started": "first_playback_client_ms"}[kind]
        if kind == "text_displayed":
            count = message.get("characters")
            if type(count) is not int or count <= 0:
                return
            session.displayed_text_chars = max(session.displayed_text_chars, min(count, session.generated_text_chars))
        elif kind == "playback_started" and session.generated_audio_ms <= 0:
            return
        if kind.startswith("text_") and session.generated_text_chars <= 0:
            return
        first = key not in session.timings
        session.timings.setdefault(key, timestamp)
        session.timings.setdefault(key.replace("client_ms", "receipt_server"), time.time())
        full_display = (session.text_finished and prior_displayed < session.displayed_text_chars
                        and session.displayed_text_chars == session.generated_text_chars)
        if first or full_display:
            status = "estimated_complete" if session.delivery_complete else "playing" if "first_playback_client_ms" in session.timings else "buffering"
            await self._emit_delivery(session, status)

    async def _maybe_delivery_complete(self, session: _Session) -> None:
        if (not session.delivery_complete and not session.closed and not session.interrupted
                and session.text_finished and session.text_queue.empty()
                and session.tts_done and session.tts_done.is_set()
                and session.generated_audio_ms > 0 and session.pending_audio_ms < 1.01):
            session.delivery_complete = True
            await self._emit_delivery(session, "estimated_complete")

    async def _emit_delivery(self, session: _Session, status: str) -> None:
        if not self._on_event:
            return
        if session.generated_text_chars == 0 and session.generated_audio_ms == 0:
            return
        result = self._on_event(session.session_id, "voice_delivery", {
            "generation_id": session.generation_id, "status": status,
            "generated_text_chars": session.generated_text_chars, "displayed_text_chars": session.displayed_text_chars,
            "generated_audio_ms": session.generated_audio_ms, "estimated_played_ms": session.playback_acked_ms,
            "peak_pending_audio_ms": session.peak_pending_audio_ms, "timing": dict(session.timings),
            "delivery_note": "Browser playback acknowledgments estimate delivery; they do not prove hearing. Client milliseconds and server seconds use distinct clocks.",
        })
        if inspect.isawaitable(result):
            await result

    async def _dispatch_control(self, session: _Session, action: str,
                                payload: dict[str, Any]) -> None:
        if session.on_control:
            result = session.on_control(session.session_id, action, payload)
            if inspect.isawaitable(result):
                await result
        if action in {"interrupt", "stop", "pause", "input_limit"}:
            await self.interrupt(session.session_id)
        elif action == "done_speaking":
            if session.input_failed:
                return
            session.defer_answers = True
            if session.force_endpoint:
                await session.force_endpoint()
            if session.input_failed:
                return
            session.defer_answers = False
            held = list(session.held_answers or [])
            if session.held_answers is not None:
                session.held_answers.clear()
            if held:
                # Keep thinking is one candidate turn even across VAD pauses.
                # Separate segment timing remains distinguishable; do not pretend
                # concatenated word times form a continuous audio interval.
                combined = " ".join(text.strip() for text, _ in held if text.strip())
                metadata = {"source": "local-faster-whisper", "language": "en", "final": True,
                            "held_segments": [details for _, details in held],
                            "audio_duration_seconds": sum(details.get("audio_duration_seconds", 0) for _, details in held)}
                if held[-1][1].get("timing"):
                    metadata["timing"] = held[-1][1]["timing"]
                if len(held) == 1:
                    metadata = held[0][1]
                if combined:
                    await self._deliver_answer(session, combined, metadata)
        elif action == "keep_thinking":
            session.defer_answers = True

    async def send_text(self, session_id: str, text: str, generation_id: str) -> None:
        """Speak only the unsent suffix of the durable assistant text."""
        session = self._sessions.get(session_id)
        if not session or session.closed:
            raise RuntimeError("Voice session is not connected")
        if session.speech_failed:
            return
        async with session.text_lock:
            offset = session.generated_text_chars if generation_id == session.generation_id else 0
            await self._send_text_delta(session_id, text[offset:], generation_id)

    async def _send_text_delta(self, session_id: str, text: str, generation_id: str) -> None:
        state = await self._session_state(session_id)
        if not state:
            raise PermissionError("Session not found or not owned by caller")
        session = self._sessions.get(session_id)
        if not session or session.closed: raise RuntimeError("Voice session is not connected")
        if session.speech_failed:
            return
        if generation_id != state.get("generation_id"): return
        if generation_id != session.generation_id:
            session.generation_id = generation_id
            session.interrupted = False
            session.text_buffer = ""
            session.last_ack_played_ms = 0
            session.playback_acked_ms = 0
            session.generated_audio_ms = 0.0
            session.offered_audio_ms = 0.0
            session.audio_progress_ms = 0
            session.peak_pending_audio_ms = 0.0
            session.generated_text_chars = 0
            session.displayed_text_chars = 0
            session.text_finished = False
            session.delivery_complete = False
            session.timings = {}
        elif session.interrupted:
            return
        delta = str(text)
        if not delta: return
        session.generated_text_chars += len(delta)
        session.generation_active = True
        await self._send_message(session, {"type": "assistant_text", "text": delta,
                                           "generation_id": generation_id})
        session.text_buffer += delta
        clauses, session.text_buffer = self._take_complete_clauses(session.text_buffer)
        for clause in clauses:
            if generation_id != session.generation_id or session.closed: return
            speech_clause = re.sub(r"\s+", " ", clause).strip()
            if speech_clause:
                await session.text_queue.put((generation_id, speech_clause))

    async def speak_saved_text(self, session_id: str, text: str, generation_id: str, *, finished: bool = True) -> None:
        """Catch up a new connection once; never duplicate text already streamed."""
        session = self._sessions.get(session_id)
        if not session or session.closed:
            return
        async with session.text_lock:
            if session.interrupted or session.generated_text_chars or session.generation_id != generation_id:
                return
            # Publish readiness only after owning the saved prefix. Live deltas
            # then wait for this prefix rather than overtaking or duplicating it.
            session.client_ready = True
            await self._send_text_delta(session_id, text, generation_id)
            if finished:
                await self._finish_text(session_id, generation_id)


    async def finish_text(self, session_id: str, generation_id: str) -> None:
        """Flush the final partial clause when provider streaming completes."""
        session = self._sessions.get(session_id)
        if not session or session.closed:
            return
        async with session.text_lock:
            await self._finish_text(session_id, generation_id)

    async def _finish_text(self, session_id: str, generation_id: str) -> None:
        state = await self._session_state(session_id)
        session = self._sessions.get(session_id)
        if not state or not session or session.closed or session.interrupted:
            return
        if generation_id != state.get("generation_id") or generation_id != session.generation_id:
            return
        remaining, session.text_buffer = session.text_buffer.strip(), ""
        session.generation_active = False
        if remaining:
            speech_clause = re.sub(r"\s+", " ", remaining).strip()
            if speech_clause:
                await session.text_queue.put((generation_id, speech_clause))
        session.text_finished = True
        await self._maybe_delivery_complete(session)

    async def _session_state(self, session_id: str) -> Any:
        if not self._get_session:
            return None
        value = self._get_session(session_id)
        return await value if inspect.isawaitable(value) else value

    @staticmethod
    def _take_complete_clauses(text: str) -> tuple[list[str], str]:
        # Keep technical identifiers intact; split only at sentence/semicolon boundaries.
        matches = list(re.finditer(r"(?<=[.!?;])\s+", text))
        if not matches:
            return [], text
        end = matches[-1].end()
        # The unfinished suffix is still provider text: its trailing space may
        # separate this delta's final word from the next delta's first word.
        ready, rest = text[:end].strip(), text[end:]
        return [part.strip() for part in re.split(r"(?<=[.!?;])\s+", ready) if part.strip()], rest

    async def _send_text(self, session: _Session) -> None:
        try:
            while True:
                item = await session.text_queue.get()
                if item is None: return
                generation, clause = item
                if session.closed or session.interrupted or session.speech_failed or generation != session.generation_id: continue
                session.synth_generation = generation
                session.waiting_tts_generation = generation
                if session.tts_done: session.tts_done.clear()
                session.timings.setdefault("first_tts_clause_server", time.time())
                frame = self._load_runtime()["TTSSpeakFrame"](clause, append_to_context=False)
                frame.metadata["generation_id"] = generation
                await session.task.queue_frames([frame])
                if session.tts_done:
                    await session.tts_done.wait()
                await self._maybe_delivery_complete(session)
        except asyncio.CancelledError:
            raise

    async def _send_message(self, session: _Session, message: dict[str, Any]) -> None:
        sender = getattr(session.connection, "send_app_message", None)
        if sender is None:
            raise RuntimeError("SmallWebRTC connection does not support app messages")
        result = sender(message)
        if inspect.isawaitable(result):
            await result

    async def send_event(self, session_id: str, event: dict[str, Any]) -> None:
        session = self._sessions.get(session_id)
        if not session or session.closed:
            return
        state = await self._session_state(session_id)
        if not state or (event.get("generation_id") and event["generation_id"] != state["generation_id"]):
            return
        await self._send_message(session, event)

    async def _accept_transcript(self, session: _Session, text: str,
                                 metadata: dict[str, Any]) -> None:
        if getattr(session, "closed", False) or getattr(session, "input_failed", False):
            return
        held = session.held_answers or []
        if len(text) + sum(len(part) + 1 for part, _ in held) > 12000 or len(held) >= 32:
            session.input_failed = True
            draft = " ".join([*(part for part, _ in held), text])[:12000]
            await self._input_failed(session,
                "The spoken draft exceeded the input limit and was not submitted. Up to 12,000 characters were saved; review and shorten the typed draft before sending, or reconnect voice.", draft)
            return
        if session.defer_answers:
            if session.held_answers is None:
                session.held_answers = []
            session.held_answers.append((text, metadata))
            return
        await self._deliver_answer(session, text, metadata)

    async def _input_failed(self, session: _Session, message: str, draft: str | None = None) -> None:
        if draft is None:
            draft = " ".join(text for text, _ in (session.held_answers or []))[:12000]
        await self._dispatch_control(session, "input_limit", {"draft_text": draft, "message": message})
        session.held_answers = None
        await self._send_message(session, {"type": "voice_error", "message": message})
        await self.close(session.session_id)

    def _schedule_callback(self, session: _Session, callback: Callable[[], Awaitable[Any]]) -> None:
        """Keep application cancellation outside Pipecat's interruptible frame loop."""
        async def run():
            try:
                await callback()
            except asyncio.CancelledError:
                raise
            except Exception:
                if not session.closed:
                    try:
                        await self._send_message(session, {
                            "type": "voice_error",
                            "message": "Spoken response could not be committed. Check the transcript, then retry or type your answer.",
                        })
                    except (RuntimeError, OSError):
                        pass
        if session.callback_tasks is None:
            session.callback_tasks = set()
        task = asyncio.create_task(run(), name=f"voice-callback-{session.session_id}")
        session.callback_tasks.add(task)
        task.add_done_callback(session.callback_tasks.discard)

    async def _deliver_answer(self, session: _Session, text: str,
                              metadata: dict[str, Any]) -> None:
        if not session.on_answer:
            return
        result = session.on_answer(session.session_id, text, metadata)
        if inspect.isawaitable(result):
            await result

    async def interrupt(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if not session or session.closed: return
        async with session.lock:
            old = session.generation_id
            state = await self._session_state(session_id)
            authoritative = (state or {}).get("generation_id", old)
            # The application session owns generation IDs. Voice invalidates its
            # local queue and playback but never invents a parallel ID namespace.
            # Keep the active utterance ID until a later delta carries the newer
            # authoritative ID; this lets that delta start the next generation.
            session.interrupted = True
            session.generation_active = False
            if session.tts_done:
                session.tts_done.set()
            session.last_ack_played_ms = 0
            async with session.audio_condition:
                session.pending_audio_ms = 0.0
                session.audio_condition.notify_all()
            while not session.text_queue.empty():
                try: session.text_queue.get_nowait()
                except asyncio.QueueEmpty: break
            await self._send_message(session, {"type": "interrupt", "generation_id": old,
                                                "authoritative_generation_id": authoritative})
            try:
                if session.interruption_done:
                    session.interruption_done.clear()
                await session.task.queue_frame(self._load_runtime()["InterruptionWorkerFrame"]())
                if session.interruption_done:
                    await asyncio.wait_for(session.interruption_done.wait(), 5)
            except (ImportError, AttributeError, TypeError, RuntimeError):
                pass
            if not session.delivery_complete:
                await self._emit_delivery(session, "unavailable" if session.speech_failed else "interrupted")

    async def close(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            initializing = getattr(session, "offer_task", None)
            if initializing and initializing is not asyncio.current_task() and not initializing.done():
                initializing.cancel()
                await asyncio.gather(initializing, return_exceptions=True)
                if self._sessions.get(session_id) is not session:
                    return
            task = getattr(session, "cleanup_task", None)
            if task is None or task.done():
                task = asyncio.create_task(self._close(session), name=f"voice-close-{session_id}")
                session.cleanup_task = task
                def completed(finished):
                    if not finished.cancelled() and finished.exception() is None and self._sessions.get(session_id) is session:
                        self._sessions.pop(session_id, None)
                task.add_done_callback(completed)
            # A pipeline close cancels application callbacks, including a callback
            # that requested the close. Keep cleanup owned independently so that
            # cancelling its waiter cannot cancel recording/transport release.
            await asyncio.shield(task)

    async def close_all(self) -> None:
        await asyncio.gather(*(self.close(session_id) for session_id in tuple(self._sessions)), return_exceptions=True)

    async def _close(self, session: _Session) -> None:
        if getattr(session, "cleanup_complete", False): return
        session.closed = True
        if not getattr(session, "delivery_complete", False):
            try:
                await self._emit_delivery(session, "closed")
            except Exception:
                # Delivery diagnostics must not prevent transport/recording release.
                pass
        async with session.audio_condition:
            session.pending_audio_ms = 0.0
            session.audio_condition.notify_all()
        callbacks = tuple(task for task in (getattr(session, "callback_tasks", None) or ())
                          if task is not asyncio.current_task())
        for callback in callbacks:
            callback.cancel()
        if callbacks:
            await asyncio.gather(*callbacks, return_exceptions=True)
        for task in (session.sender_task, session.pipeline_task):
            if task and not task.done(): task.cancel()
        for task in (session.sender_task, session.pipeline_task):
            if task:
                try: await task
                except (asyncio.CancelledError, Exception): pass
        try:
            close = getattr(session.connection, "disconnect", None)
            if close:
                result = close()
                if inspect.isawaitable(result): await result
        finally:
            if session.recording is not None:
                session.recording.close()
                session.recording = None
        session.cleanup_complete = True
