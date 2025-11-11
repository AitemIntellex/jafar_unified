from pathlib import Path
import sqlite3
from datetime import datetime

"""
sqlite_manager.py — работа с локальной SQLite-базой для хранения thread и логов команд
"""

DB_PATH = Path.home() / ".jafar" / "memory.sqlite"


def _connect():
    """Создаёт каталог и подключается к базе"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    return conn


def init_db():
    """Инициализация таблиц при первом импорте"""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS thread (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS command_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            command TEXT,
            explanation TEXT,
            note TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS skill (
            name TEXT PRIMARY KEY,
            description TEXT,
            enabled INTEGER DEFAULT 1
        );
    """)
    conn.commit()
    conn.close()


def save_thread(thread_id: str):
    """Сохраняет или обновляет запись о thread"""
    conn = _connect()
    conn.execute(
        "INSERT OR IGNORE INTO thread(id) VALUES (?)",
        (thread_id,)
    )
    conn.commit()
    conn.close()


def log_command(command: str, explanation: str | None, note: str | None):
    """Логирует выполненную AI-команду или shell-запрос"""
    conn = _connect()
    conn.execute(
        "INSERT INTO command_log(command, explanation, note) VALUES (?,?,?)",
        (command, explanation or "", note or "")
    )
    conn.commit()
    conn.close()

# автоинициализация при импорте
init_db()
