
import google.generativeai as genai
from PIL import Image

def ask_gemini_with_image(prompt: str, images: list[Image.Image]) -> str:
    """
    Отправляет текстовый промпт и список изображений в мультимодальную модель Gemini.
    """
    try:
        # Используем модель Pro Vision, которая специально предназначена для таких задач
        model = genai.GenerativeModel('models/gemini-2.5-pro') 
        
        # Формируем контент для запроса
        content = [prompt] + images
        
        response = model.generate_content(content)
        
        return response.text.strip()
    except Exception as e:
        print(f"Ошибка при вызове Gemini API с изображением: {e}")
        return f"Ошибка Gemini: {e}"

def ask_gemini_text_only(prompt: str) -> str:
    """
    Отправляет только текстовый промпт в модель Gemini.
    """
    try:
        model = genai.GenerativeModel('models/gemini-2.5-pro')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Ошибка при вызове Gemini API (только текст): {e}")
        return f"Ошибка Gemini: {e}"

if __name__ == '__main__':
    # Пример для тестирования (требует наличия изображения 'test.png')
    try:
        img = Image.open('test.png')
        prompt_text = "Что изображено на этой картинке?"
        result = ask_gemini_with_image(prompt_text, [img])
        print("Результат мультимодального запроса:")
        print(result)
    except FileNotFoundError:
        print("Для теста создайте файл 'test.png' в этой директории.")
    except Exception as e:
        print(f"Произошла ошибка при тестировании: {e}")
