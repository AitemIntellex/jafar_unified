from rich.console import Console
from rich.panel import Panel
from jafar.assistant_core.assistant_api import ask_assistant
from jafar.state.agent_preferences import load_agent_preferences, save_agent_preferences, get_default_agent_preferences

console = Console()

def agent_mode_command(prompt: str):
    from jafar.cli.command_router import handle_command # Импортируем здесь, чтобы избежать циклического импорта

    # Загружаем предпочтения агента
    preferences = load_agent_preferences()
    if not preferences:
        preferences = get_default_agent_preferences()
        save_agent_preferences(preferences) # Сохраняем предпочтения по умолчанию
        console.print(Panel("[bold green]Jafar: Инициализированы предпочтения агента по умолчанию.[/bold green]", style="green"))

    # Формируем промпт для AI, используя предпочтения
    ai_prompt = (
        f'{preferences.get("role", "")}\n'
        f'{preferences.get("interaction_style", "")}\n'
        f'{preferences.get("primary_tool", "")}\n'
        f'{preferences.get("response_style", "")}\n\n'
        f'Пользователь хочет, чтобы ты выполнил следующую задачу: "{prompt}". '
        'Определи, какие команды Jafar CLI нужно выполнить для этого. '
        'Верни ответ в JSON формате с полем "commands" (список строк команд) и, если нужно, "explanation". '
        'Пример: {"commands": ["project summary tms_backend", "github status"], "explanation": "Получение сводки и статуса git"}'
    )

    console.print(Panel(f"[bold magenta]Agent Mode Prompt:[/bold magenta] {prompt}", title="Jafar Agent Mode", style="bold blue"))
    
    # Отправляем промпт AI и просим вернуть команду Jafar CLI
    ai_response = ask_assistant(
        ai_prompt,
        response_type="json"
    )

    if ai_response and "explanation" in ai_response and isinstance(ai_response["explanation"], dict):
        response_data = ai_response["explanation"]
        commands_to_execute = response_data.get("commands")
        explanation = response_data.get("explanation")

        if commands_to_execute and isinstance(commands_to_execute, list):
            if explanation:
                console.print(Panel(f"[cyan]Пояснение:[/cyan] {explanation}", style="cyan"))
            
            for cmd in commands_to_execute:
                console.print(Panel(f"[bold green]Jafar выполняет команду:[/bold green] {cmd}", style="green"))
                try:
                    handle_command(cmd, interactive_session=False)
                except Exception as e:
                    console.print(Panel(f"[red]❌ Ошибка при выполнении команды '{cmd}': {e}[/red]", style="red"))
                    console.print(Panel("[red]Последовательность команд прервана из-за ошибки.[/red]", style="red"))
                    return # Stop execution on first error
        else:
            console.print(Panel("[red]AI не смог определить команды для выполнения.[/red]", style="red"))
    else:
        console.print(Panel("[red]Не удалось получить структурированный ответ от AI.[/red]", style="red"))
