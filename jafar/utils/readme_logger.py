import os
import json
from datetime import datetime
from pathlib import Path

# Директория для логов
MARKDOWN_DIR = Path.home() / ".jafar_cache" / "markdown"
MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)

# Файл по умолчанию
README_PATH = MARKDOWN_DIR / "jafar_activity_log.md"


def log_to_readme(
    action_type, description, result=None, notes=None, errors=None, stdout=None
):
    """
    Логирует действия в markdown-файл.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n---\n## 🗓️ {timestamp}\n"
    entry += f"### 🧩 Действие: {action_type}\n"
    entry += f"**Описание:** {description}\n"

    if result:
        if isinstance(result, dict):
            result_str = json.dumps(result, indent=2, ensure_ascii=False)
        else:
            result_str = str(result)
        entry += f"\n#### ✅ Результат\n```\n{result_str.strip()}\n```\n"
    if stdout:
        stdout_str = str(stdout)
        entry += f"\n#### 📤 Вывод\n```\n{stdout_str.strip()}\n```\n"
    if notes:
        notes_str = str(notes)
        entry += f"\n#### 📘 Заметки\n{notes_str.strip()}\n"
    if errors:
        errors_str = str(errors)
        entry += f"\n#### ❌ Ошибки\n```\n{errors_str.strip()}\n```\n"

    with open(README_PATH, "a", encoding="utf-8") as f:
        f.write(entry)

    return entry  # можно возвращать для логов или повторного вывода
