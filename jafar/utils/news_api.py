import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from newsapi import NewsApiClient

# --- Setup ---
load_dotenv()
console = None
try:
    from rich.console import Console
    console = Console()
except ImportError:
    pass

def _print(message: str):
    if console:
        console.print(message)
    else:
        print(message)

# --- API Keys ---
MARKETAUX_API_KEY = os.environ.get("MARKETAUX_API_KEY")
NEWSAPI_API_KEY = os.environ.get("NEWSAPI_API_KEY")

# --- Global Keywords for Market-Moving News ---
MARKET_MOVING_KEYWORDS = [
    'FOMC', 'Federal Reserve', 'ECB', 'Lagarde', 'Powell', 
    'inflation', 'interest rates', 'geopolitics', 'market sentiment'
]

# --- NewsAPI.org Function ---
def get_news_from_newsapi(hours_ago: int = 72, top_n: int = 10) -> str:
    """
    Fetches news from NewsAPI.org based on a predefined list of market-moving keywords.
    """
    if not NEWSAPI_API_KEY or "YOUR_NEWSAPI_API_KEY" in NEWSAPI_API_KEY:
        _print("[dim red]Ключ NewsAPI не настроен в файле .env.[/dim red]")
        return "Ключ NewsAPI не настроен."

    query = " OR ".join(f'"{keyword}"' for keyword in MARKET_MOVING_KEYWORDS)
    _print(f"[cyan]Загрузка макроэкономических новостей из NewsAPI.org...[/cyan]")
    _print(f"[dim]Поисковый запрос: {query}[/dim]")
    
    try:
        newsapi = NewsApiClient(api_key=NEWSAPI_API_KEY)
        from_date = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).strftime('%Y-%m-%dT%H:%M:%S')

        articles = newsapi.get_everything(
            q=query,
            language='en',
            sort_by='publishedAt', # Sort by newest first
            page_size=20
        )

        if not articles or not articles.get('articles'):
            _print(f"[dim yellow]NewsAPI.org: Нет статей по ключевым словам. Сырой ответ: {articles}[/dim yellow]")
            return "Новости по ключевым макроэкономическим словам не найдены."

        formatted_strings = []
        for item in articles['articles']:
            formatted_strings.append(
                f"- (NewsAPI) [{datetime.fromisoformat(item.get('publishedAt').replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')}] {item.get('title')}: {item.get('description') or 'N/A'}"
            )
        
        if not formatted_strings:
            return f"За последние {hours_ago} часов новости по ключевым словам не найдены."

        _print(f"[green]{len(formatted_strings)} актуальных макро-новостей найдено в NewsAPI.org.[/green]")
        return "\n".join(formatted_strings)

    except Exception as e:
        _print(f"[dim red]Ошибка NewsAPI: {e}[/dim red]")
        return f"Ошибка при получении новостей от NewsAPI.org: {e}"


# --- Marketaux Main Unified Function ---

def get_unified_news(hours_ago: int = 72, top_n: int = 3) -> str:
    """
    Fetches news from Marketaux API based on a predefined list of market-moving keywords.
    """
    if not MARKETAUX_API_KEY or "YOUR_MARKETAUX_API_KEY" in MARKETAUX_API_KEY:
        _print("[dim red]Ключ Marketaux API не настроен в файле .env.[/dim red]")
        return "Ключ Marketaux API не настроен."

    query = " OR ".join(f'"{keyword}"' for keyword in MARKET_MOVING_KEYWORDS)
    _print(f"[cyan]Загрузка макроэкономических новостей из Marketaux...[/cyan]")
    
    url = 'https://api.marketaux.com/v1/news/all'
    params = {
        'api_token': MARKETAUX_API_KEY,
        'search': query,
        'language': 'en',
        'limit': top_n,
    }

    _print(f"[dim]URL запроса Marketaux: {requests.Request('GET', url, params=params).prepare().url}[/dim]")

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json().get('data', [])
        
        if not data:
            _print(f"[dim yellow]Marketaux: Нет статей по ключевым словам. Сырой ответ: {response.json()}[/dim yellow]")
            return "Новости по ключевым макро-словам в Marketaux не найдены."

        # --- Format for Prompt ---
        formatted_strings = []
        for item in data:
            published_at_str = item.get('published_at')
            if not published_at_str: continue

            try:
                published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
                if published_at < datetime.now(timezone.utc) - timedelta(hours=hours_ago):
                    continue

                formatted_strings.append(
                    f"- (Marketaux) [{published_at.strftime('%Y-%m-%d %H:%M')}] {item.get('title')}: {item.get('snippet') or 'N/A'}"
                )
            except (ValueError, TypeError):
                continue
        
        if not formatted_strings:
            _print(f"[dim yellow]Marketaux: Нет отформатированных статей. Сырой ответ: {response.json()}[/dim yellow]")
            return f"За последние {hours_ago} часов в Marketaux актуальных новостей не найдено."

        _print(f"[green]{len(formatted_strings)} актуальных макро-новостей найдено в Marketaux.[/green]")
        return "\n".join(formatted_strings)

    except requests.RequestException as e:
        _print(f"[dim red]Ошибка Marketaux: {e}[/dim red]")
        if e.response:
            _print(f"[dim red]Ответ: {e.response.text}[/dim red]")
        return f"Ошибка при получении новостей от Marketaux API: {e}"