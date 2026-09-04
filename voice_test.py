import sounddevice as sd

print("Microphone test")
print("Recording for 5 seconds...")

sample_rate = 16000

recording = sd.rec(
    int(5 * sample_rate),
    samplerate=sample_rate,
    channels=1,
    dtype="float32"
)

sd.wait()

print("Recording finished!")
print("Your microphone is working.")