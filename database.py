import sqlite3
import os

DB_NAME = os.path.join(os.path.dirname(__file__), "schedules.db")


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT NOT NULL,
            target_ids TEXT NOT NULL,
            message TEXT NOT NULL,
            days TEXT NOT NULL,
            time TEXT NOT NULL,
            last_sent TEXT
        )
    """)

    conn.commit()
    conn.close()

def get_schedule_by_id(schedule_id: int):
    conn = sqlite3.connect("schedules.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, target, target_ids, message, days, time FROM schedules WHERE id = ?",
        (schedule_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row

def update_schedule(schedule_id: int, message: str, days: str, time: str):
    conn = sqlite3.connect("schedules.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE schedules
        SET message = ?, days = ?, time = ?
        WHERE id = ?
        """,
        (message, days, time, schedule_id)
    )
    conn.commit()
    conn.close()


def save_schedule(target, target_ids, message, days, time):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO schedules (target, target_ids, message, days, time)
        VALUES (?, ?, ?, ?, ?)
        """,
        (target, ",".join(map(str, target_ids)), message, ",".join(days), time)
    )

    conn.commit()
    conn.close()


def get_all_schedules():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, target, target_ids, message, days, time, last_sent
        FROM schedules
    """)
    rows = cursor.fetchall()

    conn.close()
    return rows


def update_last_sent(schedule_id, date_str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE schedules SET last_sent = ? WHERE id = ?",
        (date_str, schedule_id)
    )

    conn.commit()
    conn.close()

def get_schedules_by_owner():
    # For now: return all schedules
    # (Later we can filter per-user)
    return get_all_schedules()

def delete_schedule(schedule_id: int):
    conn = sqlite3.connect("schedules.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()

def update_schedule_time(schedule_id: int, new_time: str):
    conn = sqlite3.connect("schedules.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE schedules SET time = ? WHERE id = ?",
        (new_time, schedule_id)
    )
    conn.commit()
    conn.close()


def update_schedule_days(schedule_id: int, new_days: str):
    conn = sqlite3.connect("schedules.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE schedules SET days = ? WHERE id = ?",
        (new_days, schedule_id)
    )
    conn.commit()
    conn.close()

