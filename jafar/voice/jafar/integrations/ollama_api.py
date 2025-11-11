# jafar/integrations/ollama_api.py

import os
import requests
import json
from rich.console import Console
from rich.panel import Panel

console = Console()

# Получаем хост Ollama из переменных окружения или используем значение по умолчанию
OLLAMA_HOST = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

def generate_text(prompt: str, model: str = "llama2", stream: bool = False):
    """
    Отправляет запрос к Ollama API для генерации текста.

    Args:
        prompt (str): Входной текст для генерации.
        model (str): Название модели Ollama для использования (по умолчанию "llama2").
        stream (bool): Если True, получает ответ в потоковом режиме.
                       В этом примере обрабатывается как не-потоковый.
    Returns:
        dict: Ответ от Ollama API в формате JSON, или None в случае ошибки.
    """
    url = f"{OLLAMA_HOST}/api/generate"
    console.print(f"[dim]Отправка запроса на: {url}[/dim]") # Отладочный вывод
    headers = {"Content-Type": "application/json"}
    data = {
        "model": model,
        "prompt": prompt,
        "stream": stream
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()  # Вызывает исключение для ошибок HTTP
        return response.json()
    except requests.exceptions.RequestException as e:
        console.print(Panel(f"❌ Ошибка связи с Ollama: {e}", style="red"))
        return None

def chat_completion(messages: list, model: str = "llama2", stream: bool = False):
    """
    Отправляет запрос к Ollama API для завершения чата.

    Args:
        messages (list): Список сообщений в формате чата.
        model (str): Название модели Ollama для использования (по умолчанию "llama2").
        stream (bool): Если True, получает ответ в потоковом режиме.
                       В этом примере обрабатывается как не-потоковый.
    Returns:
        dict: Ответ от Ollama API в формате JSON, или None в случае ошибки.
    """
    url = f"{OLLAMA_HOST}/api/chat"
    console.print(f"[dim]Отправка запроса на: {url}[/dim]") # Отладочный вывод
    headers = {"Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": messages,
        "stream": stream
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()  # Вызывает исключение для ошибок HTTP
        return response.json()
    except requests.exceptions.RequestException as e:
        console.print(Panel(f"❌ Ошибка связи с Ollama: {e}", style="red"))
        return None

def list_models():
    """
    Получает список доступных моделей Ollama.

    Returns:
        dict: Список моделей Ollama в формате JSON, или None в случае ошибки.
    """
    url = f"{OLLAMA_HOST}/api/tags"
    console.print(f"[dim]Отправка запроса на: {url}[/dim]") # Отладочный вывод
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        console.print(Panel(f"❌ Ошибка получения списка моделей Ollama: {e}", style="red"))
        return None

if __name__ == "__main__":
    # Пример использования
    console.print(Panel("[bold green]Тестирование Ollama API интеграции[/bold green]"))

    # Тест generate_text
    console.print("\n[bold blue]Тестирование generate_text:[/bold blue]")
    prompt = "Напиши короткое стихотворение о весне."
    result = generate_text(prompt, model="llama2") # Убедитесь, что модель llama2 загружена
    if result and "response" in result:
        console.print(Panel(f"Сгенерированный текст:\n{result['response']}", style="cyan"))
    else:
        console.print(Panel("Не удалось сгенерировать текст.", style="red"))

    # Тест chat_completion
    console.print("\n[bold blue]Тестирование chat_completion:[/bold blue]")
    messages = [
        {"role": "user", "content": "Привет, как дела?"}
    ]
    chat_result = chat_completion(messages, model="llama2") # Убедитесь, что модель llama2 загружена
    if chat_result and "message" in chat_result:
        console.print(Panel(f"Ответ чата:\n{chat_result['message']['content']}", style="magenta"))
    else:
        console.print(Panel("Не удалось получить ответ чата.", style="red"))

    # Тест list_models
    console.print("\n[bold blue]Тестирование list_models:[/bold blue]")
    models = list_models()
    if models and "models" in models:
        console.print(Panel("Доступные модели Ollama:", style="yellow"))
        for m in models["models"]:
            console.print(f"- {m['name']}")
    else:
        console.print(Panel("Не удалось получить список моделей.", style="red"))
