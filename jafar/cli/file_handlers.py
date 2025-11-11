from jafar.cli.utils import multiline_input
from rich.console import Console
from rich.panel import Panel
import traceback
console = Console()
def file_command(args):
    console.print(Panel(f"[bold yellow]Файловая команда:[/bold yellow] {args}", title="FileOps", style="bold yellow"))
    # Здесь — todo: связка с upload/download/CI/CD для AI
    console.print("[italic yellow]Загрузка и review файлов через AI — в разработке.[/italic yellow]")
