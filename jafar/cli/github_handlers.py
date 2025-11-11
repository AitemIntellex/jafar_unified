from prompt_toolkit import PromptSession
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import os
import requests
import re
from jafar.utils.readme_logger import log_to_readme
import subprocess
from pathlib import Path
from rich.prompt import Prompt

from jafar.utils.project_manager.manager import load_config
from jafar.utils.github_api import list_issues
from jafar.utils.init_all_projects import append_log
from jafar.utils.assistant_api import ask_assistant

console = Console()
GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}


def github_command(args):
    args = args.strip()

    if not args or args in {"help", "-h", "--help"}:
        return show_github_game_style()

    if args.startswith("clone "):
        repo_url = args.split(" ", 1)[1].strip()
        return github_clone(repo_url)

    if args == "status":
        return github_status()

    if args.startswith("branch"):
        return github_branch(args)

    if args == "pull":
        return github_pull()

    if args == "push":
        return github_push()

    if args.startswith("commit"):
        return github_commit(args)

    if args == "log":
        return github_log()

    if args == "issue list":
        return github_issue_list()

    if args.startswith("issue list "):
        project_name = args.split(" ", 2)[2]
        return github_issue_list(project_name)

    console.print(
        Panel(
            f"⮞ Неизвестная или не реализованная подкоманда: {args}",
            style="bold yellow",
        )
    )


def show_github_game_style():
    md = Markdown(
        """
## 🎮 GitHub Game Mode Activated

### Ты можешь выполнить:

- `github clone <url>` — клонировать проект
- `github status` — статус изменений
- `github branch` — список/создание веток
- `github pull` — подтянуть изменения
- `github push` — отправить изменения
- `github commit "<сообщение>"` — коммитить изменения

---

### Хочешь больше?

- `github issue new "..."` — создать issue
- `github pr ...` — создать или смёржить PR
- `github log` — лог коммитов
- `github tag v1.0` — теги релизов

---

**Попробуй:** `github status`
"""
    )
    console.print(Panel(md, title="📦 GitHub CLI"))


def github_clone(repo_url):
    os.system(f"git clone {repo_url}")
    console.print(f"[bold green]Репозиторий клонирован:[/bold green] {repo_url}")
    log_to_readme("github", "Клонирование репозитория", repo_url)


def github_status():
    os.system("git status")
    log_to_readme("github", "Проверка git status")


def github_branch(args):
    if args.strip() == "branch":
        os.system("git branch")
        log_to_readme("github", "Просмотр локальных веток")
    else:
        branch_name = args.split(" ", 1)[1].strip()
        os.system(f"git checkout -b {branch_name}")
        console.print(
            f"[bold green]Ветка создана и переключено:[/bold green] {branch_name}"
        )
        log_to_readme("github", "Создание новой ветки", branch_name)


def github_pull():
    os.system("git pull")
    console.print(
        "[bold green]Изменения подтянуты из удалённого репозитория.[/bold green]"
    )
    log_to_readme("github", "Выполнен git pull")


def github_push():
    os.system("git push")
    console.print(
        "[bold green]Изменения отправлены в удалённый репозиторий.[/bold green]"
    )
    log_to_readme("github", "Выполнен git push")


def github_commit(args):
    match = re.match(r'commit\s+"(.+?)"', args)
    if not match:
        console.print('[red]❌ Укажи сообщение в кавычках: commit "текст"[/red]')
        return
    message = match.group(1)
    os.system("git add .")
    os.system(f'git commit -m "{message}"')
    console.print(f"[bold green]Коммит создан:[/bold green] {message}")
    log_to_readme("github", "Создан git commit", message)

def github_log():
    """Выводит лог коммитов для текущего проекта."""
    try:
        log = subprocess.check_output(["git", "log", "--oneline"], text=True)
        console.print(Panel(log.strip(), title="🕓 Последние коммиты", style="cyan"))
    except Exception as e:
        console.print(f"[red]Ошибка получения логов:[/red] {e}")

