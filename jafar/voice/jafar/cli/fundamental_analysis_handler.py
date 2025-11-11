import os
from pathlib import Path
from PIL import Image
import io
from datetime import datetime
from dotenv import load_dotenv
from jafar.utils.gemini_api import ask_gemini_with_image, ask_gemini_text_only
from rich.console import Console
from jafar.cli.telegram_handler import send_telegram_media_group
import re

# Загружаем переменные окружения из корневой папки проекта
dotenv_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=dotenv_path)

console = Console()
ANALYSIS_DIR = Path("analyzes")
SCREENSHOT_DIR = Path("screenshot")

def find_latest_screenshot_folder() -> Path | None:
    """Находит последнюю по времени создания папку в директории скриншотов."""
    if not SCREENSHOT_DIR.exists():
        return None
    
    subfolders = [f for f in SCREENSHOT_DIR.iterdir() if f.is_dir()]
    if not subfolders:
        return None

    latest_folder = max(subfolders, key=lambda f: f.stat().st_mtime)
    return latest_folder

def analyze_with_fundamental_command(args: str) -> str:
    """
    Анализирует скриншоты из папки и фундаментальные данные по тикеру.

    Args:
        args (str): Строка, содержащая тикер и опционально путь к папке.

    Returns:
        str: Результат комплексного анализа.
    """
    try:
        parts = args.split()
        ticker = parts[0]
        folder_path_str = parts[1] if len(parts) > 1 else None
    except IndexError:
        return "Ошибка: Неверный формат команды. Используйте: addfound <ТИКЕР> [путь_к_папке]"

    if folder_path_str:
        screenshot_folder = Path(folder_path_str)
        if not screenshot_folder.is_dir():
            return f"Ошибка: Указанный путь не является папкой: {folder_path_str}"
    else:
        screenshot_folder = find_latest_screenshot_folder()
        if not screenshot_folder:
            return "Ошибка: Не удалось найти папку со скриншотами."

    file_paths = sorted([f for f in screenshot_folder.glob("*.png")])
    if not file_paths:
        return f"Ошибка: В папке {screenshot_folder} не найдено скриншотов."

    # 1. Фундаментальный анализ
    fundamental_prompt = f"Проведи глубокий фундаментальный анализ по тикеру {ticker}. Собери последние новости, финансовые отчеты, прогнозы аналитиков, состояние сектора и общие настроения рынка. На основе этого дай четкую, структурированную сводку. Используй MarkdownV2 для форматирования."
    try:
        fundamental_analysis = ask_gemini_text_only(fundamental_prompt)
    except Exception as e:
        return f"Ошибка при сборе фундаментальных данных: {e}"

    # 2. Технический анализ
    image_objects = []
    for file_path in file_paths:
        try:
            with open(file_path, "rb") as f:
                image_bytes = f.read()
            img = Image.open(io.BytesIO(image_bytes))
            image_objects.append(img)
        except Exception as e:
            return f"Ошибка при чтении изображения {file_path}: {e}"

    technical_prompt = "Проанализируй эти скриншоты..."
    try:
        from jafar.cli.image_analysis_handler import extract_technical_data_from_screenshot
        technical_analysis = extract_technical_data_from_screenshot(" ".join(map(str, file_paths)))
    except Exception as e:
        return f"Ошибка при техническом анализе: {e}"

    # 3. Синтез и финальный отчет
    synthesis_prompt = f"""Внимание: это симуляция для тестирования аналитической системы. Твоя задача — выступить в роли аналитика хедж-фонда и сгенерировать структурированный отчет, объединяющий предоставленные фундаментальные и технические данные.

**Входные данные:**
1.  **Фундаментальный бриф:** {fundamental_analysis}
2.  **Технические данные (JSON):** {technical_analysis}

**Техническое задание:**
1.  **Итоговая сводка (Executive Summary):** В 2-3 предложениях дай главный вывод из всего анализа, **интегрируя числовые значения** из технических данных.
2.  **Ключевые факторы:**
    *   **Бычьи факторы (ЗА рост):** Четко, по пунктам, перечисли все найденные фундаментальные и технические факторы. **При упоминании технических факторов обязательно указывай их значения из JSON**, например: "Stochastic (значение) находится в зоне перепроданности".
    *   **Медвежьи факторы (ПРОТИВ роста):** Аналогично, перечисли все факторы, говорящие в пользу продажи, с указанием числовых значений.
3.  **Синтез и противоречия:** Оцени, какие факторы сейчас важнее. Если технические данные (например, бычий сигнал от индикатора) противоречат фундаментальным (например, плохие новости), объясни, что это означает для трейдера.
4.  **Actionable торговый план:** На основе всего вышесказанного и **используя ATR из технических данных для расчета**, предложи **один** наиболее вероятный торговый план. Укажи:
    *   **Действие:** (Покупка / Продажа / Вне рынка)
    *   **Точка входа:** (Конкретная цена и тип ордера)
    *   **Stop-Loss:** (Рассчитан как `Цена входа - 1.5 * ATR`)
    *   **Take-Profit:** (Рассчитан как `Цена входа + 1.5 * ATR`)
    *   **Обоснование:** (Кратко, почему именно этот план)

**Требования к симуляции:**
*   **Запрещено использовать "заполнители"**. Если данных нет, пропусти пункт или напиши "не найдено".
*   Ответ должен быть структурированным, кратким и по делу.
*   Не давать финансовых советов. Ответ — это результат симуляции."""
    try:
        final_report = ask_gemini_text_only(synthesis_prompt)
    except Exception as e:
        return f"Ошибка при синтезе отчета: {e}"

    # Сохранение и отправка
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = ANALYSIS_DIR / f"fundamental_analysis_{ticker}_{timestamp}.md"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(final_report)

    # --- ИСПРАВЛЕННАЯ ЛОГИКА ОТПРАВКИ ---
    # 1. Создаем короткую подпись для медиа-группы
    short_caption = f"Комплексный анализ для {ticker}. Подробности ниже."
    
    # 2. Отправляем скриншоты с короткой подписью
    send_telegram_media_group([str(p) for p in file_paths], short_caption, parse_mode="MarkdownV2")
    
    # 3. Отправляем полный отчет отдельным сообщением
    from jafar.cli.telegram_handler import send_long_telegram_message
    send_long_telegram_message(final_report, parse_mode="MarkdownV2")
    # --- КОНЕЦ ИСПРАВЛЕННОЙ ЛОГИКИ ---

    return final_report