import subprocess
import sys
from pathlib import Path

# 1. Импорт логирования и эволюции
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jafar_v2.jafar.cli.evolution import log_evolution_event, start_learning, log_action


def run_init_all_projects():
    """Запуск инициализации проектов"""
    print("🔄 Инициализация всех проектов...")
    try:
        subprocess.run(["python", "-m", "jafar.tools.init_all_projects"], check=True)
        log_evolution_event("init_projects", "Инициализация проектов завершена успешно")
        log_action("init_all_projects", "ok")
    except Exception as e:
        log_evolution_event("init_projects_error", str(e))
        log_action("init_all_projects", f"error: {e}")
        print(f"[Ошибка инициализации] {e}")


def run_tmux_window(session, name, command):
    subprocess.run(
        f"tmux new-window -t {session} -n {name} \"zsh -c '{command}; exec zsh'\"",
        shell=True,
    )
    run_tmux_window(session, "docker", "cd ~/Projects/tms_backend && docker compose up")


def start_tmux_services():
    session = "dev"
    # Создаём сессию tmux, если не существует
    subprocess.run(
        f"tmux has-session -t {session} || tmux new-session -d -s {session}", shell=True
    )
    # Запуск сервисов (по одному окну на каждый)
    run_tmux_window(
        session,
        "tms_backend",
        "cd ~/Projects/tms_backend && source .venv/bin/activate && python manage.py runserver 0.0.0.0:8000",
    )
    run_tmux_window(
        session,
        "tms_frontend",
        "cd ~/Projects/tms_frontend && npm run dev -- --port 3000",
    )
    run_tmux_window(
        session,
        "tradespace",
        "cd ~/Projects/TradeSpace-MVPPDO && source .venv/bin/activate && python manage.py runserver 0.0.0.0:8001",
    )
    run_tmux_window(
        session, "docker", "cd ~/Projects/TradeSpace-MVPPDO && docker compose up"
    )
    run_tmux_window(
        session,
        "jafar",
        "cd ~/Projects/jafar && source .venv/bin/activate && python -m jafar.cli.main",
    )
    print("🟢 Все сервисы запущены в tmux-сессии [dev].")
    log_evolution_event("services_started", "Все сервисы стартовали через tmux")
    log_action("start_tmux_services", "ok")
    # Вход в tmux-сессию
    subprocess.run(f"tmux attach -t {session}", shell=True)


def main():
    print("🧠 [Jafar] Центр управления стартует...\n")
    log_evolution_event("start_all", "Запуск центра управления и обучение")
    start_learning()
    run_init_all_projects()
    start_tmux_services()


if __name__ == "__main__":
    main()