def github_issue_list(project_name=None):
    """Показывает список issues и pull requests для проекта."""
    if not project_name:
        project_name = Path.cwd().name
    
    project_path = Path.home() / "Projects" / project_name
    if not project_path.exists():
        console.print(Panel(f"❌ Проект '{project_name}' не найден.", style="red"))
        return

    show_github_issues_and_prs(str(project_path))





def log_git_status(path: Path):
    os.chdir(path)
    try:
        branch = (
            subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                stderr=subprocess.DEVNULL,
            )
            .decode("utf-8")
            .strip()
        )

        status = (
            subprocess.check_output(
                ["git", "status", "--short"],
                stderr=subprocess.DEVNULL,
            )
            .decode("utf-8")
            .strip()
        )

        append_log(f"[GIT] {path.name}: ветка {branch}")
        if status:
            append_log(f"[GIT] {path.name}: незакоммиченные изменения:\n{status}")
        else:
            append_log(f"[GIT] {path.name}: рабочая директория чиста ✅")
    except Exception as e:
        append_log(f"[GIT] {path.name}: git не инициализирован или ошибка: {e}")


PROJECTS_ROOT = Path.home() / "Projects"


def github_inspect(project_name: str):
    project_path = PROJECTS_ROOT / project_name
    if not project_path.exists():
        console.print(Panel(f"❌ Проект '{project_name}' не найден.", style="red"))
        return

    os.chdir(project_path)

    console.rule(f"[bold cyan]📦 GitHub Inspect: {project_name}[/bold cyan]")

    # Git Status
    console.print(Panel("🔍 [bold]Git Status:[/bold]", style="bold green"))
    os.system("git status")

    # Current Branch
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], text=True
        ).strip()
        console.print(f"[bold yellow]🌿 Текущая ветка:[/bold yellow] {branch}")
    except Exception as e:
        console.print(f"[red]Ошибка получения ветки:[/red] {e}")

    # Git Diff
    try:
        diff = subprocess.check_output(["git", "diff", "--stat"], text=True)
        console.print(
            Panel(diff or "Нет изменений", title="📊 Разница", style="magenta")
        )
    except Exception as e:
        console.print(f"[red]Ошибка получения diff:[/red] {e}")

    # Last commits
    try:
        log = subprocess.check_output(["git", "log", "-n", "5", "--oneline"], text=True)
        console.print(Panel(log.strip(), title="🕓 Последние коммиты", style="cyan"))
    except Exception as e:
        console.print(f"[red]Ошибка получения логов:[/red] {e}")

    # Git Remote
    try:
        remotes = subprocess.check_output(["git", "remote", "-v"], text=True)
        console.print(
            Panel(remotes.strip(), title="🔗 Удалённые репозитории", style="blue")
        )
    except Exception as e:
        console.print(f"[red]Ошибка получения удалённых репозиториев:[/red] {e}")

    # Pre-commit
    precommit = project_path / ".pre-commit-config.yaml"
    if precommit.exists():
        console.print("✅ [green]pre-commit найден.[/green] Попробуем запустить:")
        os.system("pre-commit run --all-files || echo ⚠️ Ошибки в hook'ах")
    else:
        console.print("[yellow]⚠️ pre-commit не найден в проекте.[/yellow]")

    # Готовность
    console.print(
        Panel("✅ [bold cyan]Инспекция завершена[/bold cyan]", style="bold green")
    )


def extract_repo_info(project_path: str):
    """Получаем owner и repo_name из git remote (поддерживает SSH и HTTPS)"""
    try:
        # Используем subprocess для большей надежности и флаг -C для смены директории
        command = ["git", "-C", project_path, "remote", "get-url", "origin"]
        output = subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL).strip()

        if not output:
            return None, None

        # Обработка SSH URL: git@github.com:owner/repo.git
        if output.startswith("git@"):
            path = output.split(":")[1]
            owner, repo = path.replace(".git", "").split("/")
            return owner, repo

        # Обработка HTTPS URL: https://github.com/owner/repo.git
        elif output.startswith("https://"):
            path = output.split("github.com/")[1]
            owner, repo = path.replace(".git", "").split("/")
            return owner, repo

        return None, None
    except (subprocess.CalledProcessError, IndexError, Exception):
        return None, None


