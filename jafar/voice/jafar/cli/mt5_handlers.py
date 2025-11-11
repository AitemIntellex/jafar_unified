import os
import time
from pathlib import Path
from datetime import datetime
from rich.console import Console
from jafar.cli.image_analysis_handler import analyze_screenshot_for_plan

console = Console()
SCREENSHOT_DIR = Path("screenshot")

def mt5_screenshot_command(args: str = None):
    """Интерактивно делает 4 скриншота окон, которые выберет пользователь."""
    
    # 1. Создаем уникальную папку для этой сессии скриншотов
    base_screenshot_dir = SCREENSHOT_DIR
    timestamp_folder = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_MT5")
    current_batch_dir = base_screenshot_dir / timestamp_folder
    current_batch_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold green]Скриншоты будут сохранены в папку:[/bold green] {current_batch_dir}")

    screenshot_files = []
    num_screenshots = 4

    # 2. Цикл для создания 4 скриншотов
    for i in range(num_screenshots):
        console.print(f"\n[bold cyan]Готовьтесь к скриншоту #{i + 1}/{num_screenshots}.[/bold cyan]")
        console.print("У вас есть 5 секунд, чтобы переключиться на нужное окно MetaTrader 5...")
        
        # Пауза, чтобы пользователь успел переключиться
        time.sleep(5)

        # Формируем путь для сохранения файла
        screenshot_path = current_batch_dir / f"mt5_screenshot_{i + 1}.png"
        
        # Команда для захвата одного окна (macOS)
        # Флаг -w ожидает клика по окну
        command = f"screencapture -w \"{str(screenshot_path)}\""
        
        console.print("[yellow]Курсор превратился в камеру. Кликните на окно MetaTrader 5, чтобы сделать снимок.[/yellow]")
        
        # Выполняем команду
        os.system(command)
        
        # Проверяем, был ли создан файл (пользователь мог отменить)
        if screenshot_path.exists():
            console.print(f"[green]✅ Скриншот #{i + 1} успешно сохранен![/green]")
            screenshot_files.append(str(screenshot_path))
        else:
            console.print("[red]❌ Создание скриншота было отменено. Прерываю процесс.[/red]")
            return

    # 3. Запрос на анализ после создания всех скриншотов
    if len(screenshot_files) == num_screenshots:
        console.print("\n[bold green]Все 4 скриншота готовы.[/bold green]")
        console.print("[bold yellow]Начать анализ? (y/n)[/bold yellow]")
        try:
            user_input = input("> ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[red]Анализ отменен.[/red]")
            return

        if user_input == 'y':
            console.print("[bold blue]Запускаю анализ...[/bold blue]")
            # Вызываем уже существующую функцию анализа
            analysis_result = analyze_screenshot_for_plan(" ".join(screenshot_files))
            return analysis_result # Возвращаем результат для вывода в command_router
        else:
            console.print("[yellow]Анализ отменен.[/yellow]")
    else:
        console.print("[red]Не удалось создать все необходимые скриншоты.[/red]")

    return # Возвращаем None, если анализ не был запущен
