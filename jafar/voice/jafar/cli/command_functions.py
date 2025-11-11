import os
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from jafar.assistant_core.assistant_api import ask_assistant
from jafar.utils.file_utils import read_file, write_file, delete_file
from jafar.utils.code_utils import (
    extract_code_from_reply,
    extract_dbml_from_reply,
    extract_explanation_from_reply,
    extract_filename_from_reply,
)
from jafar.skills.project_manager.manager import load_config, project_list, project_run, project_status, project_update, explain_makefile, explain_readme
from jafar.integrations.github_api import (
    get_git_status,
    list_issues,
    list_pull_requests,
    list_my_tasks,
)
from rich.table import Table
from rich.markdown import Markdown
from rich.prompt import Prompt

console = Console()

def explain_code(file_path):
    content = read_file(file_path)
    if content is None:
        return
    response = ask_assistant(
        f"Объясни этот код:\n\n```python\n{content}\n```", task="explain_code"
    )
    explanation = extract_explanation_from_reply(response)
    console.print(Panel(explanation, title=f"📘 Объяснение {file_path}", style="cyan"))


def edit_code(file_path):
    content = read_file(file_path)
    if content is None:
        return
    console.print(
        Panel(
            "🤖 Что ты хочешь изменить в файле? (можно просто 'сделай лучше')",
            style="yellow",
        )
    )
    instruction = input("> ").strip() or "сделай лучше"
    response = ask_assistant(
        f"Измени этот код по инструкции '{instruction}':\n\n```python\n{content}\n```",
        task="edit_code",
    )
    new_code = extract_code_from_reply(response)
    explanation = extract_explanation_from_reply(response)
    console.print(
        Panel(explanation, title=f"📝 Предложенные изменения", style="green")
    )
    console.print(Syntax(new_code, "python", theme="monokai", line_numbers=True))
    if input("Применить изменения? (y/n) > ").lower() == "y":
        write_file(file_path, new_code)
        console.print(f"[green]✅ Файл {file_path} обновлён.[/green]")


def compare_code(file1_path, file2_path):
    content1 = read_file(file1_path)
    content2 = read_file(file2_path)
    if content1 is None or content2 is None:
        return
    response = ask_assistant(
        f"Сравни эти два файла:\n\n**{file1_path}**\n```python\n{content1}\n```\n\n**{file2_path}**\n```python\n{content2}\n```",
        task="compare_code",
    )
    explanation = extract_explanation_from_reply(response)
    console.print(
        Panel(explanation, title=f"🔄 Сравнение файлов", style="bright_magenta")
    )


def image_to_dbml(image_path):
    if not os.path.exists(image_path):
        console.print(f"[red]❌ Изображение не найдено: {image_path}[/red]")
        return
    response = ask_assistant(
        f"Конвертируй эту ERD-диаграмму в DBML-код.",
        task="image_to_dbml",
        image_path=image_path,
    )
    dbml_code = extract_dbml_from_reply(response)
    filename = extract_filename_from_reply(response) or "schema.dbml"
    console.print(Panel(dbml_code, title="💎 Сгенерированный DBML", style="blue"))
    if input("Сохранить в файл? (y/n) > ").lower() == "y":
        write_file(filename, dbml_code)
        console.print(f"[green]✅ DBML сохранён в {filename}.[/green]")

def project_summary_command(name):
    PROJECTS = load_config()
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
                file_path = os.path.join(os.path.expanduser("~/Projects"), repo, file_name)
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