import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
from rich.console import Console
import re

from ..utils.investing_calendar import get_investing_calendar

console = Console()

def fetch_and_save_economic_calendar_data(args: str = None):
    """
    Получает данные экономического календаря с Investing.com и сохраняет их во временный файл.
    """
    temp_dir = Path(__file__).parent.parent.parent / "temp"
    temp_dir.mkdir(exist_ok=True, parents=True)
    output_file = temp_dir / "economic_calendar_data.txt"

    try:
        console.print("[bold blue]Получение данных экономического календаря с Investing.com...[/bold blue]")
        calendar_events = get_investing_calendar()

        if not calendar_events:
            console.print("[bold yellow]Нет доступных событий в экономическом календаре.[/bold yellow]")
            console.print(f"GEMINI_ECONOMIC_CALENDAR_DATA_PATH:{output_file}") # Все равно выводим путь, но файл будет пустым
            return

        data_lines = []
        for event in calendar_events:
            data_lines.append(
                f"Дата: {event['time']}, Страна: {event['country']}, Важность: {event['impact']} звезды, Событие: {event['name']}, Факт: {event['fact']}, Прогноз: {event['expected']}, Пред.: {event['previous']}"
            )

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(data_lines))
        
        console.print(f"[bold green]Данные экономического календаря сохранены в {output_file}[/bold green]")
        console.print(f"GEMINI_ECONOMIC_CALENDAR_DATA_PATH:{output_file}")

    except Exception as e:
        console.print(f"[bold red]Произошла ошибка при получении данных экономического календаря: {e}[/bold red]")

def fetch_economic_calendar_data():
    """
    Получает данные экономического календаря с Investing.com и возвращает их в виде строки.
    """
    try:
        console.print("[bold blue]Получение свежих данных экономического календаря...[/bold blue]")
        calendar_events = get_investing_calendar()

        # Получаем текущее локальное время и его смещение относительно UTC
        now = datetime.now()
        local_tz_offset = now.astimezone().strftime('%z')
        current_local_time = now.strftime(f"%Y-%m-%d %H:%M:%S ({local_tz_offset})")
        
        data_lines = [f"**Ҳозирги маҳаллий вақт:** {current_local_time}"]

        if not calendar_events:
            console.print("[bold yellow]Нет доступных событий в экономическом календаре.[/bold yellow]")
            data_lines.append("Экономический календарь пуст.")
            return "\n".join(data_lines)

        for event in calendar_events:
            data_lines.append(
                f"Дата: {event['time']}, Страна: {event['country']}, Важность: {event['impact']} звезды, Событие: {event['name']}, Факт: {event['fact']}, Прогноз: {event['expected']}, Пред.: {event['previous']}"
            )
        
        console.print("[bold green]Свежие данные экономического календаря успешно получены.[/bold green]")
        return "\n".join(data_lines)

    except Exception as e:
        console.print(f"[bold red]Произошла ошибка при получении свежих данных календаря: {e}[/bold red]")
        return f"Ошибка при получении данных календаря: {e}"