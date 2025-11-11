from pathlib import Path
from jafar.config.constants import JAFAR_ACTIVE_PROJECT_FILE

def set_active_project(project_name: str):
    """Сохраняет имя активного проекта."""
    JAFAR_ACTIVE_PROJECT_FILE.write_text(project_name.strip())

def get_active_project() -> str | None:
    """Возвращает имя активного проекта или None, если не установлен."""
    if JAFAR_ACTIVE_PROJECT_FILE.exists():
        return JAFAR_ACTIVE_PROJECT_FILE.read_text().strip()
    return None

def clear_active_project():
    """Очищает активный проект."""
    if JAFAR_ACTIVE_PROJECT_FILE.exists():
        JAFAR_ACTIVE_PROJECT_FILE.unlink()
