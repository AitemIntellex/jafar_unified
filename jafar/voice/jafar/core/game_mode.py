import os
import json
from jafar.checkers.check_processes import check_process
from jafar.checkers.check_git import check_git_status
from jafar.checkers.check_internet import check_internet_status
from jafar.renderers.render_rich import render_game_status

STATE_DIR = "state"
STATE_FILE = os.path.join(STATE_DIR, "game_state.json")

def get_game_state():
    """Формирует словарь текущего состояния системы для режима Game Mode."""
    return {
        "evolution": check_process("evolution"),
        "logger": check_process("logger"),
        "git": check_git_status(),
        "internet": check_internet_status(),
    }

def save_state(state: dict, path: str = STATE_FILE):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)

def run_game_mode():
    print("🧠 Jafar Game Mode: Initializing...\n")
    state = get_game_state()
    save_state(state)
    render_game_status(state)

if __name__ == "__main__":
    run_game_mode()
