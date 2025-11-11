import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.environ.get("MARKETAUX_API_TOKEN")
API_URL = "https://api.marketaux.com/v1/news/all"

def get_news(symbols: str, limit: int = 10, keywords: list[str] = None) -> dict:
    """Fetches news for a given symbol using the MarketAux API, with optional keyword filtering."""
    print(f"--- [DEBUG] news_api.py: API_TOKEN: {API_TOKEN[:5]}... (проверка)") # Отладка
    if not API_TOKEN:
        return {"error": "MARKETAUX_API_TOKEN not found in .env file."}

    params = {
        "api_token": API_TOKEN,
        "symbols": symbols,
        "limit": limit,
        "language": "en",
    }

    if keywords:
        # MarketAux uses a comma-separated string for multiple keywords
        params["search"] = ",".join(keywords)

    print(f"--- [DEBUG] news_api.py: Запрос к API с параметрами: {params}") # Отладка

    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        print(f"--- [DEBUG] news_api.py: Ответ от API получен, {len(data.get('data', []))} новостей.") # Отладка
        return {
            "results": [
                {"title": item.get("title"), "url": item.get("url"), "snippet": item.get("snippet")}
                for item in data.get("data", [])
            ]
        }
    except requests.exceptions.RequestException as e:
        print(f"--- [DEBUG] news_api.py: Ошибка запроса: {e}") # Отладка
        return {"error": f"Failed to fetch news: {e}", "results": []}
