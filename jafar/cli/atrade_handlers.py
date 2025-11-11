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
from jafar.utils.gemini_api import ask_gemini_with_image, ask_gemini_text_only
from jafar.utils.news_api import get_news
from jafar.utils.topstepx_api_client import TopstepXClient
from .telegram_handler import send_telegram_media_group, send_long_telegram_message
from .economic_calendar_fetcher import fetch_economic_calendar_data
from .muxlisa_voice_output_handler import speak_muxlisa_text

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

def get_formatted_topstepx_data(instrument_query: str, contract_id: str) -> str:
    """
    Подключается к TopstepX API, реализует умный выбор счета, получает данные 
    параллельно и форматирует их в строку для промпта Gemini.
    """
    console.print("\n[blue]Загрузка данных из TopstepX API (параллельно)...[/blue]")
    try:
        client = TopstepXClient()
        
        # 1. Получаем список счетов
        accounts_response = client.get_account_list()
        if not accounts_response or not accounts_response.get("accounts"):
            return "  - Ошибка: Не удалось получить список счетов из TopstepX."
        
        all_accounts = accounts_response["accounts"]
        primary_account = None
        
        # 2. "Умный" выбор счета
        preferred_account_name = os.environ.get("TOPSTEPX_ACCOUNT_NAME")
        
        if preferred_account_name:
            for acc in all_accounts:
                if acc.get("name") == preferred_account_name:
                    primary_account = acc
                    console.print(f"[green]Используется счет из .env файла: {preferred_account_name}[/green]")
                    break
        
        if not primary_account:
            if preferred_account_name:
                console.print(f"[yellow]Счет '{preferred_account_name}', указанный в .env, не найден.[/yellow]")
            else:
                console.print("[yellow].env файле TOPSTEPX_ACCOUNT_NAME не указан.[/yellow]")

            console.print("[cyan]Пожалуйста, выберите счет для анализа:[/cyan]")
            for i, acc in enumerate(all_accounts):
                console.print(f"  [bold]{i + 1}[/bold]: {acc.get('name')} (Баланс: ${acc.get('balance', 0.0):,.2f})")
            
            while True:
                try:
                    choice = int(console.input("[bold]Введите номер счета: [/bold]"))
                    if 1 <= choice <= len(all_accounts):
                        primary_account = all_accounts[choice - 1]
                        break
                    else:
                        console.print("[red]Неверный номер. Попробуйте еще раз.[/red]")
                except ValueError:
                    console.print("[red]Пожалуйста, введите число.[/red]")

        account_id = primary_account["id"]
        
        # 3. Запускаем остальные запросы параллельно
        with concurrent.futures.ThreadPoolExecutor() as executor:
            end_time = datetime.utcnow()
            start_time_orders = end_time - timedelta(hours=8)
            start_time_bars = end_time - timedelta(minutes=30)

            future_positions = executor.submit(client.get_open_positions, account_id)
            future_orders = executor.submit(client.get_orders, account_id, start_time_orders, end_time)
            future_bars = executor.submit(
                client.get_historical_bars, contract_id, start_time_bars, end_time,
                unit=2, unit_number=5, limit=6
            )
            
            open_positions = future_positions.result()
            orders = future_orders.result()
            bars_response = future_bars.result()

        # 4. Форматируем данные в строку
        status_lines = [f"**ҲИСОБ ҲОЛАТИ (API):**"]
        status_lines.append(f"- **Ҳисоб:** {primary_account.get('name', 'N/A')} (ID: {account_id})")
        status_lines.append(f"- **Баланс:** ${primary_account.get('balance', 0.0):,.2f}")

        if open_positions and open_positions.get("positions"):
            status_lines.append(f"- **Очиқ Позициялар:** {len(open_positions['positions'])} та")
            for pos in open_positions["positions"]:
                side = "Long" if pos.get('side', 0) == 0 else "Short"
                status_lines.append(f"  - {pos.get('contractId')}: {side} {pos.get('size')} @ {pos.get('price')} (P&L: ${pos.get('profitAndLoss', 0.0):,.2f})")
        else:
            status_lines.append("- **Очиқ Позициялар:** Йўқ")

        active_orders = [o for o in orders.get("orders", []) if o.get("status") == 0] if orders else []
        if active_orders:
            status_lines.append(f"- **Актив Ордерлар:** {len(active_orders)} та")
            for order in active_orders:
                order_type = "Limit" if order.get('type', 0) == 0 else "Stop"
                side = "Buy" if order.get('side', 0) == 0 else "Sell"
                status_lines.append(f"  - {order.get('contractId')}: {side} {order_type} {order.get('size')} @ {order.get('limitPrice') or order.get('stopPrice')}")
        else:
            status_lines.append("- **Актив Ордерлар:** Йўқ")
            
        status_lines.append("\n**БОЗОР МАЪЛУМОТЛАРИ (API):**")
        if bars_response and bars_response.get("bars"):
            status_lines.append(f"- **Охирги 5-дақиқалик свечалар ({contract_id}):**")
            for bar in bars_response["bars"]:
                ts = datetime.fromisoformat(bar['t'].replace('Z', '+00:00')).strftime('%H:%M')
                status_lines.append(f"  - {ts} | O: {bar['o']}, H: {bar['h']}, L: {bar['l']}, C: {bar['c']}, V: {bar['v']}")
        else:
            status_lines.append(f"- {contract_id} учун свечалар ҳақида маълумот олиб бўлмади.")

        console.print("[green]TopstepX API'дан маълумотлар муваффақиятли юкланди.[/green]")
        return "\n".join(status_lines)

    except Exception as e:
        console.print(f"[red]TopstepX API'дан маълумот олишда хатолик: {e}[/red]")
        return "  - Ошибка: TopstepX API'дан маълумот олишда хатолик юз берди."

