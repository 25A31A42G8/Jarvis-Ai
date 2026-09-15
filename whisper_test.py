from faster_whisper import WhisperModel
import sounddevice as sd
import wave

print("Loading Whisper model...")
model = WhisperModel("tiny", device="cpu", compute_type="int8")

sample_rate = 16000
seconds = 5

print("Speak now...")
audio = sd.rec(
    int(seconds * sample_rate),
    samplerate=sample_rate,
    channels=1,
    dtype="int16"
)
sd.wait()

with wave.open("voice.wav", "wb") as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(sample_rate)
    f.writeframes(audio.tobytes())

print("Transcribing...")

segments, info = model.transcribe("voice.wav")

text = " ".join(segment.text for segment in segments)

print()
print("You said:", text)