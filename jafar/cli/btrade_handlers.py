import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from rich.console import Console
from rich import print_json
from PIL import Image
import io
import sys
import re
import json
import shlex
import concurrent.futures
from typing import Optional

from jafar.utils.gemini_api import ask_gemini_with_image, ask_gemini_text_only
from jafar.utils.news_api import get_unified_news, get_news_from_newsapi
from jafar.utils.topstepx_api_client import TopstepXClient
from .telegram_handler import send_telegram_media_group, send_long_telegram_message
from .economic_calendar_fetcher import fetch_economic_calendar_data
from jafar.utils.market_utils import get_current_trading_session
from .muxlisa_voice_output_handler import speak_muxlisa_text

console = Console()
SCREENSHOT_DIR = Path("screenshot")
ATRADE_LOG_PATH = Path("/Users/macbook/projects/jr/jafar_unified/memory/atrade_analysis_log.md")

def _log_atrade_summary(instrument: str, analysis_data: dict):
    pass

DEPOSIT = 2000.0
MAX_RISK_PERCENT_DEFAULT = 0.02
MAX_RISK_GROUP_A = 450.0
WINNING_DAY_TARGET_USD = 150.0
MAX_CONTRACTS_MAP = {
    "MGC": 50, "GC": 5, "CL": 10, "ES": 10,
}
CONTRACT_MULTIPLIERS = {
    "GC": 100.0, "MGC": 10.0, "EURUSD": 100000.0, "GBPUSD": 100000.0,
    "USDJPY": 100000.0, "SPX500": 50.0,
}

def calculate_trade_metrics(entry_price, stop_loss, take_profit, contract_multiplier, max_risk_for_trade, contract_symbol: str):
    risk_per_unit = abs(entry_price - stop_loss)
    if risk_per_unit == 0: return {"error": "Risk per unit is zero."}
    risk_per_contract = risk_per_unit * contract_multiplier
    if risk_per_contract == 0: return {"error": "Risk per contract is zero."}
    max_contracts_for_instrument = MAX_CONTRACTS_MAP.get(contract_symbol, 1)
    calculated_position_size = max_risk_for_trade / risk_per_contract
    position_size = min(calculated_position_size, max_contracts_for_instrument)
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

def get_formatted_topstepx_data(instrument_query: str, contract_id: str) -> tuple[str, dict, dict, list, dict]:
    try:
        client = TopstepXClient()
        accounts_response = client.get_account_list()
        if not accounts_response or not accounts_response.get("accounts"):
            return "  - Ошибка: Не удалось получить список счетов из TopstepX.", None, None, None, None
        
        all_accounts = accounts_response["accounts"]
        primary_account = next((acc for acc in all_accounts if acc.get("name") == os.environ.get("TOPSTEPX_ACCOUNT_NAME")), all_accounts[0])
        account_id = primary_account["id"]
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=8)
            future_positions = executor.submit(client.get_open_positions, account_id)
            future_orders = executor.submit(client.get_orders, account_id, start_time, end_time)
            future_trades = executor.submit(client.get_trades, account_id, start_time, end_time)
            future_bars = executor.submit(client.get_historical_bars, contract_id, end_time - timedelta(minutes=30), end_time, unit=2, unit_number=5, limit=6)
            
            open_positions = future_positions.result()
            orders = future_orders.result()
            trades = future_trades.result()
            bars_response = future_bars.result()

        status_lines = [f"**ҲИСОБ ҲОЛАТИ (API):**", f"- **Баланс:** ${primary_account.get('balance', 0.0):,.2f}"]
        
        actual_open_positions = {}
        if open_positions and open_positions.get("positions"):
            status_lines.append(f"- **Очиқ Позициялар (API):**")
            for pos in open_positions["positions"]:
                contract = pos.get("contractId")
                size = pos.get("size", 0)
                side = pos.get("side", 0)
                actual_size = size if side == 0 else -size
                actual_open_positions[contract] = actual_size
                status_lines.append(f"  - {contract}: {'Long' if actual_size > 0 else 'Short'} {abs(actual_size)}")
        else:
            status_lines.append("- **Очиқ Позициялар:** Йўқ")

        active_orders = [o for o in orders.get("orders", []) if o.get("status") in [0, 1]] if orders else []
        if active_orders:
            status_lines.append(f"- **Актив Ордерлар:** {len(active_orders)} та")
        else:
            status_lines.append("- **Актив Ордерлар:** Йўқ")

        if bars_response and bars_response.get("bars"):
            status_lines.append("\n**БОЗОР МАЪЛУМОТЛАРИ (API):**")
            status_lines.append(f"- **Охирги 5-дақиқалик свечалар ({contract_id}):**")
            for bar in bars_response["bars"]:
                ts = datetime.fromisoformat(bar['t'].replace('Z', '+00:00')).strftime('%H:%M')
                status_lines.append(f"  - {ts} | O: {bar['o']}, H: {bar['h']}, L: {bar['l']}, C: {bar['c']}")
        
        return "\n".join(status_lines), primary_account, open_positions, active_orders, actual_open_positions

    except Exception as e:
        return f"  - Ошибка: {e}", None, None, None, None