def show_github_issues_and_prs(project_path: str):
    owner, repo = extract_repo_info(project_path)
    if not owner or not repo:
        console.print("[red]❌ Не удалось определить репозиторий GitHub.[/red]")
        return

    console.rule(f"[bold green]📬 Pull Requests & Issues: {repo}[/bold green]")

    # --- Issues
    r_issues = requests.get(
        f"{GITHUB_API}/repos/{owner}/{repo}/issues",
        headers=HEADERS,
        params={"state": "open"},
    )
    if r_issues.status_code == 200:
        issues = r_issues.json()
        table = Table(title="🐞 Open Issues")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="yellow")
        table.add_column("User", style="magenta")
        for i in issues:
            if "pull_request" in i:
                continue  # это не issue, а PR
            table.add_row(str(i["number"]), i["title"], i["user"]["login"])
        console.print(table)
    else:
        console.print(f"[red]❌ Ошибка получения issues: {r_issues.status_code}[/red]")

    # --- Pull Requests
    r_prs = requests.get(
        f"{GITHUB_API}/repos/{owner}/{repo}/pulls",
        headers=HEADERS,
        params={"state": "open"},
    )
    if r_prs.status_code == 200:
        prs = r_prs.json()
        table = Table(title="📦 Open Pull Requests")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="yellow")
        table.add_column("User", style="magenta")
        for pr in prs:
            table.add_row(str(pr["number"]), pr["title"], pr["user"]["login"])
        console.print(table)
    else:
        console.print(
            f"[red]❌ Ошибка получения pull requests: {r_prs.status_code}[/red]"
        )


def push_project(name):
    config = load_config()
    if name not in config:
        console.print(f"[red]Проект {name} не найден в конфиге.[/red]")
        return
    path = os.path.expanduser(config[name]["path"])
    if not os.path.isdir(path):
        console.print(f"[red]Путь не существует: {path}[/red]")
        return
    os.chdir(path)
    # Показываем git status для ясности
    subprocess.run(["git", "status"])
    # git add .
    subprocess.run(["git", "add", "."])
    # Запрашиваем коммит-месседж
    msg = input("Введите коммит-месседж: ").strip()
    if not msg:
        msg = "Рабочий коммит (by Jafar CLI)"
    subprocess.run(["git", "commit", "-m", msg])
    # git push
    subprocess.run(["git", "push"])
    console.print("[green]Все изменения отправлены в репозиторий![/green]")


from rich.prompt import Prompt, Confirm


