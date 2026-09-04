import sqlite3
from datetime import datetime

DB_FILE = "memory.db"


def setup_database():
    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reminder TEXT NOT NULL,
            remind_at TEXT NOT NULL,
            completed INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def add_reminder(reminder, remind_at):
    conn = sqlite3.connect(DB_FILE)

    conn.execute(
        """
        INSERT INTO reminders
        (reminder, remind_at)
        VALUES (?, ?)
        """,
        (reminder, remind_at)
    )

    conn.commit()
    conn.close()


def get_due_reminders():
    now = datetime.now().isoformat()

    conn = sqlite3.connect(DB_FILE)

    rows = conn.execute(
        """
        SELECT id, reminder
        FROM reminders
        WHERE remind_at <= ?
        AND completed = 0
        """,
        (now,)
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


if __name__ == "__main__":
    setup_database()
    print("Reminder database ready.")
