from pathlib import Path

JAFAR_MEMORY_DIR = Path(__file__).parent.parent.parent / "memory"
JAFAR_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
JAFAR_THREAD_FILE = JAFAR_MEMORY_DIR / "thread_id.txt"
JAFAR_LOG_FILE = JAFAR_MEMORY_DIR / "jafar.log"
JAFAR_ACTIVE_PROJECT_FILE = JAFAR_MEMORY_DIR / "active_project.txt"
JAFAR_AGENT_PREFERENCES_FILE = JAFAR_MEMORY_DIR / "agent_preferences.json"

EMOJI = {
    "run": "⚙️",
    "ai": "✨",
    "cmd": "⌨️",
    "start": "▶️",
    "warn": "⚠️",
    "ok": "✔️",
}