def next_task(project_name, task_number=None):
    config = load_config()
    if project_name not in config:
        console.print(f"[red]Проект {project_name} не найден в конфиге.[/red]")
        return
    repo = config[project_name].get("repo", project_name)
    owner = config[project_name].get("owner", "?")
    issues = list_issues(owner, repo)
    if not issues:
        console.print("[green]Нет открытых задач! Всё, можно идти пить чай.[/green]")
        return

    table = Table("№", "Title")
    for i in issues:
        table.add_row(str(i["number"]), i["title"])
    console.print(Panel(table, title=f"📝 Issues для {project_name}", style="yellow"))

    if task_number:
        num = str(task_number)
        console.print(f"[bold]Выбрана задача:[/bold] #{num}")
    else:
        num = Prompt.ask(
            "Номер задачи для старта (Enter — первая)", default=str(issues[0]["number"])
        )

    selected = next((x for x in issues if str(x["number"]) == str(num)), None)
    if not selected:
        console.print("[red]Такой задачи нет.[/red]")
        return

    if not selected:
        console.print("[red]Такой задачи нет.[/red]")
        return

    title = selected["title"]
    body = (selected.get("body") or "").strip() or "[нет описания]"

    # Если номер задачи предоставлен, автоматически генерируем план и выходим
    if task_number:
        console.print(Panel(f"[bold]Выбрана задача:[/bold] #{num} {title}", style="green"))
        plan = ask_assistant(
            f"Составь подробный пошаговый план решения задачи: {title}\n\n{body}"
        )
        explanation = plan.get("explanation") or plan.get("message") or str(plan)
        note = plan.get("note", "")
        markdown_text = f"### 📋 План решения\n\n{explanation.strip()}"
        if note:
            markdown_text += f"\n\n> [i]{note.strip()}[/i]"
        console.print(
            Panel(
                Markdown(markdown_text),
                title="📋 План решения",
                style="cyan",
            )
        )
        return

    # Если интерактивный режим, продолжаем как раньше
    if selected:
        console.print(
            Panel(
                f"[bold]{selected['title']}[/bold]\n\n{body}",
                title=f"Issue #{num}",
                style="green",
            )
        )

    while True:
        console.print(
            Panel(
                "[1] Сгенерировать план\n"
                "[2] Создать git-ветку\n"
                "[3] Сгенерировать тесты\n"
                "[4] Объяснить задачу AI\n"
                "[5] Открыть файл/директорию\n"
                "[6] Start work (лог)\n"
                "[7] Назад",
                title="Что делаем дальше?",
                style="cyan",
            )
        )
        action = Prompt.ask(
            "Выбери действие", choices=["1", "2", "3", "4", "5", "6", "7"], default="1"
        )

        if action == "1":
            # Генерируем план решения
            plan = ask_assistant(
                f"Составь подробный пошаговый план решения задачи: {title}\n\n{body}"
            )
            # Сохраняем максимум информации: message, explanation, note
            explanation = plan.get("explanation") or plan.get("message") or str(plan)
            note = plan.get("note", "")

            # Красиво формируем вывод: Markdown
            markdown_text = f"### 📋 План решения\n\n{explanation.strip()}"
            if note:
                markdown_text += f"\n\n> [i]{note.strip()}[/i]"

            console.print(
                Panel(
                    Markdown(markdown_text),
                    title="📋 План решения",
                    style="cyan",
                )
            )
        elif action == "2":
            import subprocess

            branch_name = f"issue_{num}_{title.replace(' ', '_')[:20]}"
            subprocess.run(["git", "checkout", "-b", branch_name])
            console.print(Panel(f"🌿 Создана ветка: {branch_name}", style="green"))
        elif action == "3":
            # Генерация тестов (если есть файл)
            file_path = Prompt.ask("Укажи файл для теста", default="")
            if file_path:
                from jafar.cli.pytest_handlers import pytest_command

                pytest_command(file_path)
        elif action == "4":
            # AI-объяснение задачи
            ai_expl = ask_assistant(
                f"Объясни задачу простыми словами: {title}\n\n{body}"
            )
            console.print(
                Panel(
                    ai_expl.get("message", str(ai_expl)),
                    title="🤖 AI объяснение",
                    style="green",
                )
            )
        elif action == "5":
            # Просто открыть файл/директорию (можно реализовать через subprocess или через свой редактор)
            file_or_dir = Prompt.ask("Файл/папка для открытия", default=".")
            os.system(f"code {file_or_dir}")  # VSCode; можно сделать по-другому
        elif action == "6":
            # Start work (логировать в специальный лог)
            console.print("[green]🟢 Работа по задаче начата![/green]")
            # Можно добавить запись в логи, отправку статуса в Notion/Telegram и т.д.
        elif action == "7":
            break


import requests


def fetch_project_board_issues(owner, repo, project_number=1):
    # project_number можно узнать через GitHub UI или через API
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    query = """
    query($owner: String!, $repo: String!, $projectNumber: Int!, $first: Int!) {
      repository(owner: $owner, name: $repo) {
        projectV2(number: $projectNumber) {
          items(first: $first) {
            nodes {
              content {
                ... on Issue {
                  number
                  title
                  state
                  body
                  url
                }
              }
              fieldValues(first: 20) {
                nodes {
                  value
                }
              }
            }
          }
        }
      }
    }
    """
    variables = {
        "owner": owner,
        "repo": repo,
        "projectNumber": project_number,
        "first": 100,
    }
    resp = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers=headers,
    )
    data = resp.json()
    # Обработай data['data']['repository']['projectV2']['items']['nodes']
    return data
