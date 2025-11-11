import os
from config.constants import JAFAR_THREAD_FILE
from assistant_core.sqlite_manager import save_thread

"""
memory_manager.py — управление сохранением и получением thread_id
"""

# Инициализируем БД при первом импорте
# (sqlite_manager.init_db() уже вызывается автоматически)


def get_thread_id(client) -> str:
    """
    Возвращает существующий или создаёт новый thread_id для асинха,
    сохраняет его в SQLite и на диске.
    """
    # Проверяем мок-режим в assistant_api
    # Получаем путь к файлу JAFAR_THREAD_FILE
    if JAFAR_THREAD_FILE.exists():
        tid = JAFAR_THREAD_FILE.read_text().strip()
        save_thread(tid)
        return tid

    # Если нет файла, создаём новый тред через API-клиент
    thread = client.beta.threads.create()
    os.makedirs(os.path.dirname(JAFAR_THREAD_FILE), exist_ok=True)
    with open(JAFAR_THREAD_FILE, "w") as f:
        f.write(thread.id)
    save_thread(thread.id)
    return thread.id
