from rich.console import Console
from rich.panel import Panel
from jafar.cli.utils import multiline_input
from jafar.assistant_core.assistant_api import ask_assistant
from jafar.cli.evolution import log_action, log_step

console = Console()


def chat_command(args):
    if not args.strip():
        args = multiline_input(
            "💬 Введите сообщение для Jafar-ассистента (Ctrl+D — отправить):"
        )
        if not args:
            console.print(
                Panel("[yellow]Нет текста для отправки![/yellow]", title="Пусто")
            )
            return

    log_action("chat_input", args)
    log_step("AI-чат", args)

    # Отправляем как есть ассистенту
    result = ask_assistant(args)
    if result:
        # Универсальный способ получить ответ
        response = (
            result.get("message")
            or result.get("explanation")
            or result.get("command")
            or result.get("note")
            or str(result)
        )
        console.print(Panel(response, title="🤖 Ответ Jafar", style="bold green"))
        log_action("chat_response", response[:300])
    else:
        console.print(
            Panel("[italic grey]Ассистент не дал ответа.[/italic grey]", title="Пусто")
        )

    # Показываем, что Jafar запомнил
    console.print(
        Panel(f"[cyan]Записано в обучение[/cyan]", title="📚 Jafar", style="dim")
    )