# --- НОВОЕ ЯДРО АНАЛИЗА ("API") ---
def run_atrade_analysis(instrument_query: str, contract_id: str, screenshot_files: list[str]) -> str:
    """
    Выполняет полный "супер-анализ" на основе предоставленных данных.
    """
    # --- ШАГ 1: Сбор данных из API ---
    topstepx_data = get_formatted_topstepx_data(instrument_query, contract_id)
    
    console.print(f"\n[blue]'{instrument_query}' учун янгиликлар юкланмоқда...[/blue]")
    news_keywords = []
    if "gold" in instrument_query.lower() or "gc" in instrument_query.lower():
        news_keywords = ["Fed", "inflation", "interest rate", "geopolitics", "dollar", "treasury yields"]
        console.print(f"[cyan]Олтин учун калит сўзлар ишлатилмоқда: {', '.join(news_keywords)}[/cyan]")

    try:
        news_data = get_news(symbols=instrument_query, keywords=news_keywords)
        news_results = "\n".join([f"- {item.get('title')}" for item in news_data.get("results", [])]) or "Свежих новостей не найдено."
    except Exception as e:
        news_results = f"Ошибка при загрузке новостей: {e}"
    console.print("[green]Янгиликлар юкланди.[/green]")

    economic_calendar_data = fetch_economic_calendar_data()

    # --- ШАГ 2: Формирование промпта для Gemini ---
    console.print("\n[bold blue]Супер-комплекс таҳлил бошланмоқда...[/bold blue]")
    prompt = f"""Simulation. Role: experienced intraday trader. Instrument for analysis: {instrument_query}.
    Task: develop a detailed and flexible trading plan for the next 2-4 hours.
    Input data: 3 screenshots, news, economic calendar, and REAL DATA FROM THE TRADING ACCOUNT.

    **DATA FROM TRADING ACCOUNT (TopstepX API):**
    ```{topstepx_data}```

    **NEWS ({instrument_query}):**
    ```{news_results}```

    **ECONOMIC CALENDAR:**
    ```{economic_calendar_data}```

    **TASK:**

    1.  **Analysis:** Analyze **ALL** sources in English. Determine the trend, sentiment, key levels, and forecast confidence (A, B, C).
    2.  **Plan A (Primary):** Formulate the primary trading plan in English (Action, Entry, Stop-Loss, Targets TP1/TP2).
    3.  **Plan B (Alternative):** Describe a brief alternative plan in English if the price moves against the primary scenario.
    4.  **Translation:** Immediately translate the complete text analysis into the Uzbek language (Cyrillic script).
    5.  **Voice Summary:** Generate a very brief summary (2-3 sentences) in the Uzbek language (Cyrillic script) for the voice assistant, voicing only the **primary plan (Plan A)**.

    **OUTPUT FORMAT:**
    Provide the response STRICTLY as a single JSON object. Do not add any text before or after the JSON.

    **EXAMPLE JSON OUTPUT:**
    ```json
    {{
      "full_analysis_english": "Full text analysis in English...",
      "full_analysis_uzbek_cyrillic": "Рус тилидаги таҳлилнинг ўзбекча (кирилл) таржимаси...",
      "trade_data": {{
        "action": "BUY",
        "forecast_strength": "B",
        "primary_entry": 2350.5,
        "stop_loss": 2335.0,
        "take_profits": {{
          "tp1": 2365.0,
          "tp2": 2380.0
        }}
      }},
      "voice_summary_uzbek_cyrillic": "Буқа сентименти. А режаси: 2350.5 дан сотиб олиш, стоп-лосс 2335. Мақсадлар: 2365 ва 2380."
    }}
    ```
    """
    try:
        image_objects = [Image.open(p) for p in screenshot_files]
        # Теперь мы ожидаем от Gemini сразу готовый JSON
        raw_response = ask_gemini_with_image(prompt, image_objects)
        
        # --- Извлечение и парсинг JSON ---
        analysis_data = None
        json_match = re.search(r'```json\n({.*?})\n```', raw_response, re.DOTALL)
        if not json_match:
            json_match = re.search(r'({.*?})', raw_response, re.DOTALL)

        if json_match:
            json_string = json_match.group(1)
            try:
                analysis_data = json.loads(json_string)
            except json.JSONDecodeError:
                console.print("[red]Ошибка декодирования JSON от Gemini. Вывод сырого ответа:[/red]")
                console.print(raw_response)
                return f"Ошибка: Невалидный JSON от Gemini: {raw_response}"
        else:
            console.print("[red]Ответ Gemini не содержит ожидаемый JSON блок. Вывод сырого ответа:[/red]")
            console.print(raw_response)
            return f"Ошибка: Ответ Gemini не в формате JSON: {raw_response}"

        if not analysis_data:
            return "Ошибка: Не удалось получить структурированные данные от Gemini."

        # --- Извлекаем данные из полученного JSON ---
        text_analysis_uzbek_cyrillic = analysis_data.get("full_analysis_uzbek_cyrillic", "Таҳлил матни топилмади.")
        voice_summary_uzbek_cyrillic = analysis_data.get("voice_summary_uzbek_cyrillic")
        trade_data = analysis_data.get("trade_data")
        
        # --- Отображение полного анализа в терминале (на узбекском, кириллица) ---
        console.print(text_analysis_uzbek_cyrillic)

        # --- Обработка и красивый вывод JSON (обновленного) ---
        if trade_data:
            console.print("\n[bold green]--- JSON Data ---[/bold green]")
            print_json(data=trade_data)
        
        # --- Озвучивание голосовой сводки (на узбекском, кириллица) ---
        if voice_summary_uzbek_cyrillic:
            console.print("\n[bold cyan]Озвучиваю краткую сводку (на узбекском, кириллица)...[/bold cyan]")
            speak_muxlisa_text(voice_summary_uzbek_cyrillic)
        else:
            console.print("[yellow]Голосовая сводка не найдена в ответе.[/yellow]")

        # --- ИНТЕРАКТИВНОЕ РАЗМЕЩЕНИЕ ОРДЕРА ---
        if trade_data:
            try:
                action = trade_data.get("action", "").upper()
                
                # --- Логика для новых ордеров ---
                if action in ["BUY", "SELL"] and trade_data.get("primary_entry"):
                    entry_price = float(trade_data["primary_entry"])
                    stop_loss = float(trade_data["stop_loss"])
                    take_profit = float(trade_data["take_profits"]["tp1"])

                    console.print("\n" + "="*50)
                    console.print(f"[bold yellow]ЯНГИ ОРДЕР ЖОЙЛАШТИРИШ ТАКЛИФИ[/bold yellow]")
                    console.print(f"  - Инструмент: {contract_id}")
                    console.print(f"  - Йўналиш: [bold green]{action}[/bold green]" if action == "BUY" else f"  - Йўналиш: [bold red]{action}[/bold red]")
                    console.print(f"  - Кириш нархи (Limit): {entry_price}")
                    console.print(f"  - Stop-Loss: {stop_loss}")
                    console.print(f"  - Take-Profit: {take_profit}")
                    console.print(f"  - Ҳажм: 1 контракт")
                    console.print("="*50 + "\n")

                    console.print("[bold cyan]Автоматик тасдиқлаш режими ёқилган. Ордер автоматик равишда жойлаштирилади...[/bold cyan]")
                    confirmation = "ҳа" # Автоматик тасдиқлаш

                    if confirmation in ["ҳа", "ха", "yes", "да", "1"]:
                        console.print("[cyan]Ордерни жойлаштириш учун TopstepX'га уланилмоқда...[/cyan]")
                        client = TopstepXClient()
                        primary_account = get_primary_account(client)
                        if not primary_account:
                            console.print("[red]Ордер жойлаштириш учун ҳисоб топилмади.[/red]")
                        else:
                            # ВРЕМЕННО: Убираем SL/TP для отладки, отправляем только лимитный ордер
                            console.print("[bold yellow]!!! ДИАГНОСТИКА: Фақат Лимит ордер жўнатилмоқда (SL/TP сиз)...[/bold yellow]")
                            order_result = client.place_order(
                                contract_id=contract_id, account_id=primary_account["id"],
                                side=0 if action == "BUY" else 1, order_type=0, size=1, # 0 = Limit
                                limit_price=entry_price,
                                stop_loss=None, # Временно отключено
                                take_profit=None # Временно отключено
                            )
                            handle_order_result(order_result)
                    else:
                        console.print("[yellow]Ордер жойлаштириш бекор қилинди.[/yellow]")

                # --- Логика для закрытия существующих позиций ---
                elif action in ["SELL_TO_CLOSE", "BUY_TO_CLOSE"]:
                    close_action = "SELL" if action == "SELL_TO_CLOSE" else "BUY"
                    
                    console.print("\n" + "="*50)
                    console.print(f"[bold yellow]ПОЗИЦИЯНИ ЁПИШ ТАКЛИФИ[/bold yellow]")
                    console.print(f"  - Инструмент: {contract_id}")
                    console.print(f"  - Йўналиш: [bold red]Бозор нархида {close_action}[/bold red]")
                    console.print(f"  - Ҳажм: 1 контракт (мавжуд позицияни ёпиш учун)")
                    console.print("="*50 + "\n")
                    
                    confirmation = console.input("[bold]Ушбу позицияни бозор нархида ёпайми? (ҳа/1 ёки йўқ/0): [/bold]").lower()

                    if confirmation in ["ҳа", "ха", "yes", "да", "1"]:
                        console.print("[cyan]Позицияни ёпиш учун TopstepX'га уланилмоқда...[/cyan]")
                        client = TopstepXClient()
                        primary_account = get_primary_account(client)
                        if not primary_account:
                            console.print("[red]Ордер жойлаштириш учун ҳисоб топилмади.[/red]")
                        else:
                            order_result = client.place_order(
                                contract_id=contract_id, account_id=primary_account["id"],
                                side=1 if action == "SELL_TO_CLOSE" else 0,
                                order_type=2, size=1 # 2 = Market
                            )
                            handle_order_result(order_result)
                    else:
                        console.print("[yellow]Позицияни ёпиш бекор қилинди.[/yellow]")
                
                else:
                    raise ValueError(f"JSON'да нотўғри 'action' қиймати: '{action}'")

            except (ValueError, KeyError, TypeError) as e:
                console.print(f"[red]Ордерни автоматик жойлаштириш учун JSON'да маълумот етарли емас ёки нотўғри: {e}[/red]")

        # --- Отправка единого, форматированного сообщения в Telegram ---
        # Убираем ЛЮБОЕ форматирование, чтобы избежать ошибок парсинга
        if trade_data:
            plan_details = [
                "⚡️ Савдо Режаси ⚡️",
                f"   - Инструмент: {contract_id}",
                f"   - Йўналиш: {trade_data.get('action', 'N/A')}",
                f"   - Прогноз Ишончи: {trade_data.get('forecast_strength', 'N/A')}",
                "",
                "Нуқталар:",
                f"   - Кириш: {trade_data.get('primary_entry', 'N/A')}",
                f"   - Stop-Loss: {trade_data.get('stop_loss', 'N/A')}",
                f"   - TP1: {trade_data.get('take_profits', {}).get('tp1', 'N/A')}",
                f"   - TP2: {trade_data.get('take_profits', {}).get('tp2', 'N/A')}",
            ]
            plan_text = "\n".join(plan_details)
            telegram_message_uzbek_cyrillic = f"{text_analysis_uzbek_cyrillic}\n\n{plan_text}"
        else:
            telegram_message_uzbek_cyrillic = text_analysis_uzbek_cyrillic

        # Отправляем как обычный текст, без parse_mode
        send_long_telegram_message(telegram_message_uzbek_cyrillic)

        return telegram_message_uzbek_cyrillic
    except Exception as e:
        error_msg = f"Произошла ошибка при анализе: {e}"
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

