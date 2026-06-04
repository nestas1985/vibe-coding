import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).parent / "assistant.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS daily_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                morning_sent INTEGER DEFAULT 0,
                evening_reply TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                text TEXT NOT NULL,
                done INTEGER DEFAULT 0,
                source TEXT DEFAULT 'manual'
            );

            CREATE TABLE IF NOT EXISTS profile_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)


def save_evening_reply(text: str):
    today = date.today().isoformat()
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM daily_log WHERE date = ?", (today,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE daily_log SET evening_reply = ? WHERE date = ?",
                (text, today)
            )
        else:
            conn.execute(
                "INSERT INTO daily_log (date, evening_reply) VALUES (?, ?)",
                (today, text)
            )


def mark_morning_sent():
    today = date.today().isoformat()
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM daily_log WHERE date = ?", (today,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE daily_log SET morning_sent = 1 WHERE date = ?", (today,)
            )
        else:
            conn.execute(
                "INSERT INTO daily_log (date, morning_sent) VALUES (?, 1)", (today,)
            )


def get_week_logs():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT date, morning_sent, evening_reply FROM daily_log ORDER BY date DESC LIMIT 7"
        ).fetchall()
    return rows
