import os
import sys

# ==========================================
# JARVIS CENTRAL PATH DICTIONARY
# ==========================================

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PATHS = {
    "BASE_DIR": BASE_DIR,
    "FRONTEND": os.path.join(BASE_DIR, "frontend.py"),
    "BACKGROUND": os.path.join(BASE_DIR, "background.py"),
    "SERVER": os.path.join(BASE_DIR, "server.py"),
    "DATABASE": os.path.join(BASE_DIR, "memory.db"),
    "VOICE_WAV": os.path.join(BASE_DIR, "voice.wav"),
    "VENV": os.path.join(BASE_DIR, "venv"),
    "PYTHON": os.path.join(BASE_DIR, "venv", "Scripts", "python.exe"),
    "PYTHONW": os.path.join(BASE_DIR, "venv", "Scripts", "pythonw.exe"),
    "SERVER_URL": "http://127.0.0.1:5000",
    "SERVER_HOST": "127.0.0.1",
    "SERVER_PORT": 5000,
}

def get_path(name):
    return PATHS[name]


if __name__ == "__main__":
    print("JARVIS PATHS")
    print("=" * 40)

    for name, path in PATHS.items():
        print(f"{name}: {path}")