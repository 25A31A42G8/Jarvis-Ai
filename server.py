from flask import Flask, jsonify, request
import sqlite3
import os


app = Flask(__name__)


# =========================
# PORTABLE PATHS
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "memory.db")


# =========================
# JARVIS STATE
# =========================

jarvis_state = {
    "status": "READY",
    "message": 'Say "Hey Jarvis"',
    "messages": []
}


# =========================
# DATABASE
# =========================

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
            "reminder": row[1],
            "remind_at": row[2],
            "completed": row[3]
        }
        for row in rows
    ]


# =========================
# STATUS
# =========================

@app.route("/status", methods=["GET", "POST"])
def status():

    if request.method == "POST":

        data = request.get_json()

        if data:

            if "status" in data:
                jarvis_state["status"] = data["status"]

            if "message" in data:
                jarvis_state["message"] = data["message"]

    return jsonify(jarvis_state)


# =========================
# CHAT MESSAGES
# =========================

@app.route("/message", methods=["POST"])
def message():

    data = request.get_json()

    if data:

        jarvis_state["messages"].append({
            "speaker": data.get("speaker", "SYSTEM"),
            "text": data.get("text", "")
        })

    return jsonify({
        "success": True
    })


# =========================
# MEMORY API
# =========================

@app.route("/memories")
def memories():

    try:

        return jsonify({
            "success": True,
            "memories": get_memories()
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e),
            "memories": []
        })


# =========================
# REMINDERS API
# =========================

@app.route("/reminders")
def reminders():

    try:

        return jsonify({
            "success": True,
            "reminders": get_reminders()
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e),
            "reminders": []
        })


# =========================
# HEALTH
# =========================

@app.route("/health")
def health():

    return jsonify({
        "status": "online"
    })


# =========================
# START SERVER
# =========================

if __name__ == "__main__":

    print("Jarvis communication server started.")
    print("JARVIS folder:", BASE_DIR)
    print("Database:", DB_FILE)

    app.run(
        host="127.0.0.1",
        port=5000
    )