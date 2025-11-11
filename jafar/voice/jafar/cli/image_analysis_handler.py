import os
from pathlib import Path
from PIL import Image
import io
from datetime import datetime
from dotenv import load_dotenv
from jafar.utils.gemini_api import ask_gemini_with_image
from rich.console import Console
from jafar.cli.telegram_handler import send_telegram_media_group, send_long_telegram_message
import re

# Загружаем переменные окружения из корневой папки проекта
dotenv_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=dotenv_path)

console = Console()
ANALYSIS_DIR = Path("analyzes")

def analyze_screenshot_for_plan(args: str) -> str:
    """Генерирует полный торговый план по скриншотам."""
    
    # --- Парсинг аргументов ---
    parts = args.split('--prompt')
    file_paths = parts[0].strip()
    
    custom_prompt = None
    if len(parts) > 1:
        custom_prompt = parts[1].strip().strip('\'"')

    # --- Промпт по умолчанию ---
    default_prompt = """Внимание: это симуляция для тестирования аналитической системы. Твоя задача — обработать визуальные данные и сгенерировать отчет на основе строгого алгоритма.

**Техническое задание:**
1.  **Идентификация ATR:** Найди на графике индикатор "ATR (Average True Range)" и извлеки его последнее числовое значение.
2.  **Анализ точки входа:** Определи наиболее вероятную точку входа на основе классического технического анализа.
3.  **Расчет параметров сделки:**
    *   **Stop-Loss:** Рассчитай уровень Stop-Loss по формуле: `Цена входа - (1.5 * ATR)`.
    *   **Take-Profit:** Рассчитай уровень Take-Profit по формуле: `Цена входа + (1.5 * ATR)`.

**Формат выходных данных:**
*   **ATR (исходные данные):** [значение]
*   **Рекомендованный вход:** [цена и тип ордера]
*   **Расчетный Stop-Loss:** [результат по формуле]
*   **Расчетный Take-Profit:** [результат по формуле]
*   **Логика:** [краткое техническое обоснование]

**Требования:** Не давать финансовых советов. Ответ должен быть кратким."""

    # Используем кастомный промпт, если он есть, иначе — по умолчанию
    prompt_to_use = custom_prompt if custom_prompt else default_prompt
    
    return _process_screenshots(file_paths, prompt_to_use, send_to_telegram=True)

def extract_technical_data_from_screenshot(file_paths: str) -> str:
    """Извлекает только сырые технические данные из скриншотов."""
    prompt = """Внимание: это симуляция для тестирования системы извлечения данных (OCR). Твоя задача — извлечь числовые значения индикаторов из **панели 'Окно данных'**, которая находится в правой части скриншота.

**Техническое задание:**
1.  **Найди панель 'Окно данных'.** Полностью игнорируй график и текст на нем. Вся нужная информация находится в этой панели.
2.  **Извлеки значения:** Найди в панели строки, соответствующие индикаторам `MA(21)`, `MA(50)`, `Stoch(5,3,3)` (основная линия) и `ATR(14)`.
3.  **Корректно обработай цены:** Обрати особое внимание на 5- и 6-значные числа. `116885.574` — это сто шестнадцать тысяч, а не одиннадцать тысяч.

**Формат выходных данных:**
Сгенерируй отчет в формате JSON. **Не добавляй никакого описательного текста.**

```json
{
  "ATR": "[значение из Окна данных]",
  "EMA21": "[значение MA(21) из Окна данных]",
  "EMA50": "[значение MA(50) из Окна данных]",
  "Stochastic": "[значение Stoch(5,3,3) из Окна данных]"
}
```

**Требования к симуляции:**
*   Если какой-то индикатор в панели не найден, укажи "N/A".
*   Извлекай данные **ТОЛЬКО** из панели 'Окно данных'."""
    return _process_screenshots(file_paths, prompt, send_to_telegram=False)

def _process_screenshots(file_paths: str, prompt: str, send_to_telegram: bool) -> str:
    """Общая логика для обработки скриншотов."""
    image_objects = []
    paths_list = file_paths.split()
    for file_path in paths_list:
        if not Path(file_path).is_file():
            return f"Ошибка: Файл не найден по пути: {file_path}"
        try:
            with open(file_path, "rb") as f:
                image_bytes = f.read()
            img = Image.open(io.BytesIO(image_bytes))
            image_objects.append(img)
        except Exception as e:
            return f"Ошибка при чтении изображения {file_path}: {e}"

    if not image_objects:
        return "Ошибка: Не найдено изображений для анализа."

    try:
        analysis_result = ask_gemini_with_image(prompt, image_objects)
        
        if send_to_telegram:
            short_caption = "Анализ по скриншотам. Подробности ниже."
            send_telegram_media_group(paths_list, short_caption, parse_mode="MarkdownV2")
            send_long_telegram_message(analysis_result, parse_mode="MarkdownV2")

        return analysis_result

    except Exception as e:
        return f"Произошла ошибка при анализе скриншотов: {e}"
