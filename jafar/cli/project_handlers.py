import os
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from jafar.cli.utils import get_projects_root
from ..utils.project_utils import get_project_info
import subprocess
from pathlib import Path
import re
import time
from jafar.utils.active_project import set_active_project, get_active_project


console = Console()
CONFIG_PATH = Path(__file__).parent.parent / "utils" / "projects_config.json"
with open(CONFIG_PATH, encoding="utf-8") as f:
    PROJECTS = json.load(f)


def project_navigator(args=""):
    root = get_projects_root()
    projects = [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]

    if not projects:
        console.print("[red]Проекты не найдены![/red]")
        return

    console.print(
        Panel(
            "\n".join(f"[cyan]{i+1}.[/cyan] {p}" for i, p in enumerate(projects)),
            title="📦 Проекты в ~/Projects",
            style="bold green",
        )
    )

    choice = Prompt.ask("Введите номер проекта для перехода", default="1")
    try:
        index = int(choice) - 1
        if 0 <= index < len(projects):
            selected = projects[index]
            path = os.path.join(root, selected)
            os.chdir(path)
            console.print(f"[bold green]✅ Перешли в:[/bold green] {path}")
        else:
            console.print("[red]❌ Неверный номер проекта[/red]")
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")


def projects_command(args):
    args = args.strip()

    if args in {"init-all", "init", "all"}:
        console.print(Panel("🚀 Запуск инициализации всех проектов...", style="cyan"))
        script_path = Path(__file__).parent.parent.parent / "init_all_projects.py"
        subprocess.run(["python3", str(script_path)])
        return

    if args.startswith("set-active "):
        project_name = args.split(" ", 1)[1].strip()
        root = get_projects_root()
        project_path = root / project_name
        if not project_path.is_dir():
            console.print(Panel(f"❌ Проект '{project_name}' не найден в {root}", style="red"))
            return
        set_active_project(project_name)
        console.print(Panel(f"✅ Активный проект установлен: [bold green]{project_name}[/bold green]", style="green"))
        return

    console.print(
        Panel(f"❓ Неизвестная команда: {args}", title="Projects CLI", style="red")
    )


def project_summary_command(name=None):
    if name is None:
        name = get_active_project()
        if name is None:
            console.print(Panel("❌ Активный проект не установлен. Используйте 'project set-active <имя_проекта>' или укажите имя проекта.", style="red"))
            return

    if name not in PROJECTS:
        console.print(Panel(f"❌ Проект {name} не найден в config", style="red"))
        return
    owner = PROJECTS[name]["owner"]
    repo = PROJECTS[name]["repo"]

    # --- Собери всю информацию ---
    git_status = get_git_status(name)  # (должен возвращать dict c branch, text)
    issues = list_issues(owner, repo)
    prs = list_pull_requests(owner, repo)
    tasks = list_my_tasks(owner, repo)
    # Коммиты можно собрать через subprocess или API
    last_commits = [
        {
            "short": "abc123",
            "msg": "Example commit message",
            "author": "Author",
            "ago": "2 hours ago",
        }
    ]  # <-- доработай под свои нужды

    show_project_summary(
        project_name=name,
        owner=owner,
        repo=repo,
        issues=issues,
        prs=prs,
        tasks=tasks,
        git_status=git_status or {},
        last_commits=last_commits,
        interactive=False
    )
    # time.sleep(5)


from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.markdown import Markdown
import os

console = Console()


