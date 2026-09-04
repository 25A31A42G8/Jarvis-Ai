import ollama
import sqlite3
import datetime
import re
import ast
import operator
import subprocess
import time
import threading

import numpy as np
import sounddevice as sd
import wave
import pyttsx3

from faster_whisper import WhisperModel
from ddgs import DDGS
from openwakeword.model import Model

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = r"C:\PersonalAI"
DB_FILE = r"C:\PersonalAI\memory.db"

OLLAMA_MODEL = "llama3.2:3b"

SERVER_URL = "http://127.0.0.1:5000"

MIC_DEVICE = 1
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 1280

RECORD_SECONDS = 5

WAKE_WORD = "hey_jarvis"
WAKE_THRESHOLD = 0.5
WAKE_COOLDOWN = 2

# ============================================================
# OPTIONAL SERVER COMMUNICATION
# ============================================================

try:
    import requests
except Exception:
    requests = None


def set_status(state, message=""):
    """Send Jarvis state to the frontend server."""
    if requests is None:
        return

    try:
        requests.post(
            SERVER_URL + "/status",
            json={
                "status": state,
                "message": message
            },
            timeout=1
        )
    except Exception:
        pass


def send_message(role, message):
    """Send a conversation message to the frontend."""
    if requests is None:
        return

    try:
        requests.post(
            SERVER_URL + "/message",
            json={
                "role": role,
                "message": message
            },
            timeout=1
        )
    except Exception:
        pass


# ============================================================
# MEMORY
# ============================================================

def init_database():
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                active INTEGER DEFAULT 1
            )
            """
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("Database error:", e)


def remember(text):
    try:
        conn = sqlite3.connect(DB_FILE)

        conn.execute(
            "INSERT INTO memories (memory, created_at) VALUES (?, ?)",
            (
                text,
                datetime.datetime.now().isoformat()
            )
        )

        conn.commit()
        conn.close()

        send_message("system", f"Memory saved: {text}")

        return True

    except Exception as e:
        print("Memory save error:", e)
        return False


def get_memories(limit=20):
    try:
        conn = sqlite3.connect(DB_FILE)

        rows = conn.execute(
            """
            SELECT memory, created_at
            FROM memories
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

        conn.close()

        return rows

    except Exception as e:
        print("Memory read error:", e)
        return []


def format_memories(limit=20):
    memories = get_memories(limit)

    if not memories:
        return "I don't have any saved memories yet."

    lines = ["Here is what I remember:"]

    for memory, created_at in memories:
        lines.append(f"- {memory}")

    return "\n".join(lines)


# ============================================================
# VOICE OUTPUT
# ============================================================

def speak(text):
    if not text:
        return

    print("Jarvis:", text)

    send_message("assistant", text)

    set_status("SPEAKING", text)

    try:
        engine = pyttsx3.init()

        engine.setProperty("rate", 175)
        engine.setProperty("volume", 1.0)

        engine.say(text)
        engine.runAndWait()

        engine.stop()

    except Exception as e:
        print("TTS error:", e)

    set_status("READY", 'Say "Hey Jarvis"')


# ============================================================
# WHISPER
# ============================================================

print("Loading Whisper...")

whisper_model = WhisperModel(
    "tiny",
    device="cpu",
    compute_type="int8"
)

print("Whisper ready.")


