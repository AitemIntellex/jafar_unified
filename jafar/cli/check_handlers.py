# jafar/cli/check_handlers.py
from rich.console import Console
from ..checkers import (
    check_git,
    check_internet,
    check_processes,
)
from ..checkers.check_git import check_git_status
from ..checkers.check_internet import check_internet_status
from ..checkers.check_processes import check_process

console = Console()


def check_command(arg_string: str):
    """
    CLI: check git | internet | process <name>
    """
    if not arg_string:
        console.print("[yellow]usage:[/] check git | internet | process <proc>")
        return

    cmd, *rest = arg_string.split()
    command_checks = {
        "git": lambda: _print_git_status(),
        "internet": lambda: _print_internet_status(),
        "process": lambda: _print_process_status(rest),
    }

    if cmd in command_checks:
        command_checks[cmd]()
    else:
        console.print(f"[red]Неизвестная проверка: {cmd}[/red]")


def _print_git_status():
    status = check_git_status()
    msg = {
        "clean": "✅  Git чист",
        "changes": "⚠️  Есть изменения",
        "not a repo": "❌  Не git-репозиторий",
    }[status]
    console.print(msg)


def _print_internet_status():
    status = check_internet_status()
    msg = "✅  Интернет OK" if status == "connected" else "❌  Нет соединения"
    console.print(msg)


def _print_process_status(rest):
    if not rest:
        console.print("[yellow]Укажи название процесса[/]")
        return
    status = check_process(rest[0])
    msg = {
        "running": "✅  Процесс запущен",
        "not running": "❌  Не запущен",
        "error": "⚠️  Ошибка ps",
    }[status]
    console.print(msg)



def handle(args: list[str]):
    if not args:
        console.print("[yellow]Доступные проверки: git, internet, processes[/]")
        return

    sub = args[0]
    if sub == "git":
        check_git.run()
    elif sub == "internet":
        check_internet.run()
    elif sub == "processes":
        check_processes.run()
    else:
        console.print(f"[red]Неизвестная проверка {sub}[/]")
