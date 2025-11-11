import json
from pathlib import Path
from datetime import datetime


from ..config.constants import JAFAR_MEMORY_DIR

EVOLUTION_LOG = JAFAR_MEMORY_DIR / "evolution_log.json"
ACTIONS_LOG = JAFAR_MEMORY_DIR / "code_log.json"


def _load_log(path):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _write_log(path, logs):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


def log_evolution_event(event, info=""):
    record = {"timestamp": datetime.now().isoformat(), "event": event, "info": info}
    logs = _load_log(EVOLUTION_LOG)
    logs.append(record)
    _write_log(EVOLUTION_LOG, logs)


def log_action(command, result=None):
    record = {
        "timestamp": datetime.now().isoformat(),
        "command": command,
        "result": result,
    }
    logs = _load_log(ACTIONS_LOG)
    logs.append(record)
    _write_log(ACTIONS_LOG, logs)


def log_step(description, extra=None):
    log_evolution_event("evolution_step", f"{description} | {extra if extra else ''}")


def show_evolution_welcome():
    print(
        """
╔════════════════════════════════════╗
║   🤖 Jafar перешёл в режим        ║
║   ОБУЧЕНИЯ!                       ║
║   Всё, что ты делаешь, будет      ║
║   записано и поможет ассистенту   ║
║   стать умнее.                    ║
╚════════════════════════════════════╝
        """
    )


def start_learning():
    log_evolution_event("start_learning", "Инициализация режима обучения Jafar")
    show_evolution_welcome()


def reset_evolution_history():
    EVOLUTION_LOG.write_text("[]", encoding="utf-8")
    ACTIONS_LOG.write_text("[]", encoding="utf-8")
    print("🧹 История эволюции и команд очищена!")


def print_evolution_stats():
    logs = _load_log(EVOLUTION_LOG)
    actions = _load_log(ACTIONS_LOG)
    print(
        f"📊 Всего шагов эволюции: {len([x for x in logs if x.get('event') == 'evolution_step'])}"
    )
    print(f"📊 Всего команд: {len(actions)}")
    if logs:
        print(f"⏱ Первый шаг: {logs[0]['timestamp']}")
        print(f"⏱ Последний шаг: {logs[-1]['timestamp']}")


def tail_log(path, n=10):
    logs = _load_log(path)
    for record in logs[-n:]:
        print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import sys

    # Простая CLI-обёртка для работы с evolution
    if len(sys.argv) < 2:
        print("Использование: python evolution.py [start|reset|stats|tail|logstep ...]")
    elif sys.argv[1] == "start":
        start_learning()
    elif sys.argv[1] == "reset":
        reset_evolution_history()
    elif sys.argv[1] == "stats":
        print_evolution_stats()
    elif sys.argv[1] == "tail":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        tail_log(EVOLUTION_LOG, n)
    elif sys.argv[1] == "logstep":
        description = (
            " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Шаг без описания"
        )
        log_step(description)
        print(f"✅ Зафиксировано: {description}")
    else:
        print("Неизвестная команда для evolution.py")
