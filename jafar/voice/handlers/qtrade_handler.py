import os
import time
import re
import json
from pathlib import Path
from datetime import datetime
from PIL import Image

# Обновленные импорты
from src.utils.news_api import get_news
from src.utils.economic_calendar_fetcher import fetch_economic_calendar_data

# --- КОНСТАНТЫ ---
SCREENSHOT_DIR = Path.home() / "Desktop" / "jafar_screenshots"
MAX_CONTRACTS = 5
CONTRACT_MULTIPLIERS = {
    "GOLD": 100.0, "GC": 100.0, "MGC": 10.0, "ЗОЛОТО": 100.0,
    "EURUSD": 100000.0, "GBPUSD": 100000.0, "USDJPY": 100000.0, 
    "SPX500": 50.0, "ЭСЭМПИ500": 50.0,
    "NQ": 20.0, "НАСДАК": 20.0,
}
INSTRUMENT_TO_TICKER = {
    "ЗОЛОТО": "GC",
    "ЭСЭМПИ500": "SPX",
    "НАСДАК": "NQ",
}

# --- 1. СБОР ДАННЫХ ---

def capture_screenshots_by_window(speak_func) -> list[str]:
    """
    Управляет процессом создания 3 скриншотов путем выбора окна.
    """
    screenshot_files = []
    timestamp_folder = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_QTrade_Voice")
    current_batch_dir = SCREENSHOT_DIR / timestamp_folder
    current_batch_dir.mkdir(parents=True, exist_ok=True)

    speak_func("Приготовьтесь к созданию трех скриншотов. Вам нужно будет выбрать окно для каждого снимка.")
    
    for i in range(3):
        speak_func(f"Готовлюсь к снимку номер {i + 1}. Пожалуйста, выберите окно.")
        time.sleep(2)

        path = current_batch_dir / f"screenshot_{i + 1}.png"
        os.system(f'screencapture -w "{str(path)}"') 
        
        if not path.exists() or path.stat().st_size == 0:
            speak_func("Создание скриншота отменено. Прерываю анализ.")
            return []
            
        speak_func(f"Скриншот {i + 1} сохранен.")
        screenshot_files.append(str(path))
        time.sleep(2)

    return screenshot_files

# --- 2. АНАЛИЗ И РАСЧЕТЫ ---

