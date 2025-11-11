# renderers/render_rich.py
from rich.console import Console
from rich.table import Table

def render_game_status(state):
    console = Console()
    table = Table(title="🧠 Jafar Game Mode")

    table.add_column("Module", style="cyan", no_wrap=True)
    table.add_column("Status", style="green")

    for key, value in state.items():
        emoji = "✅" if value in ["running", "connected", "clean"] else "❌"
        table.add_row(key, f"{emoji} {value}")

    console.print(table)