def get_primary_account(client: TopstepXClient):
    """Вспомогательная функция для получения основного счета."""
    accounts_response = client.get_account_list()
    if not accounts_response or not accounts_response.get("accounts"):
        return None
    preferred_account_name = os.environ.get("TOPSTEPX_ACCOUNT_NAME")
    return next((acc for acc in accounts_response["accounts"] if acc.get("name") == preferred_account_name), accounts_response["accounts"][0])

def handle_order_result(order_result):
    """Вспомогательная функция для обработки ответа от API после размещения ордера."""
    if order_result and order_result.get("success"):
        console.print("[bold green]✅ Ордер муваффақиятли жойлаштирилди![/bold green]")
        print_json(data=order_result)
    else:
        console.print("[bold red]❌ Ордер жойлаштиришда хатолик юз берди.[/bold red]")
        if order_result:
            print_json(data=order_result)

# --- СТАРЫЙ ОБРАБОТЧИК КОМАНД (ТЕПЕРЬ ИСПОЛЬЗУЕТ "API") ---
def atrade_command(args: str = None):
    """Интерактивная оболочка для запуска супер-анализа."""
    
    console.print(f"[bold blue][DEBUG] atrade_command received args: '{args}'[/bold blue]")

    instrument_map = {
        # Oltin
        "gold": "GC", "gc": "GC", "oltin": "GC", "zoloto": "GC",
        # Neft
        "oil": "CL", "cl": "CL", "neft": "CL",
        # S&P 500
        "s&p": "ES", "es": "ES", "sipi": "ES",
        # NASDAQ
        "nasdaq": "NQ", "nq": "NQ",
        # Bitcoin
        "bitcoin": "BTC", "btc": "BTC", "bitkoin": "BTC",
        # Ethereum
        "ethereum": "ETH", "eth": "ETH", "efir": "ETH",
        # Valyutalar
        "evro": "EURUSD", "eurusd": "EURUSD",
        "frank": "USDCHF", "usdchf": "USDCHF",
        "pound": "GBPUSD", "gbpusd": "GBPUSD",
    }
    
    screenshot_files = []
    instrument_query = None
    contract_id = None

    if args:
        parts = shlex.split(args)
        instrument_query = parts[0].lower()
        console.print(f"[bold blue][DEBUG] Parsed instrument_query: '{instrument_query}'[/bold blue]")
    
    if not instrument_query:
        instrument_query = console.input("[bold yellow]Инструмент номини киритинг (масалан, gold, oil, es): [/bold yellow]").lower()

    if not instrument_query:
        console.print("[red]Инструмент номи киритилмади. Таҳлил тўхтатилди.[/red]"); return

    contract_id = instrument_map.get(instrument_query)
    console.print(f"[bold blue][DEBUG] Looked up '{instrument_query}' in instrument_map. Result: '{contract_id}'[/bold blue]")

    if not contract_id:
        console.print(f"[red]'{instrument_query}' учун API тикери топилмади. Луғатни текширинг.[/red]"); return

    console.print(f"[cyan]Таҳлил учун танланди: {instrument_query.capitalize()} (API Ticker: {contract_id})[/cyan]")
    console.print("[yellow]Интерактив скриншот олиш режими...[/yellow]")
    
    timestamp_folder = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_QTrade_CLI")
    current_batch_dir = SCREENSHOT_DIR / timestamp_folder
    current_batch_dir.mkdir(parents=True, exist_ok=True)
    for i in range(3):
        console.print(f"\n[cyan]Скриншот #{i + 1}/3 учун тайёрланинг (3 сония)...[/cyan]")
        time.sleep(3)
        path = current_batch_dir / f"screenshot_{i + 1}.png"
        os.system(f'screencapture -w "{str(path)}"')
        if not path.exists() or path.stat().st_size == 0:
            console.print("[red]Скриншот олиш бекор қилинди.[/red]"); return
        console.print(f"[green]Скриншот #{i + 1} сақланди.[/green]")
        screenshot_files.append(str(path))

    if len(screenshot_files) == 3:
        # Вызываем новое ядро анализа с обоими именами
        return run_atrade_analysis(instrument_query, contract_id, screenshot_files)
    else:
        msg = "3 та скриншот олишнинг иложи бўлмади."
        console.print(f"[red]{msg}[/red]")
        return msg