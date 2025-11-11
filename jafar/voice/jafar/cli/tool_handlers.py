from rich.console import Console
from pathlib import Path
from jafar.tools.zip_project import zip_project  # :contentReference[oaicite:3]{index=3}
from jafar.tools.init_all_projects import (
    main as init_all_projects,
)  # :contentReference[oaicite:4]{index=4}

console = Console()


def tool_command(arg_string: str):
    """
    CLI: tool zip | init_all
    """
    if not arg_string:
        console.print("[yellow]usage:[/] tool zip | init_all")
        return

    cmd, *rest = arg_string.split()
    if cmd == "zip":
        zip_project()
    elif cmd == "init_all":
        init_all_projects()
    else:
        console.print(f"[red]Неизвестная утилита: {cmd}[/red]")
