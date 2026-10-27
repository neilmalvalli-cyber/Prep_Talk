"""Compare provisioned FP32/INT8 Kokoro on CPU; never change runtime defaults.

Run in the WSL speech environment. This uses synthetic text and the real local
Whisper model for a round trip, not human listening or production latency.
"""
import gc
import hashlib
import json
import os
import statistics
import time
from pathlib import Path

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'

import numpy as np
import onnxruntime as ort
import soundfile as sf
from faster_whisper import WhisperModel
from kokoro_onnx import Kokoro
from scipy.signal import resample_poly

root = Path(__file__).resolve().parents[1]
models = root/'data/models'
output = root/'data/tts-precision-comparison'
output.mkdir(exist_ok=True)
phrases = [
    'How did you handle a successful write followed by failed invalidation?',
    'The reader and the invalidation use different cache keys.',
    'Did you compare the median latency or the ninety fifth percentile?',
    'The expiry was sixty seconds, not sixty milliseconds.',
    'The read came from a replica while the cache was bypassed.',
    'How did you discard an older response after a newer request completed?',
]
result = {'scope': 'Real local CPU Kokoro and CUDA Whisper, synthetic text only; no human listening review or integrated latency claim.',
          'voice': 'af_heart', 'speed': 1.0, 'provider': 'CPUExecutionProvider',
          'logical_cpus': os.cpu_count(), 'application_default_changed': False, 'profiles': []}
whisper = WhisperModel(str(models/'faster-whisper-large-v3-turbo'), device='cuda', compute_type='int8_float16')
list(whisper.transcribe(np.zeros(16000, dtype=np.float32), language='en', beam_size=1)[0])
for name in ('kokoro-v1.0.onnx', 'kokoro-v1.0.int8.onnx'):
    path = models/name
    model = Kokoro.from_session(ort.InferenceSession(str(path), providers=['CPUExecutionProvider']), str(models/'voices-v1.0.bin'))
    start = time.perf_counter()
    model.create('Ready.', voice='af_heart', speed=1.0, lang='en-us')
    profile = {'model': name, 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
               'warmup_seconds': time.perf_counter()-start, 'timing_samples': [], 'round_trips': []}
    for index in range(3):
        start = time.perf_counter()
        audio, rate = model.create(phrases[0], voice='af_heart', speed=1.0, lang='en-us')
        profile['timing_samples'].append({'sample': index+1, 'synthesis_seconds': time.perf_counter()-start, 'audio_seconds': len(audio)/rate})
    for index, phrase in enumerate(phrases):
        start = time.perf_counter()
        audio, rate = model.create(phrase, voice='af_heart', speed=1.0, lang='en-us')
        synthesis = time.perf_counter()-start
        sf.write(output/f'{path.stem}-{index+1}.wav', audio, rate)
        pcm = resample_poly(np.asarray(audio, dtype=np.float32), 2, 3).astype(np.float32)
        assert rate == 24000
        segments, _ = whisper.transcribe(pcm, language='en', beam_size=1, condition_on_previous_text=False)
        transcript = ' '.join(segment.text.strip() for segment in segments)
        profile['round_trips'].append({'source': phrase, 'transcript': transcript, 'synthesis_seconds': synthesis,
                                      'audio_seconds': len(audio)/rate})
    profile['median_synthesis_seconds'] = statistics.median(item['synthesis_seconds'] for item in profile['timing_samples'])
    result['profiles'].append(profile)
    (root/'docs/tts-precision-profiles.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(profile), flush=True)
    del model
    gc.collect()
