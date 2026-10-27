"""Generate local, synthetic microphone input for browser acceptance, never candidate audio."""
import wave
from pathlib import Path

import numpy as np
from kokoro_onnx import Kokoro

root = Path(__file__).resolve().parents[1]
models = root / "data/models"
model = Kokoro(str(models / "kokoro-v1.0.onnx"), str(models / "voices-v1.0.bin"))
text = "I invalidated the cache after the write."
samples, rate = model.create(text, voice="af_heart", speed=1.0, lang="en-us")
destination = root / "data/browser-synthetic-microphone.wav"
with wave.open(str(destination), "wb") as output:
    output.setnchannels(1)
    output.setsampwidth(2)
    output.setframerate(rate)
    output.writeframes((np.clip(samples, -1, 1) * 32767).astype(np.int16).tobytes())
print(f"Synthetic microphone fixture: {destination}; source: {text}")
