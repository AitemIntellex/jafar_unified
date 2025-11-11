from pathlib import Path
from datetime import datetime
from rich.console import Console
from dotenv import load_dotenv
import os
import shlex

from jafar.cli.telegram_handler import send_long_telegram_message # Используем send_long_telegram_message

# Загружаем переменные окружения из корневой папки проекта
dotenv_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=dotenv_path)

console = Console()

ANALYSIS_DIRS = {
    "news": Path(__file__).parent.parent.parent / "analyzes" / "news",
    "crypto": Path(__file__).parent.parent.parent / "analyzes" / "crypto",
    "world_news": Path(__file__).parent.parent.parent / "analyzes" / "world_news",
    "gold": Path(__file__).parent.parent.parent / "analyzes" / "gold",
    "currency": Path(__file__).parent.parent.parent / "analyzes" / "currency",
    "futures": Path(__file__).parent.parent.parent / "analyzes" / "futures",
    "economic_calendar": Path(__file__).parent.parent.parent / "analyzes" / "economic_calendar",
}

def finalize_analysis(args: str):
    """Сохраняет отчет и отправляет его в Telegram, поддерживая parse_mode."""
    try:
        parts = shlex.split(args)
        analysis_type = parts[0]

        # Устанавливаем parse_mode по умолчанию и ищем флаг
        parse_mode = "MarkdownV2"
        if "--parse_mode" in parts:
            try:
                pm_index = parts.index("--parse_mode")
                parse_mode = parts[pm_index + 1]
                # Удаляем флаг и его значение из списка для дальнейшей обработки
                parts.pop(pm_index)
                parts.pop(pm_index)
            except (ValueError, IndexError):
                console.print(f"[bold red]Ошибка: Неверное использование флага --parse_mode.[/bold red]")
                return

        # Все, что осталось после типа анализа и флагов - это текст отчета
        report_text_or_path = " ".join(parts[1:])

        if report_text_or_path.startswith('--file '):
            file_path_str = report_text_or_path[len('--file '):]
            file_path = Path(file_path_str)
            if file_path.is_file():
                with open(file_path, "r", encoding="utf-8") as f:
                    report_text = f.read()
            else:
                console.print(f"[bold red]Ошибка: Файл не найден: {file_path}[/bold red]")
                return
        else:
            report_text = report_text_or_path

        analysis_dir = ANALYSIS_DIRS.get(analysis_type)
        if not analysis_dir:
            console.print(f"[bold red]Ошибка: Неизвестный тип анализа: {analysis_type}[/bold red]")
            return

        analysis_dir.mkdir(exist_ok=True, parents=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # Сохраняем как .html если parse_mode HTML, иначе .md
        file_extension = ".html" if parse_mode == "HTML" else ".md"
        file_path = analysis_dir / f"{analysis_type}_analysis_{timestamp}{file_extension}"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        
        console.print(f"[green]Анализ сохранен в {file_path}[/green]")

        # Формируем сообщение для Telegram
        # Для HTML используем <b>, для Markdown **
        title_wrapper_start = "<b>" if parse_mode == "HTML" else "**"
        title_wrapper_end = "</b>" if parse_mode == "HTML" else "**"
        telegram_message = f"{title_wrapper_start}Отчет по анализу: {analysis_type.upper()}{title_wrapper_end}\n\n---\n\n{report_text}"
        
        # Используем send_long_telegram_message для поддержки длинных сообщений
        send_long_telegram_message(telegram_message, parse_mode=parse_mode)

    except Exception as e:
        console.print(f"[bold red]Произошла ошибка при финализации анализа: {e}[/bold red]")
