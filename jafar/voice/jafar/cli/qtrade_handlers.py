import os
import time
from pathlib import Path
from datetime import datetime
from rich.console import Console
from PIL import Image
import io
import sys
import re
import json
import shlex
from jafar.utils.gemini_api import ask_gemini_with_image, ask_gemini_text_only
from jafar.utils.news_api import get_news
from jafar.cli.telegram_handler import send_telegram_media_group, send_long_telegram_message
from jafar.cli.economic_calendar_fetcher import fetch_and_save_economic_calendar_data

console = Console()
SCREENSHOT_DIR = Path("screenshot")

# --- КОНСТАНТЫ И УТИЛИТЫ ---
DEPOSIT = 2000.0
MAX_RISK_PERCENT_DEFAULT = 0.02
MAX_RISK_GROUP_A = 450.0
WINNING_DAY_TARGET_USD = 150.0
MAX_CONTRACTS = 5
CONTRACT_MULTIPLIERS = {
    "/GC": 100.0, "/MGC": 10.0, "EURUSD": 100000.0, "GBPUSD": 100000.0,
    "USDJPY": 100000.0, "SPX500": 50.0,
}

def calculate_trade_metrics(entry_price, stop_loss, take_profit, contract_multiplier, max_risk_for_trade):
    # ... (эта функция остается без изменений)
    risk_per_unit = abs(entry_price - stop_loss)
    if risk_per_unit == 0: return {"error": "Risk per unit is zero."}
    risk_per_contract = risk_per_unit * contract_multiplier
    if risk_per_contract == 0: return {"error": "Risk per contract is zero."}
    calculated_position_size = max_risk_for_trade / risk_per_contract
    position_size = min(calculated_position_size, MAX_CONTRACTS)
    if position_size < 0.01: return {"error": f"Calculated position size ({position_size:.2f}) is too small."}
    profit_per_unit = abs(take_profit - entry_price)
    total_risk_usd = position_size * risk_per_contract
    total_profit_usd = position_size * profit_per_unit * contract_multiplier
    risk_reward_ratio = total_profit_usd / total_risk_usd if total_risk_usd > 0 else float("inf")
    return {
        "position_size": round(position_size, 2), "total_risk_usd": round(total_risk_usd, 2),
        "total_profit_usd": round(total_profit_usd, 2), "risk_reward_ratio": round(risk_reward_ratio, 2),
        "meets_winning_day_target": total_profit_usd >= WINNING_DAY_TARGET_USD,
    }

# --- НОВОЕ ЯДРО АНАЛИЗА ("API") ---
def run_qtrade_analysis(instrument_query: str, screenshot_files: list[str]) -> str:
    """
    Выполняет полный "супер-анализ" на основе предоставленных данных.
    Эта функция неинтерактивна и предназначена для вызова из других модулей.
    """
    console.print(f"[blue]Загрузка новостей для '{instrument_query}'...[/blue]")
    try:
        news_data = get_news(symbols=instrument_query)
        news_results = "\n".join([f"- {item.get('title')}" for item in news_data.get("results", [])]) or "Свежих новостей не найдено."
    except Exception as e:
        news_results = f"Ошибка при загрузке новостей: {e}"
    console.print("[green]Новости загружены.[/green]")

    console.print("[blue]Загрузка экономического календаря...[/blue]")
    fetch_and_save_economic_calendar_data()
    calendar_path = Path(__file__).parent.parent.parent / "temp" / "economic_calendar_data.txt"
    economic_calendar_data = calendar_path.read_text(encoding="utf-8") if calendar_path.exists() else ""
    console.print("[green]Экономический календарь загружен.[/green]")

    console.print("\n[bold blue]Запускаю супер-комплексный анализ...[/bold blue]")
    prompt = f"""Симуляция. Роль: интрадей-трейдер. Задача: разработать торговый план на 2-4 часа.
    Входные данные: 3 скриншота, новости, экономический календарь.
    Новости: ```{news_results}```
    Календарь: ```{economic_calendar_data}```
    Задание:
    1. Проанализируй все 3 источника, определи тренд, точку входа, ATR.
    2. Оцени уверенность в прогнозе (A, B, C).
    3. Сформулируй торговый план (Действие, Вход, Stop-Loss, Take-Profit, Обоснование).
    4. Включи в конце ответа JSON со значениями: {{"entry_price": ..., "stop_loss": ..., "take_profit": ..., "atr_value": ..., "instrument": "...", "contract_multiplier": ..., "forecast_strength": "..."}}
    """
    try:
        image_objects = [Image.open(p) for p in screenshot_files]
        analysis_result = ask_gemini_with_image(prompt, image_objects)
        
        # ... (логика парсинга JSON и расчета метрик) ...
        
        send_telegram_media_group(screenshot_files, "Супер-комплексный анализ.", parse_mode="MarkdownV2")
        send_long_telegram_message(analysis_result, parse_mode="MarkdownV2")

        return analysis_result
    except Exception as e:
        error_msg = f"Произошла ошибка при анализе: {e}"
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

# --- СТАРЫЙ ОБРАБОТЧИК КОМАНД (ТЕПЕРЬ ИСПОЛЬЗУЕТ "API") ---
def qtrade_command(args: str = None):
    """Интерактивная оболочка для запуска супер-анализа."""
    
    screenshot_files = []
    instrument_query = None

    if args:
        parts = shlex.split(args)
        instrument_query = parts[0]
    
    if not instrument_query:
        instrument_query = console.input("[bold yellow]Введите тикер: [/bold yellow]")

    if not instrument_query:
        console.print("[red]Тикер не введен. Анализ невозможен.[/red]"); return

    console.print("[yellow]Запускаю интерактивный режим создания скриншотов...[/yellow]")
    timestamp_folder = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_QTrade_CLI")
    current_batch_dir = SCREENSHOT_DIR / timestamp_folder
    current_batch_dir.mkdir(parents=True, exist_ok=True)
    for i in range(3):
        console.print(f"\n[cyan]Готовьтесь к скриншоту #{i + 1}/3 (5 сек)...[/cyan]")
        time.sleep(5)
        path = current_batch_dir / f"screenshot_{i + 1}.png"
        os.system(f'screencapture -w "{str(path)}"')
        if not path.exists() or path.stat().st_size == 0:
            console.print("[red]Создание скриншота отменено.[/red]"); return
        console.print(f"[green]Скриншот #{i + 1} сохранен.[/green]")
        screenshot_files.append(str(path))

    if len(screenshot_files) == 3:
        # Вызываем новое ядро анализа
        return run_qtrade_analysis(instrument_query, screenshot_files)
    else:
        msg = "Не удалось получить 3 скриншота."
        console.print(f"[red]{msg}[/red]")
        return msg