def _get_sentiment_from_data(data_type: str, data_content: str, instrument: str) -> str:
    return "Neutral"

def _log_market_sentiment(instrument: str, news_sentiment: str, calendar_sentiment: str):
    pass

def handle_order_result(order_result):
    if order_result and order_result.get("success"):
        console.print("[bold green]✅ Ордер муваффақиятли жойлаштирилди![/bold green]")
    else:
        console.print("[bold red]❌ Ордер жойлаштиришда хатолик юз берди.[/bold red]")
    if order_result:
        print_json(data=order_result)

def run_btrade_analysis(instrument_query: str, contract_symbol: str, screenshot_files: list[str]) -> dict:
    client = TopstepXClient()
    try:
        contract_info = client.search_contract(name=contract_symbol)
        active_contract = next((c for c in contract_info["contracts"] if c.get("activeContract")), None)
        if not active_contract: return {"status": "Ошибка", "full_analysis": f"Ошибка: Не найдено активных контрактов для символа '{contract_symbol}'."}
        full_contract_id = active_contract.get("id")
        tick_size = active_contract.get("tickSize")
    except Exception as e:
        return {"status": "Ошибка", "full_analysis": f"Ошибка при поиске контракта: {e}"}

    topstepx_data, primary_account, open_positions, active_orders, open_calculated_positions = get_formatted_topstepx_data(instrument_query, full_contract_id)
    if not primary_account:
        return {"status": "Ошибка", "full_analysis": "Ошибка: Не удалось получить данные об аккаунте для расчета рисков."}

    current_position_size = open_calculated_positions.get(full_contract_id, 0)
    image_objects = [Image.open(p) for p in screenshot_files]
    analysis_data = None

    current_session = get_current_trading_session()
    console.print(f"[bold magenta]Текущая сессия:[/bold magenta] {current_session}")

    if current_position_size != 0:
        position_side = "Long" if current_position_size > 0 else "Short"
        console.print(f"\n[bold yellow]Обнаружена открытая позиция: {position_side} {abs(current_position_size)} {instrument_query}. Запускаю анализ для управления...[/bold yellow]")
        
        console.print(f"\n[blue]Загрузка новостей из всех источников...[/blue]")
        news_results = ""
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_marketaux = executor.submit(get_unified_news)
            future_newsapi = executor.submit(get_news_from_newsapi)
            marketaux_news = future_marketaux.result()
            newsapi_news = future_newsapi.result()

        news_results = f"**Новости от Marketaux:**\n{marketaux_news}\n\n**Новости от Bloomberg/Reuters (via NewsAPI):\n{newsapi_news}"
        
        news_log_path = Path("/Users/macbook/projects/jr/jafar_unified/memory/btrade_last_news.txt")
        try:
            with news_log_path.open("w", encoding="utf-8") as f: f.write(news_results)
            console.print(f"\n[bold green]--- Полученные Новости (сохранено в {news_log_path}) ---[/bold green]")
            console.print(news_results)
        except Exception as e:
            console.print(f"[red]Ошибка сохранения новостей: {e}[/red]")

        economic_calendar_data = fetch_economic_calendar_data()
        news_sentiment = _get_sentiment_from_data("Новости", news_results, instrument_query)
        calendar_sentiment = _get_sentiment_from_data("Экономический календарь", economic_calendar_data, instrument_query)
        _log_market_sentiment(instrument_query, news_sentiment, calendar_sentiment)

        prompt = f'''
        **РЕЖИМ: УПРАВЛЕНИЕ ОТКРЫТОЙ ПОЗИЦИЕЙ**
        Instrument: {instrument_query}. My position: {position_side} {abs(current_position_size)}.
        **Текущая торговая сессия:** {current_session}
        **PRE-ANALYZED SENTIMENTS:**
        - News Sentiment: {news_sentiment}
        - Calendar Sentiment: {calendar_sentiment}
        **LATEST DATA:**
        - Account & Market Data: ```{topstepx_data}```
        - News: ```{news_results}```
        - Calendar: ```{economic_calendar_data}```
        **TASK:**
        1.  **Filter News:** First, critically evaluate the relevance of each news item provided. **Completely ignore any news not directly related to financial markets (e.g., celebrity, sports, social news).** Prioritize the most recent and impactful news.
        2.  **Analyze:** Based on the RELEVANT news and all other data, analyze my current position.
        3.  **Recommend Action:** MUST be one of: "HOLD", "CLOSE", "MODIFY_SL_TP".
        4.  **Provide Data:** If "MODIFY_SL_TP", provide `new_stop_loss` and `new_take_profit`.
        **OUTPUT FORMAT (STRICTLY JSON):**
        ```json
        {{
          "full_analysis_uzbek_cyrillic": "...",
          "management_data": {{"action": "HOLD" or "CLOSE" or "MODIFY_SL_TP", "new_stop_loss": 0.0, "new_take_profit": 0.0}},
          "voice_summary_uzbek_cyrillic": "..."
        }}
        ```
        '''
        raw_response = ask_gemini_with_image(prompt, image_objects)
        json_match = re.search(r'```json\n(.*?)\n```', raw_response, re.DOTALL) or re.search(r'({.*?})', raw_response, re.DOTALL)
        if not json_match: return {"status": "Ошибка", "full_analysis": f"Ошибка: Ответ Gemini не в формате JSON: {raw_response}"}
        analysis_data = json.loads(json_match.group(1))
        management_data = analysis_data.get("management_data")
        if not management_data: return {"status": "Ошибка", "full_analysis": "Gemini не предоставил 'management_data'."}
        action = management_data.get("action", "").upper()
        console.print(f"\n[bold green]--- РЕКОМЕНДАЦИЯ GEMINI: {action} ---[/bold green]")
        print_json(data=management_data)
        if action == "CLOSE":
            confirmation = console.input("[bold yellow]Закрыть позицию? (да/нет): [/bold yellow]").lower()
            if confirmation in ["да", "ха", "yes", "1"]:
                close_result = client.place_order(contract_id=full_contract_id, account_id=primary_account["id"], side=1 if current_position_size > 0 else 0, order_type=2, size=int(abs(current_position_size)), tick_size=tick_size)
                handle_order_result(close_result)
        elif action == "MODIFY_SL_TP":
            new_sl = management_data.get("new_stop_loss")
            new_tp = management_data.get("new_take_profit")
            all_orders = client.get_orders(primary_account["id"], datetime.utcnow() - timedelta(hours=24), datetime.utcnow()).get("orders", [])
            sl_order = next((o for o in all_orders if o.get("contractId") == full_contract_id and o.get("type") == 4 and o.get("status") == 1), None)
            tp_order = next((o for o in all_orders if o.get("contractId") == full_contract_id and o.get("type") == 1 and o.get("status") == 1), None)
            if sl_order: client.modify_order(account_id=primary_account["id"], order_id=sl_order['id'], stop_price=new_sl)
            if tp_order: client.modify_order(account_id=primary_account["id"], order_id=tp_order['id'], limit_price=new_tp)
        
        return {"status": "Успех", "full_analysis": analysis_data.get("full_analysis_uzbek_cyrillic", "Анализ не предоставлен."), "voice_summary": analysis_data.get("voice_summary_uzbek_cyrillic")}
    else:
        # --- РЕЖИМ 1: ПОИСК НОВОЙ СДЕЛКИ ---
        console.print(f"\n[blue]Загрузка новостей из всех источников...[/blue]")
        news_results = ""
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_marketaux = executor.submit(get_unified_news)
            future_newsapi = executor.submit(get_news_from_newsapi)
            marketaux_news = future_marketaux.result()
            newsapi_news = future_newsapi.result()

        news_results = f"**Новости от Marketaux:**\n{marketaux_news}\n\n**Новости от Bloomberg/Reuters (via NewsAPI):\n{newsapi_news}"
        
        news_log_path = Path("/Users/macbook/projects/jr/jafar_unified/memory/btrade_last_news.txt")
        try:
            with news_log_path.open("w", encoding="utf-8") as f: f.write(news_results)
            console.print(f"\n[bold green]--- Полученные Новости (сохранено в {news_log_path}) ---[/bold green]")
            console.print(news_results)
        except Exception as e:
            console.print(f"[red]Ошибка сохранения новостей: {e}[/red]")

        economic_calendar_data = fetch_economic_calendar_data()
        news_sentiment = _get_sentiment_from_data("Новости", news_results, instrument_query)
        calendar_sentiment = _get_sentiment_from_data("Экономический календарь", economic_calendar_data, instrument_query)
        _log_market_sentiment(instrument_query, news_sentiment, calendar_sentiment)
        prompt = f'''
        **РЕЖИм: ПОИСК НОВОЙ СДЕЛКИ**
        Instrument: {instrument_query}.
        **Текущая торговая сессия:** {current_session}
        **PRE-ANALYZED SENTIMENTS:**
        - News Sentiment: {news_sentiment}
        - Calendar Sentiment: {calendar_sentiment}
        **DATA:**
        - Account Data: ```{topstepx_data}```
        - News: ```{news_results}```
        - Calendar: ```{economic_calendar_data}```
        **TASK:**
        1.  **Filter News:** First, critically evaluate the relevance of each news item provided. **Completely ignore any news not directly related to financial markets (e.g., celebrity, sports, social news).** Prioritize the most recent and impactful news.
        2.  **Analysis:** Based on the RELEVANT news and all other data, determine trend, sentiment, key levels, and forecast confidence (A, B, C).
        3.  **Risk Proposal:** Based on your forecast confidence, propose a risk percentage for this trade, from 2% (low confidence) to 25% (high confidence).
        4.  **Plan A (Primary):** Formulate the primary trading plan (Action, Entry, Stop-Loss, Targets TP1/TP2).
        5.  **Translation:** Translate the complete analysis into Uzbek (Cyrillic).
        6.  **Voice Summary:** Generate a brief summary in Uzbek (Cyrillic) for the voice assistant.
        **OUTPUT FORMAT (STRICTLY JSON):**
        ```json
        {{
          "full_analysis_uzbek_cyrillic": "...",
          "trade_data": {{
            "action": "BUY",
            "forecast_strength": "B",
            "risk_percent": 5.0,
            "primary_entry": 2350.5,
            "stop_loss": 2335.0,
            "take_profits": {{
              "tp1": 2365.0,
              "tp2": 2380.0
            }}
          }},
          "voice_summary_uzbek_cyrillic": "..."
        }}
        ```
        '''
        raw_response = ask_gemini_with_image(prompt, image_objects)
        json_match = re.search(r'```json\n(.*?)\n```', raw_response, re.DOTALL) or re.search(r'({.*?})', raw_response, re.DOTALL)
        if not json_match: return {"status": "Ошибка", "full_analysis": f"Ошибка: Ответ Gemini не в формате JSON: {raw_response}"}
        
        try:
            analysis_data = json.loads(json_match.group(1))
        except json.JSONDecodeError:
            return {"status": "Ошибка", "full_analysis": f"Ошибка декодирования JSON: {json_match.group(1)}"}

        trade_data = analysis_data.get("trade_data")
        if trade_data:
            action = trade_data.get("action", "").upper()
            if action in ["BUY", "SELL"] and trade_data.get("primary_entry"):
                risk_percent = float(trade_data.get("risk_percent", 3.0))
                console.print(f"[bold cyan]Gemini предлагает риск: {risk_percent}%[/bold cyan]")
                entry_price = float(trade_data["primary_entry"])
                stop_loss = float(trade_data["stop_loss"])
                take_profit = float(trade_data["take_profits"]["tp1"])
                balance = primary_account.get("balance", 0.0)
                max_risk_for_trade = balance * (risk_percent / 100.0)
                contract_multiplier = active_contract.get("tickValue") / active_contract.get("tickSize")
                metrics = calculate_trade_metrics(entry_price, stop_loss, take_profit, contract_multiplier, max_risk_for_trade, contract_symbol)
                
                if "error" in metrics:
                    console.print(f"[red]Ошибка расчета метрик: {metrics['error']}[/red]")
                    position_size = 1
                else:
                    position_size = metrics.get("position_size", 1)
                    console.print("\n[bold cyan]--- Управление Рисками ---[/bold cyan]")
                    print_json(data=metrics)

                console.print(f"\n[bold yellow]АВТОМАТИЧЕСКОЕ РАЗМЕЩЕНИЕ ОРДЕРА: {action} {int(position_size)} {contract_symbol} @ {entry_price}[/bold yellow]")
                order_result = client.place_order(
                    contract_id=full_contract_id, account_id=primary_account["id"],
                    side=0 if action == "BUY" else 1, order_type=0, size=int(position_size),
                    limit_price=entry_price, stop_loss=stop_loss, take_profit=take_profit, tick_size=tick_size
                )
                handle_order_result(order_result)

        full_analysis_text = analysis_data.get("full_analysis_uzbek_cyrillic", "Анализ не предоставлен.")
        send_long_telegram_message(f"BTRADE АНАЛИЗ (Новая сделка) ({instrument_query}):\n\n{full_analysis_text}")
        
        return {"status": "Успех", "full_analysis": full_analysis_text, "voice_summary": analysis_data.get("voice_summary_uzbek_cyrillic")}

