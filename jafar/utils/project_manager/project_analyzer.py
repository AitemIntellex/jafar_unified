import os
import json
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from jafar.assistant_core.assistant_api import ask_assistant

console = Console()

CACHE_DIR = Path.home() / ".jafar_cache" / "analyzed"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_file_mtime(file_path):
    if not os.path.exists(file_path):
        return None
    return os.path.getmtime(file_path)


def analyze_project(name, path, force=False, reset=False):
    project_path = Path(path).expanduser()
    if not project_path.exists():
        console.print(f"[red]❌ Путь проекта не найден: {project_path}[/red]")
        return

    makefile_path = project_path / "Makefile"
    readme_path = project_path / "README.md"
    cache_file = CACHE_DIR / f"{name}.json"

    if reset and cache_file.exists():
        cache_file.unlink()
        console.print(f"[yellow]♻️ Сброшен кэш анализа для {name}[/yellow]")

    cached = {}
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            cached = json.load(f)

    def should_update(file_path, key):
        mtime = get_file_mtime(file_path)
        if not mtime:
            return False
        return force or (key not in cached or cached[key]["mtime"] != mtime)

    updated = False

    # --- Makefile ---
    if should_update(makefile_path, "makefile"):
        content = (
            makefile_path.read_text(encoding="utf-8") if makefile_path.exists() else ""
        )
        prompt = (
            f"Ты — ассистент-программист. Объясни, как работает Makefile проекта '{name}'. "
            f"Укажи, какие команды доступны, что они делают и в каком порядке обычно вызываются. "
            f"Приведи объяснение в кратком и понятном виде. Вот содержимое Makefile:\n\n{content}"
        )
        console.print("[yellow]🧠 Обращаюсь к AI для анализа Makefile...[/yellow]")
        result = ask_assistant(prompt)
        explanation = result.get("explanation") or "(нет ответа)"
        cached["makefile"] = {
            "mtime": get_file_mtime(makefile_path),
            "explanation": explanation,
        }
        updated = True

    # --- README.md ---
    if should_update(readme_path, "readme"):
        content = (
            readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
        )
        prompt = (
            f"Прочитай README.md проекта '{name}' и объясни кратко:\n"
            f"- цель проекта,\n"
            f"- его возможности или модули,\n"
            f"- как он запускается (если указано).\n\n"
            f"Содержимое README:\n\n{content}"
        )
        console.print("[yellow]🧠 Обращаюсь к AI для анализа README.md...[/yellow]")
        result = ask_assistant(prompt)
        explanation = result.get("explanation") or "(нет ответа)"
        cached["readme"] = {
            "mtime": get_file_mtime(readme_path),
            "explanation": explanation,
        }
        updated = True

    if updated:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cached, f, indent=2)
        console.print(
            f"[green]✅ AI-анализ обновлён и сохранён для [bold]{name}[/bold][/green]"
        )
    else:
        console.print(
            f"[green]🔄 Нет изменений. Используем кэш для [bold]{name}[/bold][/green]"
        )

    # Вывод анализа

    console.print(
        Panel(
            cached.get("makefile", {}).get("explanation", "-"),
            title="🛠 Makefile",
            style="cyan",
        )
    )
    console.print(
        Panel(
            cached.get("readme", {}).get("explanation", "-"),
            title="📘 README.md",
            style="green",
        )
    )
