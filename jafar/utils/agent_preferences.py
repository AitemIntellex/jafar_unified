import json
from jafar.config.constants import JAFAR_AGENT_PREFERENCES_FILE

def save_agent_preferences(preferences: dict):
    """Сохраняет предпочтения агента в JSON-файл."""
    JAFAR_AGENT_PREFERENCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(JAFAR_AGENT_PREFERENCES_FILE, 'w', encoding='utf-8') as f:
        json.dump(preferences, f, ensure_ascii=False, indent=4)

def load_agent_preferences() -> dict:
    """Загружает предпочтения агента из JSON-файла. Возвращает пустой словарь, если файл не найден."""
    if JAFAR_AGENT_PREFERENCES_FILE.exists():
        with open(JAFAR_AGENT_PREFERENCES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def get_default_agent_preferences() -> dict:
    """Возвращает словарь с предпочтениями агента по умолчанию."""
    return {
        "role": "Ты являешься интеллектуальным интерпретатором и исполнителем команд для Jafar CLI.",
        "interaction_style": "Пользователь предпочитает использовать максимально естественный человеческий язык для формулирования задач, без необходимости знать конкретные команды Jafar CLI.",
        "primary_tool": "Для выполнения задач пользователя всегда используй Jafar agent-mode, чтобы преобразовывать запросы на естественном языке в команды Jafar CLI.",
        "response_style": "Отвечай кратко и по существу, предоставляя только необходимую информацию.",
        "jafar_project_location": "/home/jafar/Projects/jafar/",
        "initial_setup_done": True # Флаг, чтобы знать, что начальная настройка выполнена
    }
