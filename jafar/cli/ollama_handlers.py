# jafar/cli/ollama_handlers.py

from rich.console import Console
from rich.panel import Panel
from jafar.integrations.ollama_api import generate_text, chat_completion, list_models

console = Console()

def ollama_generate_command(prompt: str, model: str = "llama2"):
    """
    Генерирует текст с помощью Ollama.
    """
    console.print(Panel(f"[bold blue]Генерация текста с Ollama (модель: {model})...[/bold blue]"))
    result = generate_text(prompt, model=model)
    if result and "response" in result:
        console.print(Panel(f"[bold green]Ответ Ollama:[/bold green]\n{result["response"]}", style="green"))
    else:
        console.print(Panel("[bold red]Не удалось сгенерировать текст с Ollama.[/bold red]", style="red"))

def ollama_chat_command(message: str, model: str = "llama2"):
    """
    Отправляет сообщение в чат Ollama.
    """
    console.print(Panel(f"[bold blue]Отправка сообщения в чат Ollama (модель: {model})...[/bold blue]"))
    messages = [
        {"role": "user", "content": message}
    ]
    chat_result = chat_completion(messages, model=model)
    if chat_result and "message" in chat_result:
        console.print(Panel(f"[bold green]Ответ Ollama Chat:[/bold green]\n{chat_result["message"]["content"]}", style="green"))
    else:
        console.print(Panel("[bold red]Не удалось получить ответ от Ollama Chat.[/bold red]", style="red"))

def ollama_list_models_command():
    """
    Выводит список доступных моделей Ollama.
    """
    console.print(Panel("[bold blue]Получение списка моделей Ollama...[/bold blue]"))
    models = list_models()
    if models and "models" in models:
        console.print(Panel("[bold green]Доступные модели Ollama:[/bold green]", style="green"))
        for m in models["models"]:
            console.print(f"- [bold]{m['name']}[/bold] (размер: {round(m['size'] / (1024*1024*1024), 2)} GB)")
    else:
        console.print(Panel("[bold red]Не удалось получить список моделей Ollama.[/bold red]", style="red"))
