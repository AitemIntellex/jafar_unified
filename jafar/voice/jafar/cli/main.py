import os
import platform
import getpass
import socket
import traceback
from datetime import datetime
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import HTML

from jafar.assistant_core.ai_watcher import observe_and_respond
from jafar.cli.command_router import handle_command
from jafar.cli.game_handlers import game_mode_chat
from jafar.assistant_core.readme_logger import log_to_readme

from jafar.integrations.github_api import list_issues
from jafar.skills.project_manager.manager import load_config

console = Console()
HISTORY_FILE = os.path.expanduser("~/.jafar/jafar_history.txt")


def print_banner():
    md = Markdown(
        f"""# 🚀 Jafar AI Terminal 🚀

## 🤖 Ваш интеллектуальный ассистент

**Время запуска:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Версия Python:** {platform.python_version()}

--- 

*   **Готов к работе!**
*   **Введите `help` для списка команд.**
"""
    )
    console.print(Panel(md, style="bold green", border_style="bright_cyan"))


def jafar_prompt():
    user = getpass.getuser()
    host = socket.gethostname().split(".")[0]
    cwd = os.path.basename(os.getcwd())
    return HTML(
        f"<ansisilver>{user}</ansisilver>"
        f"@<ansicyan>{host}</ansicyan> "
        f"<ansigreen>{cwd}</ansigreen> "
        f"<ansiblack></ansiblack> "
        f"<ansiblue>jafar</ansiblue> <white>❯</white> "
    )


def show_jafar_status():
    table = Table(title="🧠 Jafar Status Overview", style="cyan", expand=True)
    table.add_column("Parameter/Параметр")
    table.add_column("Value/Значение")
    table.add_row("OS", platform.system())
    table.add_row("User", getpass.getuser())
    table.add_row("Machine", socket.gethostname())
    table.add_row("Python", platform.python_version())
    table.add_row("Working Dir", os.getcwd())
    table.add_row("Active Project", get_active_project())
    table.add_row("Mode", "CLI-ready")
    table.add_row("AI Thread", "✓ loaded")
    console.print(table)


def get_active_project():
    cwd = os.getcwd()
    config = load_config() or {}
    parts = cwd.split(os.sep)
    for part in reversed(parts):
        if part in config:
            return part
    return "jafar_v2"


def show_project_tasks(project_name=None):
    config = load_config() or {}
    if not config:
        console.print(Panel("Конфиг проектов не найден.", style="red"))
        return

    name = project_name or get_active_project()
    project_info = config.get(name)
    if not project_info:
        console.print(Panel(f"Проект '{name}' не найден в config.", style="yellow"))
        return

    owner = project_info.get("owner")
    repo = project_info.get("repo")

    if not owner or not repo:
        console.print(
            Panel(f"В конфиге для '{name}' отсутствуют owner/repo.", style="red")
        )
        return

    issues = list_issues(owner, repo)
    if not issues or (isinstance(issues, dict) and issues.get("message")):
        console.print(Panel("Нет открытых задач или ошибка API.", style="yellow"))
        return

    table = Table(title=f"GitHub Issues for {name}", style="magenta", expand=True)
    table.add_column("#")
    table.add_column("Title")
    table.add_column("Status")
    for issue in issues:
        table.add_row(
            str(issue.get("number", "")), issue.get("title", ""), issue.get("state", "")
        )
    console.print(table)


def show_mock_tasks():
    md = Markdown(
        """
**📋 Tasks from neighbor project**

- [ ] Подключить pre-commit в tms_backend
- [ ] Настроить Celery + Redis в TradeSpace
- [ ] Проверить структуру game_handlers.py
- [ ] Сделать граф auto-evolution
        """
    )
    panel = Panel(
        md,
        title="🚧 Project Tasks Snapshot (Mock)",
        style="bright_cyan",
    )
    console.print(panel)


def main():
    command = ""
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

        if len(sys.argv) > 1:
            # Если есть аргументы командной строки, выполнить их как команду
            command = " ".join(sys.argv[1:])
            handle_command(command, interactive_session=False)
            return  # Завершить работу после выполнения команды

        if not sys.stdout.isatty():
            console.print(Panel("[bold yellow]Non-interactive mode detected. Jafar CLI is designed for interactive use.[/bold yellow]\nTo execute a command, pass it as an argument, e.g., [cyan]jafar 'your command'[/cyan]", title="Jafar CLI"))
            return

        session = PromptSession(history=FileHistory(HISTORY_FILE))
        print_banner()
        # show_jafar_status() # <-- Закомментировать или удалить эту строку
        console.print("[bold green]Jafar готов к работе! Введите 'help' для списка команд.[/bold green]") # <-- Новое, более явное сообщение
        log_to_readme("запуск CLI", "Jafar готов к работе")

        while True:
            try:
                command = session.prompt(jafar_prompt()).strip()
                if not command:
                    continue
                # Теперь handle_command не блокирует prompt даже при неизвестной команде!
                handle_command(command, interactive_session=True)

                response = observe_and_respond(command)
                if response:
                    console.print(
                        Panel(
                            f"🦉 [bold green]Advice:[/bold green] {response}",
                            style="blue",
                        )
                    )
                    log_to_readme(
                        "рекомендация", f"Совет по команде '{command}'", response
                    )

            except (KeyboardInterrupt, EOFError):
                console.print("\n👋 See you!")
                log_to_readme("exit", "Jafar completed Cli")
                break
            except Exception as e:
                console.print(f"[red]❌ Error: {e}[/red]")
                traceback.print_exc()
                log_to_readme("error", f"Ошибка в команде '{command}'", str(e))

    except Exception as e:
        console.print(f"[red]❌ Ошибка при старте: {e}[/red]")
        traceback.print_exc()
        log_to_readme("ошибка запуска", "Ошибка при запуске CLI", str(e))



if __name__ == "__main__":
    main()


def run_jafar():
    main()