def run_qtrade_analysis(instrument_query: str, screenshot_files: list[str], gemini_multimodal_func) -> tuple[str, str]:
    """
    Выполняет полный "супер-анализ" и возвращает (полный_текст, голосовая_сводка).
    """
    print(f"Запуск 'atrade' анализа для '{instrument_query}'...")
    
    # --- Улучшенная логика получения новостей ---
    news_keywords = []
    ticker_for_news = instrument_query # По умолчанию используем сам инструмент
    
    if "ЗОЛОТО" in instrument_query.upper() or "GC" in instrument_query.upper():
        news_keywords = ["Fed", "inflation", "interest rate", "geopolitics", "dollar", "treasury yields"]
        ticker_for_news = "" # Очищаем тикер, чтобы искать только по ключевым словам
        print(f"Используются ключевые слова для золота: {', '.join(news_keywords)}")

    try:
        news_data = get_news(symbols=ticker_for_news, keywords=news_keywords)
        news_results = "\n".join([f"- {item.get('title')}" for item in news_data.get("results", [])]) or "Свежих новостей не найдено."
    except Exception as e:
        news_results = f"Ошибка при загрузке новостей: {e}"
    print("Новости загружены.")

    # --- Получение свежих данных календаря ---
    economic_calendar_data = fetch_economic_calendar_data()
    print("Экономический календарь загружен.")

    # --- Расширенный промпт из atrade ---
    prompt = f"""Симуляция. Роль: опытный интрадей-трейдер. Задача: разработать детальный и гибкий торговый план на 2-4 часа.
    Входные данные: 3 скриншота, новости, экономический календарь.
    Новости: ```{news_results}```
    Календарь: ```{economic_calendar_data}```

    **ЗАДАНИЕ:**
    1.  **Общий Анализ:** Проанализируй все 3 источника, определи основной тренд, сентимент и ключевые уровни. Оцени уверенность в прогнозе (A, B, C).
    2.  **Основной План (План А):** Сформулируй основной торговый план: **Действие**, **Точка Входа**, **Stop-Loss**.
    3.  **Управление Позицией:**
        *   **Цели (Take-Profit):** Определи две цели: **TP1** и **TP2**.
        *   **Добавление к позиции:** Укажи цену для безопасного добавления объема.
        *   **Усреднение:** Если тактически оправдано, укажи цену для усреднения. Если нет — укажи, что не рекомендуется.
    4.  **Альтернативный Сценарий (План Б):** Опиши план действий, если цена пойдет к другому важному уровню.
    5.  **Голосовая Сводка:** Сгенерируй очень краткую сводку (2-3 предложения) для озвучивания, включив **основной план (План А)**.
    6.  **JSON Вывод:** Включи в самый конец ответа JSON со всеми числовыми значениями.

    **ПРИМЕР JSON ВЫВОДА:**
    ```json
    {{
      "forecast_strength": "B",
      "primary_entry": 2350.5,
      "alternative_entry": 2340.0,
      "stop_loss": 2335.0,
      "take_profits": {{"tp1": 2365.0, "tp2": 2380.0}},
      "scaling_in": {{"add_at_price": 2358.0}},
      "averaging_down": {{"add_at_price": 2342.0}},
      "voice_summary": "Бычий сентимент. План А: покупка от 2350.5, стоп-лосс 2335. Цели: 2365 и 2380."
    }}
    ```
    """
    
    try:
        print("Отправка данных в Gemini...")
        image_objects = [Image.open(p) for p in screenshot_files]
        analysis_result = gemini_multimodal_func(prompt, image_objects)
        
        # --- Извлечение JSON и голосовой сводки ---
        json_string = None
        voice_summary = "Анализ завершен, но не удалось извлечь голосовую сводку."
        
        json_match = re.search(r'```json\n({.*?})\n```', analysis_result, re.DOTALL)
        if not json_match:
            json_match = re.search(r'({.*?})', analysis_result, re.DOTALL)

        if json_match:
            json_string = json_match.group(1)
            trade_data = json.loads(json_string)
            voice_summary = trade_data.get("voice_summary", voice_summary)
        
        # Возвращаем полный текст для вывода в консоль и краткую сводку для озвучивания
        return analysis_result, voice_summary

    except Exception as e:
        error_msg = f"Произошла критическая ошибка при анализе: {e}"
        print(error_msg)
        return error_msg, "При анализе произошла ошибка."

# --- 3. ТОЧКА ВХОДА ---

def _determine_instrument(user_text: str, speak_func) -> tuple[str | None, str | None]:
    """Определяет инструмент из текста пользователя."""
    match = re.search(r'(полный\s+анализ|анализ)\s*(.*)', user_text, re.IGNORECASE)
    if not match:
        return None, "Не удалось обработать команду анализа."

    instrument_query = match.group(2).strip().upper()
    instrument_query = re.sub(r'[^\w\s]+$', '', instrument_query).strip()

    if not instrument_query:
        speak_func("Тикер не указан. Выполняю анализ для инструмента по умолчанию: Золото.")
        return "ЗОЛОТО", None

    # Нормализация
    if "ЗОЛОТ" in instrument_query or "ГОЛД" in instrument_query:
        key = "ЗОЛОТО"
    elif "ЭСЭМПИ" in instrument_query or "SPX" in instrument_query:
        key = "ЭСЭМПИ500"
    elif "НАСДАК" in instrument_query or "NQ" in instrument_query:
        key = "НАСДАК"
    else:
        key = instrument_query

    if key in CONTRACT_MULTIPLIERS:
        return key, None
    else:
        return None, f"Не удалось распознать инструмент '{instrument_query}'. Попробуйте, например, 'анализ золото'."


