# jafar_v2/core/project_manager.py

import os
import json
import subprocess
from pathlib import Path
from rich.table import Table
from rich.console import Console
from datetime import datetime, timedelta
from jafar.assistant_core.assistant_api import ask_assistant


console = Console()
CONFIG_PATH = Path.home() / ".jafar" / "projects_config.json"

CACHE_DIR = Path.home() / ".jafar" / "project_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
console = Console()


def get_git_commit_hash(path):
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path)
            .decode()
            .strip()
        )
    except Exception:
        return None


def get_project_files_snapshot(path):
    files = ["Makefile", "README.md", "requirements.txt"]
    snapshot = {}
    for fname in files:
        f = Path(path) / fname
        if f.exists():
            stat = f.stat()
            snapshot[fname] = {
                "mtime": stat.st_mtime,
                "size": stat.st_size,
            }
    return snapshot


def load_cached_analysis(name):
    cache_file = CACHE_DIR / f"{name}.json"
    if not cache_file.exists():
        return None
    with open(cache_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cached_analysis(name, data):
    with open(CACHE_DIR / f"{name}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def is_cache_valid(cached, current_commit, file_snapshot):
    if not cached:
        return False
    if cached.get("last_commit") != current_commit:
        return False
    if cached.get("files") != file_snapshot:
        return False
    timestamp = datetime.fromisoformat(cached.get("last_updated"))
    return datetime.now() - timestamp < timedelta(hours=6)


###***********************###***********###***


def interactive_run():
    name = choose_project()
    if name:
        project_run(name)


def load_config():
    if not CONFIG_PATH.exists():
        console.print("[yellow]⚠️ Конфиг не найден, создаём из ~/Projects...[/yellow]")
        init_config_from_folders()

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def project_list():
    config = load_config()
    if not config:
        console.print("[red]Конфигурация пуста.[/red]")
        return
    table = Table(title="📂 Список проектов")
    table.add_column("Имя")
    table.add_column("Путь")
    for name, info in config.items():
        table.add_row(name, info["path"])
    console.print(table)


from prompt_toolkit.shortcuts import radiolist_dialog


def choose_project():
    config = load_config()
    if not config:
        return None
    options = [(k, f"{k} — {v['path']}") for k, v in config.items()]
    result = radiolist_dialog(
        title="Выбор проекта",
        text="Выберите проект:",
        values=options,
    ).run()
    return result


def project_update():
    config = load_config()
    for name, info in config.items():
        path = os.path.expanduser(info["path"])
        branch = info.get("branch")
        console.print(f"[cyan]📁 Обновляем {name}...[/cyan]")
        if not os.path.isdir(path):
            console.print(f"[red]Путь не найден: {path}[/red]")
            continue
        os.chdir(path)
        try:
            subprocess.run(["git", "checkout", branch], check=True)
            subprocess.run(["git", "pull", "origin", branch], check=True)
            console.print(f"[green]✅ {name} обновлён.[/green]\n")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]❌ Ошибка обновления {name}: {e}[/red]")


def get_make_targets(makefile_path):
    targets = []
    with open(makefile_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() and not line.startswith("\t") and ":" in line:
                target = line.split(":")[0].strip()
                # Фильтруем только обычные имена целей
                if target.isidentifier():
                    targets.append(target)
    return targets


import subprocess


def project_run(name):
    config = load_config()
    if name not in config:
        console.print(f"[red]Проект {name} не найден в конфиге.[/red]")
        return
    path = os.path.expanduser(config[name]["path"])
    if not os.path.isdir(path):
        console.print(f"[red]Путь не существует: {path}[/red]")
        return
    makefile_path = os.path.join(path, "Makefile")
    if not os.path.exists(makefile_path):
        console.print(f"[red]Makefile не найден в {path}[/red]")
        return
    targets = get_make_targets(makefile_path)
    for goal in ("run", "up", "start"):
        if goal in targets:
            console.print(f"🚀 Запускаем [cyan]{name}[/cyan] с помощью make {goal}...")
            os.chdir(path)
            subprocess.run(["make", goal])
            return
    console.print(
        Panel(
            f"❌ В Makefile нет целей 'run', 'up' или 'start'!\n"
            f"Доступные цели: {', '.join(targets)}",
            title="Makefile Error",
            style="red",
        )
    )


def project_status():
    config = load_config()
    table = Table(title="📊 Статус проектов")
    table.add_column("Проект")
    table.add_column("Ветка")
    table.add_column("Makefile")
    table.add_column("README")

    for name, info in config.items():
        path = Path(os.path.expanduser(info["path"]))
        branch = info.get("branch", "-")
        makefile = "✅" if (path / "Makefile").exists() else "❌"
        readme = "📄" if (path / "README.md").exists() else "-"
        table.add_row(name, branch, makefile, readme)

    console.print(table)


def explain_makefile(name):
    config = load_config()
    if name not in config:
        console.print(f"[red]Проект {name} не найден.[/red]")
        return
    path = Path(os.path.expanduser(config[name]["path"]))
    makefile_path = path / "Makefile"
    if not makefile_path.exists():
        console.print(f"[red]Makefile не найден в {path}[/red]")
        return

    with open(makefile_path, "r", encoding="utf-8") as f:
        content = f.read()
    result = ask_assistant(f"Объясни, что делает этот Makefile:\n\n{content}")
    explanation = result.get("response") or result.get("text") or "(Пустой ответ)"
    console.print(f"\n[bold cyan]AI объяснение:[/bold cyan]\n{explanation}")


def init_config_from_folders():
    default_path = Path("~/Projects").expanduser()
    projects = [p for p in default_path.iterdir() if p.is_dir()]
    data = {}
    for p in projects:
        data[p.name] = {"path": str(p), "branch": "dev"}
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    console.print(
        f"[green]Сконфигурировано {len(data)} проектов в {CONFIG_PATH}[/green]"
    )


def explain_readme(name):
    config = load_config()
    if name not in config:
        console.print(f"[red]Проект {name} не найден.[/red]")
        return
    path = Path(os.path.expanduser(config[name]["path"]))
    readme_path = path / "README.md"
    if not readme_path.exists():
        console.print(f"[red]README.md не найден.[/red]")
        return
    text = readme_path.read_text(encoding="utf-8")
    result = ask_assistant(f"Объясни этот README:\n\n{text}")
    explanation = result.get("response") or result.get("text") or "(нет ответа)"
    console.print(f"\n[bold green]📘 AI объяснение README:[/bold green]\n{explanation}")