def btrade_command(args: str = None):
    instrument_map = {
        "gold": "MGC", "mgc": "MGC", "oltin": "MGC", "zoloto": "MGC", "gc": "GC",
        "oil": "CL", "cl": "CL", "neft": "CL", "s&p": "ES", "es": "ES",
    }
    instrument_query = None
    if args:
        try:
            instrument_query = shlex.split(args)[0].lower()
        except (IndexError, ValueError):
            console.print("[red]Неверный формат аргумента.[/red]"); return
    if not instrument_query:
        instrument_query = console.input("[bold yellow]Инструмент (например, gold): [/bold yellow]").lower()
    if not instrument_query:
        console.print("[red]Инструмент не указан.[/red]"); return
    contract_symbol = instrument_map.get(instrument_query)
    if not contract_symbol:
        console.print(f"[red]Тикер для '{instrument_query}' не найден.[/red]"); return

    console.print(f"[cyan]Анализ для: {instrument_query.capitalize()} ({contract_symbol})[/cyan]")
    console.print("[yellow]Режим интерактивных скриншотов...[/yellow]")
    screenshot_files = []
    current_batch_dir = SCREENSHOT_DIR / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    current_batch_dir.mkdir(parents=True, exist_ok=True)
    for i in range(3):
        console.print(f"\nСкриншот #{i + 1}/3 через 3 секунды...")
        time.sleep(3)
        path = current_batch_dir / f"screenshot_{i + 1}.png"
        os.system(f'screencapture -w "{str(path)}"')
        if path.exists() and path.stat().st_size > 0:
            console.print(f"Скриншот #{i + 1} сохранен.")
            screenshot_files.append(str(path))
        else:
            console.print("[red]Скриншот не сделан. Анализ отменен.[/red]"); return

    if len(screenshot_files) == 3:
        analysis_result = run_btrade_analysis(instrument_query, contract_symbol, screenshot_files)
        if isinstance(analysis_result, dict) and analysis_result.get("status") == "Успех":
            console.print(f"\n[bold green]--- Полный Анализ ---[/bold green]\n{analysis_result.get('full_analysis', 'Текст анализа отсутствует.')}")
            voice_summary = analysis_result.get("voice_summary")
            if voice_summary:
                speak_muxlisa_text(voice_summary)
        else:
            console.print(f"\n[bold red]--- Ошибка Анализа ---[/bold red]\n{analysis_result.get('full_analysis', 'Неизвестная ошибка.')}")
    else:
        console.print("[red]Не удалось сделать 3 скриншота.[/red]")