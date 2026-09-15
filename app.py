import ollama
import sqlite3
from datetime import datetime

import sounddevice as sd
import numpy as np
import wave
import pyttsx3

from faster_whisper import WhisperModel
from openwakeword.model import Model
from ddgs import DDGS


# =========================
# SETTINGS
# =========================

OLLAMA_MODEL = "llama3.2:3b"

MIC_DEVICE = 1
SAMPLE_RATE = 16000

# =========================
# MEMORY
# =========================

conn = sqlite3.connect("memory.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT,
    created_at TEXT
)
""")

conn.commit()


def remember(text):
    cursor.execute(
        "INSERT INTO memories (text, created_at) VALUES (?, ?)",
        (text, datetime.now().isoformat())
    )
    conn.commit()


def get_memories():
    cursor.execute(
        "SELECT text FROM memories ORDER BY id DESC LIMIT 20"
    )
    rows = cursor.fetchall()

    if not rows:
        return "No memories stored."

    return "\n".join(row[0] for row in rows)


# =========================
# WHISPER
# =========================

print("Loading Whisper...")
whisper = WhisperModel(
    "tiny",
    device="cpu",
    compute_type="int8"
)

# =========================
# WAKE WORD
# =========================

print("Loading wake-word engine...")

wake_model = Model(
    wakeword_models=["hey_jarvis"],
    inference_framework="onnx"
)

# =========================
# VOICE OUTPUT
# =========================


def speak(text):
    print("Jarvis:", text)

    engine = pyttsx3.init()
    engine.setProperty("rate", 170)

    engine.say(text)
    engine.runAndWait()
    engine.stop()


# =========================
# RECORD + TRANSCRIBE
# =========================


def listen():
    print("\n🎤 Listening...")

    duration = 5

    recording = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        device=MIC_DEVICE
    )

    sd.wait()

    filename = "voice.wav"

    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(recording.tobytes())

    segments, info = whisper.transcribe(
        filename,
        beam_size=1
    )

    text = " ".join(
        segment.text for segment in segments
    ).strip()

    return text


# =========================
# WAKE WORD LISTENER
# =========================


def wait_for_wake_word():

    print("\n🤖 Jarvis is waiting...")
    print("Say: Hey Jarvis")

    detected = False

    def callback(indata, frames, time_info, status):

        nonlocal detected

        audio = (
            indata[:, 0] * 32767
        ).astype(np.int16)

        prediction = wake_model.predict(audio)

        score = prediction["hey_jarvis"]

        if score > 0.5:
            detected = True

    with sd.InputStream(
        device=MIC_DEVICE,
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=1280,
        callback=callback
    ):

        while not detected:
            sd.sleep(100)

    print("🎯 Hey Jarvis detected!")


# =========================
# WEB SEARCH
# =========================


def web_search(query):

    print("🌐 Searching the web...")

    try:

        results = DDGS().text(
            query,
            region="in-en",
            max_results=5
        )

        formatted = ""

        for result in results:

            formatted += (
                f"\nTITLE: {result['title']}"
                f"\nURL: {result['href']}"
                f"\nINFO: {result['body']}\n"
            )

        return formatted

    except Exception as e:

        return f"Search failed: {e}"


# =========================
# STARTUP
# =========================

print("\n==============================")
print("🤖 JARVIS PERSONAL AI")
print("==============================")

speak("Jarvis is online.")


# =========================
# MAIN LOOP
# =========================

while True:

    # Wait for Hey Jarvis
    wait_for_wake_word()

    speak("Yes?")

    # Listen to command
    user_input = listen()

    if not user_input:
        continue

    print("You:", user_input)

    # -------------------------
    # EXIT
    # -------------------------

    if user_input.lower() in [
        "exit",
        "quit",
        "goodbye",
        "stop"
    ]:
        speak("Goodbye.")
        break

    # -------------------------
    # REMEMBER
    # -------------------------

    if user_input.lower().startswith("remember "):

        memory = user_input[9:].strip()

        remember(memory)

        speak("I'll remember that.")

        continue

    # -------------------------
    # WEB SEARCH
    # -------------------------

    if user_input.lower().startswith("search the web"):

        query = user_input[len("search the web"):].strip()

        results = web_search(query)

        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content":
                    "Answer using only the provided web search results. "
                    "If the results are insufficient, say so. "
                    "Keep the answer concise."
                },
                {
                    "role": "user",
                    "content":
                    f"Question: {query}\n\n"
                    f"Search results:\n{results}"
                }
            ]
        )

        answer = response["message"]["content"]

        speak(answer)

        continue
    # -------------------------
    # TIME
    # -------------------------

    if "current time" in user_input.lower() or "what time is it" in user_input.lower():

        current_time = datetime.now().strftime("%I:%M %p")

        speak(f"The current time is {current_time}.")

        continue
    # -------------------------
    # DATE
    # -------------------------

    if (
        "today's date" in user_input.lower()
        or "what date is it" in user_input.lower()
        or "what day is it" in user_input.lower()
    ):

        today = datetime.now().strftime("%A, %B %d, %Y")

        speak(f"Today is {today}.")

        continue
    # -------------------------
    # CALCULATOR
    # -------------------------
    if user_input.lower().startswith("calculate "):
        expression = user_input[10:].strip().lower()

        expression = expression.replace("times", "*")
        expression = expression.replace("multiplied by", "*")
        expression = expression.replace("plus", "+")
        expression = expression.replace("minus", "-")
        expression = expression.replace("divided by", "/")

        try:
            import ast
            import operator

            allowed = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
            }

            def safe_calc(node):
                if isinstance(node, ast.Expression):
                    return safe_calc(node.body)
                if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                    return node.value
                if isinstance(node, ast.BinOp) and type(node.op) in allowed:
                    return allowed[type(node.op)](
                        safe_calc(node.left),
                        safe_calc(node.right)
                    )
                if isinstance(node, ast.UnaryOp) and type(node.op) in allowed:
                    return allowed[type(node.op)](safe_calc(node.operand))
                raise ValueError

            tree = ast.parse(expression, mode="eval")
            result = safe_calc(tree)

            speak(f"The answer is {result}.")

        except Exception:
            speak("I couldn't calculate that.")

        continue
    # SYSTEM COMMANDS
    lower_input = user_input.lower()

    if "hello" in lower_input or "hi jarvis" in lower_input:
        speak("Hello. How can I help you?")
        continue

    if "who are you" in lower_input:
        speak("I am Jarvis, your personal AI assistant.")
        continue

    if "what can you do" in lower_input:
        speak("I can answer questions, remember information, search the web, calculate, and respond to your voice.")
        continue
    # -------------------------
    # NORMAL AI
    # -------------------------

    memories = get_memories()

    memory_text = "\n".join(
        [f"- {m[0]}" for m in memories]
    )

    system_prompt = f"""
You are Jarvis, a helpful personal AI assistant.

Here are the user's saved memories:
{memory_text}

Use these memories when they are relevant.
Be concise and conversational.
"""

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    )

    answer = response["message"]["content"]
    print("Jarvis:", answer)
    speak(answer)