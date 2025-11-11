
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
import os

from src.jafar.analysis.analyzer import analyze_news
from src.jafar.utils.news_api import get_news

console = Console()

# Словарь с настройками для каждого типа анализа
ANALYSIS_CONFIG = {
    "1": {
        "name": "Анализ рынка золота",
        "type": "gold",
        "keywords": ["gold", "XAUUSD", "Fed", "inflation", "dollar"],
        "analysis_dir": Path(__file__).parent.parent.parent / "analyzes" / "gold",
        "prompt_file": Path(__file__).parent.parent / "analysis" / "prompts" / "gold_news_prompt.txt",
    },
    "2": {
        "name": "Анализ криптовалют",
        "type": "crypto",
        "keywords": ["bitcoin", "ethereum", "crypto", "SEC", "blockchain"],
        "analysis_dir": Path(__file__).parent.parent.parent / "analyzes" / "crypto",
        "prompt_file": Path(__file__).parent.parent / "analysis" / "prompts" / "crypto_prompt.txt",
    },
    "3": {
        "name": "Анализ валютного рынка",
        "type": "currency",
        "keywords": ["forex", "EURUSD", "GBPUSD", "USDJPY", "ECB", "central bank"],
        "analysis_dir": Path(__file__).parent.parent.parent / "analyzes" / "currency",
        "prompt_file": Path(__file__).parent.parent / "analysis" / "prompts" / "currency_news_prompt.txt",
    },
    "4": {
        "name": "Анализ фьючерсов",
        "type": "futures",
        "keywords": ["futures", "commodities", "oil", "CME"],
        "analysis_dir": Path(__file__).parent.parent.parent / "analyzes" / "futures",
        "prompt_file": Path(__file__).parent.parent / "analysis" / "prompts" / "futures_news_prompt.txt",
    },
    "5": {
        "name": "Общий анализ мировых новостей",
        "type": "world_news",
        "keywords": ["geopolitics", "world economy", "market sentiment"],
        "analysis_dir": Path(__file__).parent.parent.parent / "analyzes" / "world_news",
        "prompt_file": Path(__file__).parent.parent / "analysis" / "prompts" / "world_news_prompt.txt",
    },
}

def start_interactive_analysis(args: str = None):
    """Запускает интерактивный режим для выбора и выполнения анализа с автоматической загрузкой новостей."""
    try:
        console.print(Panel("[bold cyan]Интерактивный Анализатор Jafar[/bold cyan]", title="🤖 Jafar"))
        console.print("Пожалуйста, выберите тип анализа:")
        for key, config in ANALYSIS_CONFIG.items():
            console.print(f"  [yellow]{key}[/yellow]. {config['name']}")
        
        choice = console.input("\n[bold]Введите номер: [/bold]")

        if choice not in ANALYSIS_CONFIG:
            console.print("[red]Неверный выбор. Пожалуйста, запустите команду 'analyze' снова.[/red]")
            return

        selected_config = ANALYSIS_CONFIG[choice]
        console.print(f"\n[blue]Выбран анализ: {selected_config['name']}[/blue]")

        # --- Автоматическая загрузка новостей ---
        console.print(f"[cyan]Загрузка свежих новостей по теме...[/cyan]")
        try:
            # Используем ключевые слова для поиска, а символы оставляем пустыми
            news_data = get_news(symbols="", keywords=selected_config["keywords"], limit=10)
            if "error" in news_data:
                console.print(f"[red]Ошибка API новостей: {news_data['error']}[/red]")
                return
            
            snippets = "\n".join([f"- {item.get('title')}: {item.get('snippet', '')}" for item in news_data.get("results", [])])
            if not snippets:
                console.print("[yellow]Не удалось найти свежие новости по данной теме.[/yellow]")
                return
            console.print("[green]✅ Новости успешно загружены.[/green]")

        except Exception as e:
            console.print(f"[red]Произошла ошибка при загрузке новостей: {e}[/red]")
            return

        # --- Запуск анализа ---
        console.print("[bold blue]Запускаю анализ...[/bold blue]")
        analysis_output = analyze_news(
            snippets=snippets,
            prompt_file=str(selected_config["prompt_file"]),
            analysis_dir=selected_config["analysis_dir"],
            analysis_type=selected_config["type"],
        )
        
        console.print(Panel(analysis_output, title="🤖 Jafar - Результат анализа", style="green"))

    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Анализ прерван пользователем.[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Произошла непредвиденная ошибка: {e}[/bold red]")
