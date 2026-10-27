"""Verify shared warmup with real local models, without cloud or runner calls."""
import asyncio
import json
import os
import threading
import time
from pathlib import Path
from unittest.mock import patch

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'

import faster_whisper
import kokoro_onnx
from interviewer.voice import VoiceManager


async def main():
    root = Path(__file__).resolve().parents[1]
    manager = VoiceManager(model_dir=root/'data/models', data_dir=root/'data')
    calls = []
    started = threading.Event()
    whisper_type, kokoro_type = faster_whisper.WhisperModel, kokoro_onnx.Kokoro

    def load_whisper(*args, **kwargs):
        calls.append('whisper')
        started.set()
        return whisper_type(*args, **kwargs)

    def load_kokoro(*args, **kwargs):
        calls.append('kokoro')
        return kokoro_type(*args, **kwargs)

    before = time.monotonic()
    with patch.object(faster_whisper, 'WhisperModel', load_whisper), \
            patch.object(kokoro_onnx, 'Kokoro', load_kokoro):
        first = asyncio.create_task(manager.warmup())
        try:
            assert await asyncio.to_thread(started.wait, 30), 'native load did not start'
            owned = manager._warmup_task
            assert not owned.done(), 'warmup completed before cancellation probe'
            first.cancel()
            try:
                await first
                raise AssertionError('caller cancellation was ignored')
            except asyncio.CancelledError:
                pass
            assert not owned.cancelled() and manager._warmup_task is owned
            ready = await asyncio.wait_for(manager.warmup(), 150)
            assert ready['ready'], ready
            assert manager._warmup_task is owned
            assert sorted(calls) == ['kokoro', 'whisper'], calls
            models = manager._whisper_model, manager._kokoro_model
            assert (await manager.warmup())['ready']
            assert (manager._whisper_model, manager._kokoro_model) == models
            assert sorted(calls) == ['kokoro', 'whisper'], calls
        finally:
            await asyncio.gather(first, return_exceptions=True)
            if manager._warmup_task:
                await manager._warmup_task
    result = {
        'real_local_models': True,
        'cloud_or_runner_calls': False,
        'cancelled_waiter_does_not_cancel_native_loading': True,
        'replacement_waiter_shares_owned_task': True,
        'native_model_constructor_calls': calls,
        'subsequent_warmup_reuses_models': True,
        'elapsed_seconds': time.monotonic()-before,
        'readiness': ready,
        'scope': 'Real CUDA Whisper and CPU Kokoro loading/warmup; no physical microphone or provider connectivity claim.',
    }
    (root/'docs/warmup-cancellation-results.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)


asyncio.run(main())
