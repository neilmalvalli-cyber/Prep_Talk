"""Measure fixed CPU thread profiles with the provisioned model; no cloud/runner."""
import gc
import json
import os
import statistics
import time
from pathlib import Path

import onnxruntime as ort
from kokoro_onnx import Kokoro

root=Path(__file__).resolve().parents[1]
question='How did you handle a successful write followed by failed invalidation?'
result={'model':'provisioned kokoro-v1.0.onnx','voice':'af_heart','provider':'CPUExecutionProvider',
        'logical_cpus':os.cpu_count(),'synthetic_text':question,'profiles':[]}
for threads in (0,1,2,4):
    start=time.perf_counter()
    options=ort.SessionOptions()
    options.intra_op_num_threads=threads
    options.inter_op_num_threads=1
    session=ort.InferenceSession(str(root/'data/models/kokoro-v1.0.onnx'),
        sess_options=options,providers=['CPUExecutionProvider'])
    model=Kokoro.from_session(session,str(root/'data/models/voices-v1.0.bin'))
    model.create('Ready.',voice='af_heart',speed=1.0,lang='en-us')
    preparation=time.perf_counter()-start
    samples=[]
    for index in range(3):
        before=time.perf_counter()
        audio,rate=model.create(question,voice='af_heart',speed=1.0,lang='en-us')
        samples.append({'sample':index+1,'synthesis_seconds':time.perf_counter()-before,
                        'audio_seconds':len(audio)/rate,'sample_rate':rate})
    profile={'intra_op_threads':threads,'inter_op_threads':1,'preparation_and_warmup_seconds':preparation,
             'samples':samples,'median_synthesis_seconds':statistics.median(s['synthesis_seconds'] for s in samples)}
    result['profiles'].append(profile)
    (root/'docs/tts-cpu-profiles.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(profile),flush=True)
    del model,session
    gc.collect()
