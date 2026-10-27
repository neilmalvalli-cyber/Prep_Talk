"""Real local synthesis smoke for speech-only technical pronunciation."""
import asyncio
import json
import os
import re
from pathlib import Path

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'

from interviewer.voice import VoiceManager


def experimental_spelling(text):
    names = {'API': 'A P I', 'TTL': 'T T L', 'HTTP': 'H T T P', 'HTTPS': 'H T T P S',
             'SQL': 'S Q L', 'JSON': 'J S O N', 'UI': 'U I'}
    text = re.sub(r'\b(?:API|TTL|HTTP|HTTPS|SQL|JSON|UI)\b', lambda m: names[m.group()], text)
    return text.replace('C++', 'C plus plus')


async def main():
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly
    root = Path(__file__).resolve().parents[1]
    manager = VoiceManager(model_dir=root/'data/models', data_dir=root/'data')
    readiness = await manager.warmup()
    if not readiness['ready']:
        raise RuntimeError('Local speech warmup unavailable')
    output = root/'data/speech-pronunciation-check'
    output.mkdir(exist_ok=True)
    samples = []
    for index, original in enumerate([
        'How did your API use a TTL?',
        'Would HTTP or HTTPS change your SQL query?',
        'How did the C++ program parse JSON for the UI?',
    ]):
        comparisons = []
        for mode in ('original', 'experimental_letter_spacing'):
            synthesis_text = experimental_spelling(original) if mode != 'original' else original
            audio, rate = await manager._synthesize_clause(synthesis_text)
            assert rate == 24000 and len(audio)
            sf.write(output/f'{index+1}-{mode}.wav', audio, rate)
            pcm = resample_poly(np.asarray(audio, dtype=np.float32), 2, 3).astype(np.float32)
            text, _ = await manager._transcribe_async(pcm)
            comparisons.append({'mode': mode, 'synthesis_text': synthesis_text,
                                'synthetic_round_trip_transcript': text, 'audio_seconds': len(audio)/rate})
        samples.append({'original_display_text': original, 'comparisons': comparisons})
    result = {'scope': 'Real local CPU Kokoro/CUDA Whisper on three synthetic prompts; no human listening or acoustic microphone claim.',
              'application_pronunciation_changed': False, 'samples': samples}
    (root/'docs/speech-pronunciation-results.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)


asyncio.run(main())
