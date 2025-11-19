import shlex
import concurrent.futures
from pathlib import Path
from rich.console import Console

from jafar.utils.news_api import get_unified_news, get_news_from_newsapi

console = Console()

def news_command(args: str = None):
    """
    Fetches news from all available sources for a given instrument and displays them.
    """
    if not args:
        instrument_query = console.input("[bold yellow]Введите инструмент для поиска новостей (например, gold): [/bold yellow]").lower()
    else:
        try:
            instrument_query = shlex.split(args)[0].lower()
        except (IndexError, ValueError):
            console.print("[red]Неверный формат аргумента.[/red]")
            return

    if not instrument_query:
        console.print("[red]Инструмент не указан.[/red]")
        return

    console.print(f"\n[bold blue]Загрузка новостей для '{instrument_query}' из всех источников...[/bold blue]")
    
    news_results = ""
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_marketaux = executor.submit(get_unified_news)
        future_newsapi = executor.submit(get_news_from_newsapi)
        
        marketaux_news = future_marketaux.result()
        newsapi_news = future_newsapi.result()

    news_results = f"**Новости от Marketaux:**\n{marketaux_news}\n\n**Новости от Bloomberg/Reuters (via NewsAPI):\n{newsapi_news}"
    
    news_log_path = Path("/Users/macbook/projects/jr/jafar_unified/memory/btrade_last_news.txt")
    try:
        with news_log_path.open("w", encoding="utf-8") as f:
            f.write(news_results)
        console.print(f"\n[bold green]--- Полученные Новости (сохранено в {news_log_path}) ---[/bold green]")
        console.print(news_results)
    except Exception as e:
        console.print(f"[red]Ошибка сохранения новостей: {e}[/red]")
