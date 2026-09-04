import time
import sqlite3
import pyttsx3
from datetime import datetime

DB_FILE = r"C:\PersonalAI\memory.db"


def get_due_reminders():

    conn = sqlite3.connect(DB_FILE)

    rows = conn.execute(
        """
        SELECT id, reminder
        FROM reminders
        WHERE remind_at <= ?
        AND completed = 0
        """,
        (datetime.now().isoformat(),)
    ).fetchall()

    conn.close()

    return rows


def complete_reminder(reminder_id):

    conn = sqlite3.connect(DB_FILE)

    conn.execute(
        """
        UPDATE reminders
        SET completed = 1
        WHERE id = ?
        """,
        (reminder_id,)
    )

    conn.commit()
    conn.close()


def speak(text):

    print("REMINDER:", text)

    engine = pyttsx3.init()

    engine.say(text)
    engine.runAndWait()

    engine.stop()


print("Jarvis reminder service started.")

while True:

    reminders = get_due_reminders()

    for reminder_id, reminder in reminders:

        speak(
            f"Reminder: {reminder}"
        )

        complete_reminder(
            reminder_id
        )

    time.sleep(10)
