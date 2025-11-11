import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.environ.get("MARKETAUX_API_TOKEN")
API_URL = "https://api.marketaux.com/v1/news/all"

def get_news(symbols: str, limit: int = 5, keywords: list[str] = None) -> dict:
    """Fetches news for a given symbol using the MarketAux API, with optional keyword filtering."""
    if not API_TOKEN:
        return {"error": "MARKETAUX_API_TOKEN not found in .env file."}

    params = {
        "api_token": API_TOKEN,
        "symbols": symbols,
        "limit": limit,
        "language": "en",
    }

    if keywords:
        params["search"] = ",".join(keywords)

    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        # Трансформируем данные в формат, похожий на старый
        return {
            "results": [
                {"title": item.get("title"), "url": item.get("url"), "snippet": item.get("snippet")}
                for item in data.get("data", [])
            ]
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch news: {e}", "results": []}
