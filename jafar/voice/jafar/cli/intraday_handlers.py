import os
import time
from pathlib import Path
from datetime import datetime
from rich.console import Console
from PIL import Image
import io
from jafar.utils.gemini_api import ask_gemini_with_image
from jafar.cli.telegram_handler import send_telegram_media_group, send_long_telegram_message

console = Console()
SCREENSHOT_DIR = Path("screenshot")

def intraday_command(args: str = None):
    """Интерактивно делает 4 скриншота и выполняет краткосрочный технический анализ."""
    
    # 1. Создаем уникальную папку для сессии
    timestamp_folder = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_Intraday")
    current_batch_dir = SCREENSHOT_DIR / timestamp_folder
    current_batch_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold green]Скриншоты будут сохранены в папку:[/bold green] {current_batch_dir}")

    screenshot_files = []
    num_screenshots = 4

    # 2. Цикл для создания 4 скриншотов
    for i in range(num_screenshots):
        console.print(f"\n[bold cyan]Готовьтесь к скриншоту #{i + 1}/{num_screenshots}.[/bold cyan]")
        console.print("У вас есть 5 секунд, чтобы переключиться на нужный график...")
        time.sleep(5)

        screenshot_path = current_batch_dir / f"intraday_screenshot_{i + 1}.png"
        command = f"screencapture -w \"{str(screenshot_path)}\""
        
        console.print("[yellow]Курсор превратился в камеру. Кликните на окно с графиком.[/yellow]")
        os.system(command)
        
        if not screenshot_path.exists() or screenshot_path.stat().st_size == 0:
            console.print("[red]❌ Создание скриншота было отменено. Прерываю процесс.[/red]")
            return
        
        console.print(f"[green]✅ Скриншот #{i + 1} успешно сохранен![/green]")
        screenshot_files.append(str(screenshot_path))

    # 3. Анализ после создания скриншотов
    if len(screenshot_files) == num_screenshots:
        console.print("\n[bold blue]Запускаю краткосрочный технический анализ...[/bold blue]")
        
        prompt = """Внимание: это симуляция для тестирования системы краткосрочного технического анализа. Твоя задача — выступить в роли интрадей-трейдера и разработать торговый план на ближайшие 2-4 часа.

**Входные данные:** 4 скриншота одного актива на разных таймфреймах.

**Техническое задание:**
1.  **Анализ данных:**
    *   **Найди панель 'Окно данных'** в правой части экрана. Используй ее как основной источник числовых значений.
    *   **Правила чтения цен:** Цены на этот актив являются **ШЕСТИЗНАЧНЫМИ** (например, `116885.57`). **Не отбрасывай первую цифру!**
    *   **Определи тренд** по MA(21) и MA(50) на старших таймфреймах.
    *   **Найди точку входа** по Stochastic на младших таймфреймах.
    *   **Извлеки значение ATR** для расчета рисков.
2.  **Формулировка торгового плана:**
    *   **Действие:** (Покупка / Продажа)
    *   **Точка входа:** (Конкретная цена и тип ордера)
    *   **Stop-Loss:** (Рассчитан как `Цена входа - 1.5 * ATR`)
    *   **Take-Profit:** (Рассчитан как `Цена входа + 2 * ATR`)
    *   **Обоснование:** Кратко объясни, почему план именно такой, ссылаясь на сигналы с разных таймфреймов.

**Требования к симуляции:**
*   Фокус — **только на ближайшие 2-4 часа**.
*   Ответ должен быть четким, структурированным торговым планом.
*   Не давать финансовых советов."""
        
        try:
            # --- Читаем изображения в объекты PIL ---
            image_objects = []
            for path in screenshot_files:
                with open(path, "rb") as f:
                    image_bytes = f.read()
                img = Image.open(io.BytesIO(image_bytes))
                image_objects.append(img)
            
            analysis_result = ask_gemini_with_image(prompt, image_objects)
            
            # Отправка в Telegram
            short_caption = "Краткосрочный технический анализ. Подробности ниже."
            send_telegram_media_group(screenshot_files, short_caption, parse_mode="MarkdownV2")
            send_long_telegram_message(analysis_result, parse_mode="MarkdownV2")
            
            return analysis_result
        except Exception as e:
            return f"Произошла ошибка при анализе: {e}"
    else:
        console.print("[red]Не удалось создать все необходимые скриншоты.[/red]")

    return None