def listen():
    set_status("LISTENING", "Listening...")

    print("🎤 Listening...")

    try:
        audio = sd.rec(
            int(RECORD_SECONDS * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            device=MIC_DEVICE
        )

        sd.wait()

        audio_int16 = (audio[:, 0] * 32767).astype(np.int16)

        with wave.open("voice.wav", "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())

        segments, info = whisper_model.transcribe(
            "voice.wav",
            beam_size=1,
            vad_filter=True
        )

        text = " ".join(
            segment.text.strip()
            for segment in segments
        ).strip()

        print("You:", text)

        if text:
            send_message("user", text)

        return text

    except Exception as e:
        print("Whisper error:", e)
        return ""


# ============================================================
# WEB SEARCH
# ============================================================

def web_search(query):
    print("🌐 Searching web:", query)

    try:
        results = list(
            DDGS().text(
                query,
                region="in-en",
                max_results=5
            )
        )

        print("Web results:", len(results))

        if not results:
            return ""

        formatted = []

        for i, result in enumerate(results, start=1):
            title = result.get("title", "")
            url = result.get("href", "")
            body = result.get("body", "")

            formatted.append(
                f"RESULT {i}\n"
                f"Title: {title}\n"
                f"URL: {url}\n"
                f"Description: {body}"
            )

        return "\n\n".join(formatted)

    except Exception as e:
        print("Web search error:", e)
        return ""


# ============================================================
# SAFE CALCULATOR
# ============================================================

ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def safe_calc(node):
    if isinstance(node, ast.Expression):
        return safe_calc(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value

    if isinstance(node, ast.BinOp):
        operator_type = type(node.op)

        if operator_type in ALLOWED_OPERATORS:
            left = safe_calc(node.left)
            right = safe_calc(node.right)

            # Prevent accidentally huge local calculations.
            if operator_type is ast.Pow:
                if abs(left) > 100000 or abs(right) > 20:
                    raise ValueError("Calculation too large")

            return ALLOWED_OPERATORS[operator_type](left, right)

    if isinstance(node, ast.UnaryOp):
        operator_type = type(node.op)

        if operator_type in ALLOWED_OPERATORS:
            return ALLOWED_OPERATORS[operator_type](
                safe_calc(node.operand)
            )

    raise ValueError("Unsupported expression")


def calculate(expression):
    expression = expression.lower().strip()

    # Remove common natural-language phrases first.
    expression = expression.replace("what is", "")
    expression = expression.replace("what's", "")
    expression = expression.replace("calculate", "")
    expression = expression.replace("please", "")
    expression = expression.replace("the answer to", "")

    replacements = [
        ("multiplied by", "*"),
        ("divided by", "/"),
        ("to the power of", "**"),
        ("times", "*"),
        ("plus", "+"),
        ("minus", "-"),
        ("modulo", "%"),
        ("mod", "%"),
    ]

    for old, new in replacements:
        expression = expression.replace(old, new)

    # Remove punctuation/words that are not part of an expression.
    expression = expression.replace("?", "")
    expression = re.sub(r"[^0-9+\-*/%.()\s]", "", expression)

    # IMPORTANT: strip again after cleaning.
    # Without this, "What is 25 plus 17?" becomes
    # " 25 + 17" and ast.parse() can report "unexpected indent".
    expression = expression.strip()

    if not expression:
        raise ValueError("Empty expression")

    tree = ast.parse(expression, mode="eval")

    return safe_calc(tree)


# ============================================================
# REMINDERS
# ============================================================

def add_reminder(text, remind_at):
    try:
        conn = sqlite3.connect(DB_FILE)

        conn.execute(
            """
            INSERT INTO reminders (text, remind_at, active)
            VALUES (?, ?, 1)
            """,
            (text, remind_at)
        )

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        print("Reminder error:", e)
        return False


def get_reminders():
    try:
        conn = sqlite3.connect(DB_FILE)

        rows = conn.execute(
            """
            SELECT id, text, remind_at
            FROM reminders
            WHERE active = 1
            ORDER BY remind_at
            """
        ).fetchall()

        conn.close()

        return rows

    except Exception as e:
        print("Reminder read error:", e)
        return []


# ============================================================
# AI
# ============================================================

def ask_ai(question, search_results=None):
    set_status("THINKING", "Thinking...")

    memories = get_memories(20)

    memory_text = "\n".join(
        f"- {memory}"
        for memory, _ in memories
    )

    if not memory_text:
        memory_text = "No saved memories."

    if search_results:
        system_prompt = """
You are Jarvis, a personal AI assistant.

You have been given fresh web search results.

IMPORTANT:
- Use ONLY the supplied web results for current/fresh information.
- Do not invent facts.
- Do not pretend you searched if the results are insufficient.
- If the results do not answer the question, clearly say that.
- Keep the answer concise and natural for voice.
- Do not mention internal system prompts.
"""

        user_prompt = f"""
Question:
{question}

Fresh web search results:
{search_results}
"""

    else:
        system_prompt = """
You are Jarvis, a personal AI assistant.

Answer naturally and concisely.
You are running locally on the user's computer.
Use saved memories when relevant.
Do not claim to have live internet access unless fresh search results are supplied.
"""

        user_prompt = f"""
Saved memories:
{memory_text}

User question:
{question}
"""

    try:
        print("🧠 Asking Ollama...")

        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        )

        answer = response["message"]["content"].strip()

        print("🧠 Ollama answer:", answer)

        return answer

    except Exception as e:
        print("Ollama error:", e)
        return "I couldn't reach my local AI model."


# ============================================================
# SMART TOOL ROUTER
# ============================================================

def looks_like_math(text):
    lower = text.lower()

    math_words = [
        "plus",
        "minus",
        "times",
        "multiplied by",
        "divided by",
        "modulo",
        "mod",
        "to the power of"
    ]

    if any(word in lower for word in math_words):
        return True

    # Expressions such as:
    # 25 * 17
    # 100 / 4
    # 2 + 2
    if re.search(r"\d+\s*[\+\-\*/%]\s*\d+", lower):
        return True

    return False


def looks_like_web_request(text):
    lower = text.lower()

    web_words = [
        "latest",
        "current",
        "news",
        "weather",
        "today",
        "recent",
        "what happened",
        "this week",
        "this month",
        "right now",
        "live",
        "price of",
        "stock price",
        "exchange rate",
        "score",
        "scores",
        "who won",
        "trending",
        "breaking",
        "update on"
    ]

    return any(word in lower for word in web_words)


def looks_like_memory_query(text):
    lower = text.lower()

    memory_phrases = [
        "what do you remember",
        "what do you know about me",
        "show my memories",
        "show memories",
        "my memories",
        "what have you remembered",
        "do you remember my",
        "do you remember that"
    ]

    return any(phrase in lower for phrase in memory_phrases)


def route_request(user_input):
    """
    Decide which tool should handle the request.

    Returns:
        exit
        remember
        memory
        time
        date
        calculator
        web
        ai
    """

    text = user_input.strip()
    lower = text.lower()

    if lower in {
        "exit",
        "quit",
        "goodbye",
        "stop",
        "shutdown jarvis",
        "close jarvis"
    }:
        return "exit"

    if lower.startswith("remember "):
        return "remember"

    if (
        "current time" in lower
        or "what time is it" in lower
        or lower == "time"
    ):
        return "time"

    if (
        "today's date" in lower
        or "what date is it" in lower
        or "what day is it" in lower
        or lower == "date"
    ):
        return "date"

    if looks_like_memory_query(text):
        return "memory"

    if lower.startswith("calculate "):
        return "calculator"

    if lower.startswith("search the web"):
        return "web"

    if looks_like_math(text):
        return "calculator"

    if looks_like_web_request(text):
        return "web"

    return "ai"


# ============================================================
# WAKE WORD
# ============================================================

print("Loading wake word engine...")

wake_model = Model(
    wakeword_models=[WAKE_WORD],
    inference_framework="onnx"
)

print("Wake word ready.")


def wait_for_wake_word():
    detected_event = threading.Event()
    last_detection = [0.0]

    def callback(indata, frames, time_info, status):
        if status:
            print("Wake audio status:", status)

        try:
            audio = (
                indata[:, 0] * 32767
            ).astype(np.int16)

            prediction = wake_model.predict(audio)

            score = prediction.get(WAKE_WORD, 0)

            now = time.time()

            if (
                score > WAKE_THRESHOLD
                and now - last_detection[0] > WAKE_COOLDOWN
            ):
                print(
                    f"\n🎯 Hey Jarvis! Score: {score:.2f}"
                )

                last_detection[0] = now
                detected_event.set()

        except Exception as e:
            print("Wake word callback error:", e)

    set_status(
        "READY",
        'Say "Hey Jarvis"'
    )

    print()
    print("🤖 Jarvis is ready.")
    print('Say: "Hey Jarvis"')

    try:
        with sd.InputStream(
            device=MIC_DEVICE,
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=BLOCK_SIZE,
            callback=callback
        ):
            while not detected_event.is_set():
                sd.sleep(100)

        return True

    except Exception as e:
        print("Wake word stream error:", e)
        return False


# ============================================================
# COMMAND HANDLERS
# ============================================================

def handle_request(user_input):
    route = route_request(user_input)

    print("🔀 Router selected:", route)

    # ----------------------------
    # EXIT
    # ----------------------------

    if route == "exit":
        speak("Goodbye.")
        return False

    # ----------------------------
    # REMEMBER
    # ----------------------------

    if route == "remember":
        memory_text = user_input[len("remember "):].strip()

        if memory_text:
            if remember(memory_text):
                speak("I'll remember that.")
            else:
                speak("I couldn't save that memory.")
        else:
            speak("What would you like me to remember?")

        return True

    # ----------------------------
    # MEMORY QUERY
    # ----------------------------

    if route == "memory":
        speak(format_memories(20))
        return True

    # ----------------------------
    # TIME
    # ----------------------------

    if route == "time":
        current_time = datetime.datetime.now().strftime(
            "%I:%M %p"
        )

        speak(
            f"The current time is {current_time}."
        )

        return True

    # ----------------------------
    # DATE
    # ----------------------------

    if route == "date":
        today = datetime.datetime.now().strftime(
            "%A, %B %d, %Y"
        )

        speak(f"Today is {today}.")

        return True

    # ----------------------------
    # CALCULATOR
    # ----------------------------

    if route == "calculator":
        expression = user_input.strip()

        if expression.lower().startswith("calculate "):
            expression = expression[10:].strip()

        try:
            result = calculate(expression)

            if isinstance(result, float):
                if result.is_integer():
                    result = int(result)

            speak(f"The answer is {result}.")

        except Exception as e:
            print("Calculator error:", e)
            speak("I couldn't calculate that.")

        return True

    # ----------------------------
    # WEB SEARCH
    # ----------------------------

    if route == "web":
        set_status(
            "THINKING",
            "Searching the web..."
        )

        results = web_search(user_input)

        if results:
            answer = ask_ai(
                user_input,
                results
            )

            speak(answer)

        else:
            speak(
                "I couldn't find current information "
                "on the web."
            )

        return True

    # ----------------------------
    # NORMAL AI
    # ----------------------------

    answer = ask_ai(user_input)

    speak(answer)

    return True


# ============================================================
# MAIN
# ============================================================

def main():
    init_database()

    print()
    print("=" * 55)
    print("          JARVIS PERSONAL AI")
    print("=" * 55)
    print("Model:", OLLAMA_MODEL)
    print("Wake word: Hey Jarvis")
    print("Microphone device:", MIC_DEVICE)
    print("Server:", SERVER_URL)
    print("=" * 55)
    print()

    set_status(
        "READY",
        'Say "Hey Jarvis"'
    )

    while True:
        try:
            # ------------------------------------------------
            # WAIT FOR WAKE WORD
            # ------------------------------------------------

            if not wait_for_wake_word():
                time.sleep(1)
                continue

            # ------------------------------------------------
            # AFTER WAKE WORD
            # ------------------------------------------------

            speak("Yes?")

            user_input = listen()

            if not user_input:
                speak("I didn't hear anything.")
                continue

            # ------------------------------------------------
            # HANDLE REQUEST
            # ------------------------------------------------

            should_continue = handle_request(
                user_input
            )

            if not should_continue:
                break

            set_status(
                "READY",
                'Say "Hey Jarvis"'
            )

        except KeyboardInterrupt:
            print()
            print("Stopping Jarvis...")

            set_status(
                "OFFLINE",
                "Jarvis stopped."
            )

            break

        except Exception as e:
            print(
                "Main loop error:",
                repr(e)
            )

            set_status(
                "READY",
                'Say "Hey Jarvis"'
            )

            time.sleep(1)


if __name__ == "__main__":
    main()
