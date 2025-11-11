#!/usr/bin/env python3

import os
import shutil
import subprocess
import json
from pathlib import Path
from rich import print
from rich.table import Table
from rich.console import Console
from jafar.cli.evolution import log_evolution_event


console = Console()
PROJECTS_DIR = Path.home() / "Projects"
LOGFILE = PROJECTS_DIR / "init_log.txt"
LOGFILE.write_text("", encoding="utf-8")


def run_in_tmux(session, window, command, path):
    subprocess.run(["tmux", "new-session", "-d", "-s", session, "-n", window], cwd=path)
    subprocess.run(["tmux", "send-keys", "-t", f"{session}:{window}", command, "C-m"])


def detect_project_types(path: Path) -> list[str]:
    types = []
    if (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
        types.append("python")
    if (path / "pyproject.toml").exists() and "tool.poetry" in (
        path / "pyproject.toml"
    ).read_text(errors="ignore"):
        types.append("poetry")
    if (path / "package.json").exists():
        types.append("node")
    if (path / "Dockerfile").exists() or (path / "docker-compose.yml").exists():
        types.append("docker")
    if (path / "Makefile").exists():
        types.append("make")
    return types


def append_log(message: str):
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(f"{message}\n")


def setup_python_project(path):
    os.chdir(path)
    if (path / ".venv").exists():
        append_log(
            f"[SKIP] Python-проект {path.name}: виртуальное окружение уже существует."
        )
        return
    try:
        subprocess.run(["python3", "-m", "venv", ".venv"], check=True)
        subprocess.run(
            ["bash", "-c", "source .venv/bin/activate && pip install --upgrade pip"],
            check=True,
        )
        for req_file in path.glob("*require*.txt"):
            subprocess.run(
                f"source .venv/bin/activate && pip install -r {req_file.name}",
                shell=True,
                executable="/bin/bash",
                check=True,
            )
        vscode_dir = path / ".vscode"
        vscode_dir.mkdir(exist_ok=True)
        settings_path = vscode_dir / "settings.json"
        interpreter_path = str(path / ".venv" / "bin" / "python")
        settings_path.write_text(
            json.dumps({"python.pythonPath": interpreter_path}, indent=2)
        )
        append_log(f"[OK] Python-проект {path.name} успешно инициализирован.")
    except subprocess.CalledProcessError as e:
        append_log(f"[ERROR] Python-проект {path.name}: {str(e)}")


def setup_node_project(path):
    os.chdir(path)
    if not shutil.which("npm"):
        append_log(f"[SKIP] Node.js-проект {path.name}: npm не найден.")
        return
    try:
        subprocess.run(["npm", "install"], check=True)
        append_log(f"[OK] Node.js-проект {path.name} успешно установлен.")
    except subprocess.CalledProcessError as e:
        append_log(f"[ERROR] Node.js-проект {path.name}: {str(e)}")


def setup_docker_project(path):
    os.chdir(path)
    try:
        if (path / "docker-compose.yml").exists():
            subprocess.run(["docker-compose", "build"], check=True)
        elif (path / "Dockerfile").exists():
            subprocess.run(
                ["docker", "build", "-t", path.name.lower(), "."], check=True
            )
        append_log(f"[OK] Docker-проект {path.name} успешно собран.")
    except subprocess.CalledProcessError as e:
        append_log(f"[ERROR] Docker-проект {path.name}: {str(e)}")


def setup_make_project(path):
    os.chdir(path)
    try:
        subprocess.run(["make"], check=True)
        append_log(f"[OK] Make-проект {path.name} успешно выполнен.")
    except subprocess.CalledProcessError as e:
        append_log(f"[ERROR] Make-проект {path.name}: {str(e)}")


def main():
    log_evolution_event(
        "init_all_projects_start", "Автоматический старт инициализации всех проектов"
    )

    table = Table(title="📁 Автоматический обход проектов в ~/Projects")
    table.add_column("Проект", style="cyan")
    table.add_column("Типы")

    session_name = "jafar_projects"

    # Создаем новую сессию tmux (если нет)
    subprocess.run(["tmux", "new-session", "-d", "-s", session_name])

    for sub in PROJECTS_DIR.iterdir():
        if sub.is_dir():
            types = detect_project_types(sub)
            if not types:
                continue

            window_name = sub.name.replace(" ", "_")

            if "python" in types:
                setup_python_project(sub)
                run_in_tmux(
                    session_name,
                    window_name + "_py",
                    "source .venv/bin/activate && python manage.py runserver",
                    sub,
                )

            if "node" in types:
                setup_node_project(sub)
                run_in_tmux(session_name, window_name + "_node", "npm run dev", sub)

            if "docker" in types:
                setup_docker_project(sub)
                run_in_tmux(
                    session_name, window_name + "_docker", "docker-compose up", sub
                )

            if "make" in types:
                setup_make_project(sub)
                run_in_tmux(session_name, window_name + "_make", "make", sub)

            table.add_row(str(sub.name), ", ".join(types))

    console.print(table)
    console.print(f"\n📄 Лог инициализации: {LOGFILE}")
    log_evolution_event(
        "init_all_projects_end", "Автоматическая инициализация всех проектов завершена"
    )

    console.print(
        f"✅ Проекты запущены в tmux-сессии: [bold cyan]{session_name}[/bold cyan]"
    )
    console.print(
        f"🔍 Чтобы подключиться: [yellow]tmux attach -t {session_name}[/yellow]"
    )
