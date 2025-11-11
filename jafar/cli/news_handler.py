

import os
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from jafar.utils.assistant_api import ask_assistant
ANALYSIS_DIR = Path("analyzes/news")
console = Console()

def process_news_command(file_path: str) -> str:
    """
    Анализирует новостные фрагменты из файла с помощью AI.

    Args:
        file_path (str): Путь к файлу с новостными фрагментами.

    Returns:
        str: Результат анализа новостей.
    """
    try:
        if not os.path.exists(file_path):
            return f"Ошибка: Файл не найден по пути: {file_path}"

        with open(file_path, "r", encoding="utf-8") as f:
            news_snippets = f.read()

        if not news_snippets:
            return "Файл пуст или не содержит новостных фрагментов для анализа."

        prompt = f"На основе этих новостных фрагментов, предоставь краткий обзор текущей ситуации на рынке. Укажи ключевые события, общий сентимент (бычий, медвежий, нейтральный) и возможные влияния на рынок.\n\nНовости:\n{news_snippets}"

        console.print("[bold blue]🤖 Анализ новостей с помощью AI...[/bold blue]")
        analysis_result = ask_assistant(prompt)

        # Сохранение результата
        ANALYSIS_DIR.mkdir(exist_ok=True, parents=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file = ANALYSIS_DIR / f"news_analysis_{timestamp}.md"

        log_entry = f"""# 📰 Анализ новостей от {timestamp}

## 🤖 Результат анализа
{analysis_result}
"""

        with open(log_file, "w", encoding="utf-8") as f:
            f.write(log_entry)
        
        console.print(f"[green]Анализ сохранен в {log_file}[/green]")

        return analysis_result.get("explanation") or str(analysis_result)

    except Exception as e:
        console.print(f"[bold red]Произошла ошибка при анализе новостей: {e}[/bold red]")
        return ""

