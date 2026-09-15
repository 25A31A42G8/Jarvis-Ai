from flask import Flask, jsonify, request
import sqlite3
import os

# SINGLE SERVER INSTANCE

import ctypes
from ctypes import wintypes
import sys

ERROR_ALREADY_EXISTS = 183

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

CreateMutexW = kernel32.CreateMutexW
CreateMutexW.argtypes = [
    wintypes.LPVOID,
    wintypes.BOOL,
    wintypes.LPCWSTR
]
CreateMutexW.restype = wintypes.HANDLE

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL

SERVER_MUTEX = CreateMutexW(
    None,
    False,
    "Local\\JARVIS_Flask_Server"
)

if not SERVER_MUTEX:
    raise ctypes.WinError(ctypes.get_last_error())

mutex_error = ctypes.get_last_error()

if mutex_error == ERROR_ALREADY_EXISTS:
    print("JARVIS server is already running.")
    CloseHandle(SERVER_MUTEX)
    sys.exit(0)

print("JARVIS server instance lock acquired.")

app = Flask(__name__)


# PORTABLE PATHS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "memory.db")

# Stop signal file
STOP_FILE = os.path.join(BASE_DIR, "jarvis_stop.flag")


# JARVIS STATE

jarvis_state = {
    "status": "READY",
    "message": 'Say "Hey Jarvis"',
    "messages": []
}


# DATABASE

def get_memories():

    conn = sqlite3.connect(DB_FILE)

    rows = conn.execute(
        """
        SELECT memory, created_at
        FROM memories
        ORDER BY id DESC
        LIMIT 50
        """
    ).fetchall()

    conn.close()

    return [
        {
            "memory": row[0],
            "created_at": row[1]
        }
        for row in rows
    ]


def get_reminders():

    conn = sqlite3.connect(DB_FILE)

    rows = conn.execute(
        """
        SELECT id, reminder, remind_at, completed
        FROM reminders
        WHERE completed = 0
        ORDER BY remind_at ASC
        """
    ).fetchall()

    conn.close()

    return [
        {
            "id": row[0],
