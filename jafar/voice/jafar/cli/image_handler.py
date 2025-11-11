from pathlib import Path
from PIL import Image
import pytesseract

def process_image_for_prompt(image_path):
    """
    Выполняет OCR над изображением и формирует промпт для ассистента.
    :param image_path: путь к файлу изображения
    :return: строка-подсказка для генерации backend формы
    """
    path = Path(image_path)
    if not path.is_file():
        return f"Файл не найден: {image_path}"
    try:
        with Image.open(path) as img:
            text = pytesseract.image_to_string(img, lang="eng+rus")
        text = text.strip()
        if not text:
            text = "[Текст не обнаружен]"
        summary = (
            f"На изображении видим следующий текст/элементы:\n"
            f"{text}\n\n"
            f"Сгенерируй backend для этой формы."
        )
        return summary
    except Exception as e:
        return f"Ошибка OCR: {e}. Проверь файл и попробуй снова или обработай вручную."