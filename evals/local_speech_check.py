"""Actual local-model smoke; no cloud provider or runner. Run in WSL voice venv."""
import asyncio
import json
import os
import socket
import sys
import time
from pathlib import Path

os.environ['HF_HUB_OFFLINE']='1'
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
from interviewer.voice import VoiceManager


async def main():
    root=Path(__file__).resolve().parents[1]
    isolated='--network-isolated' in sys.argv
    if isolated and any(name!='lo' for _,name in socket.if_nameindex()):
        raise SystemExit('Offline check requires a network namespace with only loopback.')
    voice=VoiceManager(model_dir=root/'data/models',data_dir=root/'data')
    start=time.monotonic()
    readiness=await voice.warmup()
    result={'real_local_models':True,'readiness':readiness,'cold_warmup_seconds':time.monotonic()-start,'internet_blocked_at_os_level':isolated,'hf_offline_environment':True,'checks':[]}
    if readiness['ready']:
        import numpy as np
        from scipy.signal import resample_poly
        from math import gcd
        phrase='The reader and the invalidation use different cache keys.'
        for index in range(3):
            before=time.monotonic()
            samples,rate=await asyncio.to_thread(voice._kokoro_model.create,phrase,voice='af_heart',speed=1.0,lang='en-us')
            tts=time.monotonic()-before
            factor=gcd(int(rate),16000)
            pcm=resample_poly(np.asarray(samples,dtype=np.float32),16000//factor,int(rate)//factor).astype(np.float32)
            before=time.monotonic()
            text,words=await asyncio.to_thread(voice._transcribe,pcm)
            result['checks'].append({'sample':index+1,'synthetic_source_text':phrase,'transcript':text,'word_count':len(words),'tts_seconds':tts,'stt_seconds':time.monotonic()-before,'audio_seconds':len(pcm)/16000})
    destination=root/('docs/local-speech-offline-results.json' if isolated else 'docs/local-speech-results.json')
    destination.write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    if not readiness['ready']:raise SystemExit(1)


asyncio.run(main())