def show_project_summary(
    project_name,
    owner,
    repo,
    issues,
    prs,
    tasks,
    git_status,
    last_commits,
    ai_note=None,
    interactive=True
):
    console.rule(f":rocket: [bold cyan]{project_name}[/bold cyan] — [dim]{owner}/{repo}[/dim]")

    # --- Compact Summary ---
    console.print(f"[bold]Branch:[/bold] [cyan]{git_status.get('branch', 'dev')}[/cyan] | "
                  f"[bold]Issues:[/bold] [yellow]{len(issues)}[/yellow] | "
                  f"[bold]PRs:[/bold] [green]{len(prs)}[/green] | "
                  f"[bold]Assigned:[/bold] [magenta]{len(tasks)}[/magenta]")

    # --- Git Status (short) ---
    if git_status.get("text"):
        console.print(f"[dim]Git Status:[/dim] {git_status['text'].splitlines()[0]}")

    # --- Last Commits (more concise) ---
    if last_commits:
        console.print("[bold]Last Commits:[/bold]")
        for c in last_commits: # Show all commits
            console.print(f"  [dim]{c['short']}[/dim] {c['msg']} — {c['author']}, {c['ago']}")

    # --- Issues (brief) ---
    if issues:
        console.print("[bold]Open Issues:[/bold]")
        for i in issues:
            console.print(f"  [yellow]#{i['number']}[/yellow] {i['title']}")

    # --- Pull Requests (brief) ---
    if prs:
        console.print("[bold]Open Pull Requests:[/bold]")
        for pr in prs:
            console.print(f"  [green]#{pr['number']}[/green] {pr['title']}")

    # --- AI Advice Panel (more direct) ---
    advice = ai_note or (
        "Сконцентрируйся на приоритетных задачах из Issues. "
        "Проверь новые PR для ревью! Посмотри последние коммиты и не забывай тестировать!"
    )
    console.print(Panel(f"🦉 [bold green]Совет Jafar:[/bold green] {advice}", style="bright_blue"))

    # --- Actions Menu ---
    if interactive:
        actions = {
            "1": "Показать описание задачи из Issues",
            "2": "Показать все Pull Requests",
            "3": "Попросить AI объяснить файл",
            "4": "Сгенерировать тест для задачи",
            "5": "Перейти в директорию проекта",
            "6": "Вернуться в CLI",
            "7": "Выйти",
        }
        console.rule("[bold cyan]Что делать дальше?[/bold cyan]")
        for k, v in actions.items():
            console.print(f"[cyan][{k}][/cyan] {v}")

        while True:
            choice = Prompt.ask(
                "Выбери действие", choices=list(actions.keys()), default="6"
            )
            from jafar.assistant_core.assistant_api import ask_assistant

            if choice == "1" and issues:
                issue_num = Prompt.ask(
                    "Номер задачи из Issues", default=str(issues[0]["number"])
                )
                issue = next(
                    (i for i in issues if str(i["number"]) == str(issue_num)), None
                )
                if issue:
                    msg = ask_assistant(
                        f"Объясни, что требуется сделать по этой задаче GitHub:\n\n{issue['title']}\n\n{issue.get('body','')}"
                    )
                    console.print(
                        Panel(
                            msg.get("explanation", str(msg)),
                            title=f"🦉 Issue #{issue_num} — AI пояснение",
                            style="green",
                        )
                    )
                else:
                    console.print(f"[red]Задача #{issue_num} не найдена.[/red]")

            elif choice == "2" and prs:
                for pr in prs:
                    console.print(f"[green]#{pr['number']}[/green] {pr['title']}")
            elif choice == "3":
                file_name = Prompt.ask("Файл для объяснения", default="README.md")
                file_path = os.path.join(get_projects_root(), repo, file_name)
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        file_content = f.read()
                    from jafar.assistant_core.assistant_api import ask_assistant

                    msg = ask_assistant(
                        f"Объясни содержимое файла {file_name}:\n\n{file_content[:3000]}"
                    )
                    console.print(
                        Panel(
                            msg.get("explanation", str(msg)),
                            title=f"📘 {file_name}",
                            style="cyan",
                        )
                    )
                else:
                    console.print(f"[red]Файл {file_name} не найден[/red]")

            elif choice == "4" and issues:
                issue_num = Prompt.ask(
                    "Номер задачи для теста", default=str(issues[0]["number"])
                )
                issue = next(
                    (i for i in issues if str(i["number"]) == str(issue_num)), None
                )
                if issue:
                    from jafar.assistant_core.assistant_api import ask_assistant

                    msg = ask_assistant(
                        f"Сгенерируй pytest к задаче:\n\n{issue['title']}\n\n{issue.get('body','')}"
                    )
                    console.print(
                        Panel(
                            msg.get("command", str(msg)),
                            title=f"🧪 Тест к Issue #{issue_num}",
                            style="magenta",
                        )
                    )
                else:
                    console.print(f"[red]Задача #{issue_num} не найдена.[/red]")

            elif choice == "5":
                path = os.path.join(os.path.expanduser("~/Projects"), repo)
                console.print(f"[green]cd {path}[/green]")
            elif choice == "6":
                console.print("[dim]Возвращаемся в обычный CLI...[/dim]")
                break
            elif choice == "7":
                console.print("[yellow]До встречи![/yellow]")
                exit(0)
            else:
                console.print("[red]Некорректный выбор![/red]")


# --- Пример вызова ---
if __name__ == "__main__":
    smart_project_dashboard(
        project_name="tms_backend",
        owner="Cargosys",
        repo="tms_backend",
        issues=[
            {"number": 40, "title": "Create database models from the database schemas"},
            {"number": 39, "title": "Configure the initial deployment for dev server"},
        ],
        prs=[
            {"number": 5, "title": "Refactor login logic"},
        ],
        tasks=[
            {"number": 38, "title": "Finish tests for dispatcher panel"},
        ],
        git_status={
            "branch": "dev",
            "text": "On branch dev\nYour branch is up to date with 'origin/dev'.\nnothing to commit, working tree clean",
        },
        last_commits=[
            {
                "short": "3241024",
                "msg": "Merge pull request #8 ...",
                "author": "O'ktamjon",
                "ago": "5 days ago",
            },
            {
                "short": "2ace688",
                "msg": "implemented storing payment cards ...",
                "author": "Uktamjon Komilov",
                "ago": "5 days ago",
            },
        ],
    )


def get_make_targets(makefile_path):
    # Простой парсер целей Makefile
    with open(makefile_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    targets = []
    for line in lines:
        if line.strip() and not line.startswith("\t") and ":" in line:
            tgt = line.split(":")[0].strip()
            if tgt.isidentifier():
                targets.append(tgt)
    return targets


def project_run(project_name):
    project_path = Path(f"/home/jafar/Projects/{project_name}")
    makefile_path = project_path / "Makefile"
    if not makefile_path.exists():
        console.print(f"[red]❌ В проекте {project_name} нет Makefile![/red]")
        return

    targets = get_make_targets(makefile_path)
    for target in ("run", "up", "start"):
        if target in targets:
            console.print(f"🚀 Запускаю {project_name} с помощью make {target}...")
            os.chdir(str(project_path))
            os.system(f"make {target}")
            return

    console.print(
        Panel(
            f"❌ Нет целей 'run', 'up' или 'start' в Makefile!\n"
            f"Доступные цели: {', '.join(targets)}",
            title="Makefile Error",
            style="red",
        )
    )
