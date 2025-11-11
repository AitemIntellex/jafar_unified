from rich.console import Console
from jafar.core.game_mode import run_game_mode  # твой game_mode.py
from jafar.core.trainer_mode import run_trainer_mode  # твой trainer_mode.py

console = Console()


def mode_command(arg_string: str):
    """
    CLI: mode game | trainer
    """
    if arg_string == "game":
        run_game_mode()
    elif arg_string == "trainer":
        run_trainer_mode()
    else:
        console.print("[yellow]usage:[/] mode game | trainer")
