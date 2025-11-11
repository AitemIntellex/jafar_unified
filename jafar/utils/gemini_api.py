import base64
import io
import os

import google.generativeai as genai
from PIL import Image


def ask_gemini_with_image(prompt: str, images: list[Image.Image]) -> str:
    """
    Отправляет список изображений и текстовый запрос в Gemini API для анализа.

    Args:
        prompt (str): Текстовый запрос для Gemini.
        images (list[Image.Image]): Список объектов PIL.Image.

    Returns:
        str: Результат анализа от Gemini.
    """
    # Получаем API ключ из переменных окружения
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "Ошибка: GOOGLE_API_KEY не установлен в переменных окружения."

    genai.configure(api_key=api_key)

    # Выбираем модель, которая поддерживает работу с изображениями
    model = genai.GenerativeModel("gemini-2.5-pro")

    try:
        # Создаем список содержимого для отправки: сначала изображения, затем промпт
        contents = [*images, prompt]
        response = model.generate_content(contents)
        return response.text
    except Exception as e:
        return f"Ошибка при обращении к Gemini API: {e}"


def ask_gemini_text_only(prompt: str) -> str:
    """
    Отправляет текстовый запрос в Gemini API.

    Args:
        prompt (str): Текстовый запрос для Gemini.

    Returns:
        str: Результат от Gemini.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "Ошибка: GOOGLE_API_KEY не установлен в переменных окружения."

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-pro")

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Ошибка при обращении к Gemini API: {e}"