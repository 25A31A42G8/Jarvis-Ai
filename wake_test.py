import sounddevice as sd
import numpy as np
from openwakeword.model import Model
import time

model = Model(
    wakeword_models=["hey_jarvis"],
    inference_framework="onnx"
)

detected = False
last_detection = 0

print("🤖 Jarvis is ready.")
print("Say: Hey Jarvis")
print("Press Ctrl+C to stop.")

def callback(indata, frames, time_info, status):
    global detected, last_detection

    audio = (indata[:, 0] * 32767).astype(np.int16)
    prediction = model.predict(audio)
    score = prediction["hey_jarvis"]

    now = time.time()

    if score > 0.5 and now - last_detection > 2:
        print(f"\n🎯 Hey Jarvis! Score: {score:.2f}")
        last_detection = now

with sd.InputStream(
    device=1,
    samplerate=16000,
    channels=1,
    dtype="float32",
    blocksize=1280,
    callback=callback
):
    while True:
        sd.sleep(1000)