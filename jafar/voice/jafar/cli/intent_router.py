# jafar/cli/intent_router.py

import re
import os
import subprocess
import shutil  # 🔧 для создания резервных копий
from jafar.cli.code_handlers import code_command, edit_file_by_path
from jafar.cli.github_handlers import github_command
from jafar.cli.pytest_handlers import pytest_command
from jafar.cli.project_handlers import projects_command, project_summary_command
from jafar.cli.utils import find_file_in_projects
from rich.console import Console
from rich.panel import Panel

console = Console()

FILE_REGEX = re.compile(r"(?:/[^\s]+\.py)")  # путь к .py файлу


def detect_project_root(filepath: str) -> str:
    """
    По пути к файлу определяет корневую директорию проекта.
    """
    if "/tms_backend/" in filepath:
        return "/home/jafar/Projects/tms_backend"
    if "/jafar_v2/" in filepath:
        return "/home/jafar/Projects/jafar_v2"
    return os.path.dirname(filepath)


def detect_project_venv(filepath: str) -> str | None:
    if "/tms_backend/" in filepath:
        return "/home/jafar/Projects/tms_backend/.venv/bin/activate"
    if "/jafar_v2/" in filepath:
        return "/home/jafar/Projects/jafar_v2/.venv/bin/activate"
    return None


def route_by_intent(text: str) -> bool:
    """
    Высокоуровневая маршрутизация по смыслу команды.
    Возвращает True, если команда была перехвачена и выполнена.
    """
    text = text.strip()
    text_lower = text.lower()

    # 🧠 Попытка распознать путь к .py файлу
    path_match = FILE_REGEX.search(text)
    if path_match:
        filepath = path_match.group(0)
        if os.path.exists(filepath):
            if any(
                kw in text_lower
                for kw in [
                    "исправь",
                    "обнови",
                    "отредактируй",
                    "вызывает ошибку",
                    "сломался",
                ]
            ):
                edit_file_by_path(filepath)
                return True
            if "объясни" in text_lower or "что делает" in text_lower:
                code_command(f"explain {filepath}")
                return True
            if "сравни" in text_lower:
                other_matches = FILE_REGEX.findall(text)
                if len(other_matches) >= 2:
                    code_command(f"compare {other_matches[0]} {other_matches[1]}")
                    return True
        else:
            console.print(Panel(f"[red]Файл не найден: {filepath}[/red]"))
            return True  # всё равно считаем, что обработано

    # 🔍 Pytest (через subprocess с определением проекта и виртуального окружения)
    if "тест" in text_lower or "pytest" in text_lower:
        file_match = FILE_REGEX.search(text)
        target = file_match.group(0) if file_match else ""
        project_root = detect_project_root(target or os.getcwd())
        venv_activate = detect_project_venv(target or os.getcwd())

        try:
            console.print(
                Panel(f"🚀 Запуск pytest для {target or 'всего проекта'}", style="cyan")
            )
            if venv_activate and os.path.exists(venv_activate):
                subprocess.run(
                    (
                        f"bash -c 'source {venv_activate} && pytest {target}'"
                        if target
                        else f"bash -c 'source {venv_activate} && pytest'"
                    ),
                    shell=True,
                    cwd=project_root,
                )
            else:
                console.print(
                    Panel(
                        f"[yellow]⚠️ Виртуальное окружение не найдено. Убедитесь, что оно активировано и Django установлен.[/yellow]"
                    )
                )
                env = os.environ.copy()
                env["PYTHONPATH"] = project_root
                result = subprocess.run(
                    ["pytest", target] if target else ["pytest"],
                    cwd=project_root,
                    env=env,
                    capture_output=True,
                    text=True,
                )
                if "ModuleNotFoundError: No module named 'django'" in result.stderr:
                    console.print(
                        Panel(
                            "[red]❌ Ошибка: Django не найден. Возможно, виртуальное окружение не запущено.[/red]\n\n💡 [yellow]Совет:[/yellow] Используй команду `make shell` или активируй venv вручную.\n\n📂 Проект: [bold cyan]"
                            + project_root
                            + "[/bold cyan]",
                            title="Не хватает Django",
                            style="red",
                        )
                    )
                    console.print(result.stderr)
                else:
                    print(result.stdout)
        except Exception as e:
            console.print(Panel(f"[red]Ошибка запуска pytest: {e}[/red]"))
        return True

    # 🔁 GitHub
    if (
        "git" in text_lower
        or "github" in text_lower
        or "pull" in text_lower
        or "issue" in text_lower
    ):
        github_command(text)
        return True

    # 📦 Проекты
    if "обнови проект" in text_lower:
        projects_command("update")
        return True
    if "запусти проект" in text_lower:
        name = text.split("проект")[-1].strip()
        projects_command(f"run {name}")
        return True
    if "статус проекта" in text_lower:
        projects_command("status")
        return True
    if "сводка проекта" in text_lower:
        name = text.split("проекта")[-1].strip()
        project_summary_command(name)
        return True

    return False
