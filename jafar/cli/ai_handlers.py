from jafar.cli.utils import multiline_input
from rich.console import Console
from rich.panel import Panel
from jafar.utils.assistant_api import ask_assistant

console = Console()

def ai_command(args):
    if not args.strip():
        console.print(Panel("[yellow]⚠ Введите запрос после команды ai[/yellow]", title="AI Запрос"))
        return

    # Парсинг опций
    prompt_text = args
    response_type = "text"  # По умолчанию

    if "--code" in args:
        response_type = "code"
        prompt_text = args.replace("--code", "").strip()
    elif "--plan" in args:
        response_type = "plan"
        prompt_text = args.replace("--plan", "").strip()
    elif "--json" in args:
        response_type = "json"
        prompt_text = args.replace("--json", "").strip()

    console.print(Panel(f"[bold magenta]AI:[/bold magenta] {prompt_text}", title="AI Запрос", style="bold cyan"))
    result = ask_assistant(prompt_text, response_type=response_type) or {}

    if "command" in result:
        console.print(f"[bold green]⮞ Команда:[/bold green] {result['command']}")
    if "explanation" in result:
        console.print(f"[cyan]⮞ Пояснение:[/cyan] {result['explanation']}")
    if "note" in result and result['note']:
        console.print(f"[yellow]⮞ Примечание:[/yellow] {result['note']}")
    if not result:
        console.print("[yellow]Нет ответа от ассистента[/yellow]")
