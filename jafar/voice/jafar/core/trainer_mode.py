import os
import subprocess
import socket

PROJECT_ROOT = "jafar_v2"
VENV_PATH = ".venv/bin/activate"
CHECK_PROCESSES = ["evolution", "ai_watcher"]


def check_current_directory():
    cwd = os.getcwd()
    if PROJECT_ROOT not in os.path.basename(cwd):
        print(f"❌ Вы не в корне проекта ({PROJECT_ROOT}).")
        print(f"💡 Перейдите в: cd ~/Projects/{PROJECT_ROOT}")
        return False
    print(f"✅ Директория проекта: {cwd}")
    return True

def check_virtual_env():
    if os.environ.get("VIRTUAL_ENV"):
        print("✅ Виртуальное окружение активировано.")
        return True
    print("❌ Виртуальное окружение не активировано.")
    print(f"💡 Активируйте: source {VENV_PATH}")
    return False

def check_internet():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        print("✅ Интернет-соединение есть.")
        return True
    except OSError:
        print("❌ Нет интернет-соединения.")
        return False

def check_process_running(name):
    try:
        ps = subprocess.run(["pgrep", "-f", name], capture_output=True)
        if ps.stdout:
            print(f"✅ {name} — запущен.")
            return True
        print(f"❌ {name} не запущен.")
        print(f"💡 Запустите: python3 jafar/assistant_core/{name}.py")
        return False
    except Exception as e:
        print(f"Ошибка при проверке {name}: {e}")
        return False

def run_trainer_mode():
    print("\n🎮 Jafar Trainer Mode — проверка окружения:\n")
    env_ok = check_current_directory()
    venv_ok = check_virtual_env()
    net_ok = check_internet()
    procs_ok = all(check_process_running(p) for p in CHECK_PROCESSES)
    if all([env_ok, venv_ok, net_ok, procs_ok]):
        print("\n🚀 Окружение готово к запуску задач!")
    else:
        print("\n⚠️ Обнаружены проблемы с окружением. Исправьте их перед продолжением.")

if __name__ == "__main__":
    run_trainer_mode()
