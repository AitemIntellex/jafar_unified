from pathlib import Path
import os
import re

from src.utils.news_api import get_news
from src.utils.gemini_api import ask_gemini_text_only

# Словарь с настройками для каждого типа анализа
ANALYSIS_CONFIG = {
    "1": {"name": "Анализ рынка золота", "type": "gold", "keywords": ["gold", "XAUUSD", "Fed", "inflation", "dollar"]},
    "2": {"name": "Анализ криптовалют", "type": "crypto", "keywords": ["bitcoin", "ethereum", "crypto", "SEC", "blockchain"]},
    "3": {"name": "Анализ валютного рынка", "type": "currency", "keywords": ["forex", "EURUSD", "GBPUSD", "USDJPY", "ECB", "central bank"]},
    "4": {"name": "Анализ фьючерсов", "type": "futures", "keywords": ["futures", "commodities", "oil", "CME"]},
    "5": {"name": "Общий анализ мировых новостей", "type": "world_news", "keywords": ["geopolitics", "world economy", "market sentiment"]},
}

def _run_analysis(selected_config: dict, speak_func):
    """Загружает новости и выполняет анализ для выбранной темы."""
    speak_func(f"Выбрана тема: {selected_config['name']}. Загружаю свежие новости.")

    try:
        news_data = get_news(symbols="", keywords=selected_config["keywords"], limit=20)
        if "error" in news_data:
            return f"Ошибка при загрузке новостей: {news_data['error']}"
        
        snippets = "\n".join([f"- {item.get('title')}: {item.get('snippet', '')}" for item in news_data.get("results", [])])
        if not snippets:
            return "Не удалось найти свежие новости по данной теме."
        speak_func("Новости успешно загружены. Запускаю анализ.")
    except Exception as e:
        return f"Произошла ошибка при загрузке новостей: {e}"

    try:
        prompt_file_path = Path(__file__).parent.parent.parent.parent / "jafar" / "jafar" / "analysis" / "prompts" / f"{selected_config['type']}_news_prompt.txt"
        
        with open(prompt_file_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()

        prompt = prompt_template.format(snippets=snippets)
        full_analysis_text = ask_gemini_text_only(prompt)
        
        if not full_analysis_text:
            return "Не удалось получить ответ от AI ассистента."
            
        summary_match = re.search(r'"voice_summary":\s*"(.*?)"', full_analysis_text, re.DOTALL)
        if summary_match:
            return summary_match.group(1)
        else:
            return ". ".join(full_analysis_text.split('.')[:3])
    except Exception as e:
        return f"Произошла непредвиденная ошибка во время анализа: {e}"

def interactive_analysis_entrypoint(user_text: str, speak_func, stt_func):
    """
    Интеллектуально обрабатывает запрос на анализ новостей.
    """
    user_text_lower = user_text.lower()

    # --- Прямой анализ, если тема указана сразу ---
    for config in ANALYSIS_CONFIG.values():
        # Ищем ключевое слово темы (например, "золото", "криптовалют")
        if any(keyword in user_text_lower for keyword in config['name'].lower().split()):
            return _run_analysis(config, speak_func)

    # --- Если тема не указана, запускаем интерактивное меню ---
    speak_func("Пожалуйста, выберите тип анализа.")
    for key, config in ANALYSIS_CONFIG.items():
        speak_func(f"Вариант {key}. {config['name']}")
    speak_func("Скажите номер или название темы.")
    
    choice_text = stt_func()
    if not choice_text:
        return "Не удалось распознать ваш выбор."

    # --- Обработка выбора из меню ---
    selected_config = None
    choice_text_lower = choice_text.lower()
    
    choice_num_match = re.search(r'\d+', choice_text_lower)
    if choice_num_match and choice_num_match.group(0) in ANALYSIS_CONFIG:
        selected_config = ANALYSIS_CONFIG[choice_num_match.group(0)]
    else:
        for config in ANALYSIS_CONFIG.values():
            if any(keyword in choice_text_lower for keyword in config['name'].lower().split()):
                selected_config = config
                break

    if not selected_config:
        return "Не удалось распознать ваш выбор. Пожалуйста, попробуйте еще раз, сказав 'анализ новостей'."

    return _run_analysis(selected_config, speak_func)

