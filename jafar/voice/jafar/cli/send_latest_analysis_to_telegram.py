import os
from pathlib import Path
from rich.console import Console
from jafar.cli.telegram_handler import send_telegram_media_group, send_long_telegram_message

console = Console()

SCREENSHOT_DIR = Path("/Users/macbook/projects/jafar/screenshot")
ANALYSIS_DIR = Path("/Users/macbook/projects/jafar/analyzes")

def send_latest_analysis_to_telegram_command():
    """
    Находит последние 4 скриншота и последний файл анализа, 
    затем отправляет их в Telegram как медиа-группу с текстовой подписью.
    """
    console.print("[bold blue]Поиск последних скриншотов...[/bold blue]")
    screenshot_files = sorted(SCREENSHOT_DIR.glob("**/*.png"), key=os.path.getmtime, reverse=True)
    
    if not screenshot_files:
        console.print("[bold red]❌ Ошибка: Скриншоты не найдены в директории.[/bold red]")
        return

    # Берем последние 4 скриншота
    latest_screenshots = [str(f) for f in screenshot_files[:4]]
    console.print(f"[green]Найдены последние скриншоты: {latest_screenshots}[/green]")

    console.print("[bold blue]Поиск последнего файла анализа...[/bold blue]")
    analysis_files = sorted(ANALYSIS_DIR.glob("analysis_*.md"), key=os.path.getmtime, reverse=True)

    if not analysis_files:
        console.print("[bold red]❌ Ошибка: Файлы анализа не найдены в директории.[/bold red]")
        return

    latest_analysis_file = str(analysis_files[0])
    console.print(f"[green]Найден последний файл анализа: {latest_analysis_file}[/green]")

    # Читаем содержимое файла анализа
    try:
        with open(latest_analysis_file, 'r', encoding='utf-8') as f:
            analysis_content = f.read()
    except Exception as e:
        console.print(f"[bold red]❌ Ошибка при чтении файла анализа: {e}[/bold red]")
        return

    # Отправляем в Telegram как медиа-группу с коротким заголовком
    console.print("[bold blue]Отправка анализа и скриншотов в Telegram...[/bold blue]")
    send_telegram_media_group(latest_screenshots, "Последние скриншоты", parse_mode=None)
    
    # Отправляем длинное сообщение с анализом
    send_long_telegram_message(analysis_content, parse_mode="MarkdownV2")

    console.print("[bold green]✅ Процесс отправки завершен.[/bold green]")
