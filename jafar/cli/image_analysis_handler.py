import os
from pathlib import Path
from PIL import Image
import io
from datetime import datetime
from jafar.utils.gemini_api import ask_gemini_with_image

ANALYSIS_DIR = Path("analyzes")

def analyze_screenshot_command(file_paths: str) -> str:
    """
    Анализирует скриншоты с помощью Gemini API и записывает результат в лог.

    Args:
        file_paths (str): Строка с абсолютными путями к файлам скриншотов, разделенными пробелами.

    Returns:
        str: Результат анализа от Gemini.
    """
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
            return f"Ошибка при чтении или декодировании изображения {file_path}: {e}"

    if not image_objects:
        return "Ошибка: Не найдено изображений для анализа."

    prompt = "Проанализируй эти скриншоты торгового терминала, представленные на разных таймфреймах. Определи общий тренд, ключевые уровни поддержки/сопротивления, фигуры технического анализа, показания индикаторов (если есть) на каждом таймфрейме и их взаимосвязь. На основе этого мультитаймфреймового анализа дай краткую сводку и возможный прогноз движения цены."
    
    try:
        analysis_result = ask_gemini_with_image(prompt, image_objects)
        
        # Создаем папку, если ее нет
        ANALYSIS_DIR.mkdir(exist_ok=True)

        # Запись в Markdown-файл
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file = ANALYSIS_DIR / f"analysis_{timestamp}.md"

        log_entry = f"\n---\n## 🗓️ Анализ скриншотов от {timestamp}\n"
        log_entry += f"### 🖼️ Скриншоты:\n"
        for path in paths_list:
            log_entry += f"- `{path}`\n"
        log_entry += f"\n#### 🤖 Результат анализа:\n{analysis_result}\n"

        with open(log_file, "w", encoding="utf-8") as f:
            f.write(log_entry)

        return analysis_result

    except Exception as e:
        return f"Произошла ошибка при анализе скриншотов: {e}"
