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
import subprocess
import concurrent.futures
from typing import Optional

from jafar.utils.gemini_api import ask_gemini_with_image
from jafar.utils.news_api import get_unified_news, get_news_from_newsapi
from jafar.utils.topstepx_api_client import TopstepXClient
from .telegram_handler import send_long_telegram_message
from .economic_calendar_fetcher import fetch_economic_calendar_data
from jafar.utils.market_utils import get_current_trading_session
from .muxlisa_voice_output_handler import speak_muxlisa_text
from jafar.utils.text_utils import convert_numbers_to_words_in_text

console = Console()
SCREENSHOT_DIR = Path("screenshot")
KEY_LEVELS_FILE = Path("memory/key_levels.json")

KEY_LEVELS_FILE = Path("memory/key_levels.json")

def save_key_levels_to_memory(instrument: str, trade_data: dict):
    """Saves key levels from trade_data to memory/key_levels.json."""
    if not trade_data:
        return

    source_id = f"ctrade-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    new_levels = []
    
    action = trade_data.get("action", "UNKNOWN")

    if entry := trade_data.get("entry_price"):
        level_type = f"ENTRY_{action.upper()}"
        new_levels.append({"level": float(entry), "type": level_type, "source_id": source_id, "status": "active"})
    
    if sl := trade_data.get("stop_loss"):
        new_levels.append({"level": float(sl), "type": "STOP_LOSS", "source_id": source_id, "status": "active"})
        
    if tps := trade_data.get("take_profits"):
        for i, (tp_name, tp_level) in enumerate(tps.items()):
            new_levels.append({"level": float(tp_level), "type": f"TAKE_PROFIT_{i+1}", "source_id": source_id, "status": "active"})

    if not new_levels:
        console.print("[yellow]Saqlash uchun yangi darajalar topilmadi.[/yellow]")
        return

    try:
        if KEY_LEVELS_FILE.exists() and KEY_LEVELS_FILE.stat().st_size > 0:
            with open(KEY_LEVELS_FILE, 'r', encoding='utf-8') as f:
                memory_data = json.load(f)
        else:
            memory_data = {}

        if instrument not in memory_data:
            memory_data[instrument] = []

        # Avoid adding duplicate levels based on level value (simple check)
        existing_levels = {lvl['level'] for lvl in memory_data[instrument]}
        for new_level in new_levels:
            if new_level['level'] not in existing_levels:
                memory_data[instrument].append(new_level)
                existing_levels.add(new_level['level'])

        with open(KEY_LEVELS_FILE, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, indent=2, ensure_ascii=False)
        
        console.print(f"[bold green]✅ {len(new_levels)} ta yangi daraja {instrument} uchun xotiraga saqlandi.[/bold green]")

    except (IOError, json.JSONDecodeError) as e:
        console.print(f"[red]Xotira fayliga darajalarni saqlashda xatolik: {e}[/red]")


# --- UTILITIES & CONSTANTS (from atrade) ---
MAX_CONTRACTS_MAP = {"MGC": 50, "GC": 5, "CL": 10, "ES": 10}

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
    }

def get_formatted_topstepx_data(instrument_query: str, contract_id: str) -> tuple[str, dict, dict]:
    try:
        client = TopstepXClient()
        accounts_response = client.get_account_list()
        if not accounts_response or not accounts_response.get("accounts"):
            return "  - Error: Could not get account list from TopstepX.", None, None
        
        all_accounts = accounts_response["accounts"]
        primary_account = next((acc for acc in all_accounts if acc.get("name") == os.environ.get("TOPSTEPX_ACCOUNT_NAME2")), all_accounts[0])
        account_id = primary_account["id"]
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=8)
            future_real_positions = executor.submit(client.get_open_positions, account_id)
            future_trades = executor.submit(client.get_trades, account_id, start_time, end_time)
            
            real_positions_response = future_real_positions.result()
            trades = future_trades.result()

        status_lines = [f"**ACCOUNT STATUS ({primary_account.get('name')}):**", f"- **Balance:** ${primary_account.get('balance', 0.0):,.2f}"]
        
        open_positions_with_side = {}
        real_open_positions = real_positions_response.get("positions", [])
        if real_open_positions:
            if trades and trades.get("trades"):
                sorted_trades = sorted(trades["trades"], key=lambda x: x.get("creationTimestamp", ""))
                temp_positions = {}
                for trade in sorted_trades:
                    contract = trade.get("contractId")
                    size = trade.get("size", 0)
                    side = trade.get("side", 0) # 0 = Buy, 1 = Sell
                    position_change = size if side == 0 else -size
                    temp_positions[contract] = temp_positions.get(contract, 0) + position_change
                
                for real_pos in real_open_positions:
                    contract = real_pos.get("contractId")
                    if temp_positions.get(contract) is not None:
                         open_positions_with_side[contract] = temp_positions[contract]

            for contract, size in open_positions_with_side.items():
                side_str = "Long" if size > 0 else "Short"
                status_lines.append(f"  - {contract}: {side_str} {abs(size)}")
        else:
            status_lines.append("- **Open Positions:** None")
        
        return "\n".join(status_lines), primary_account, open_positions_with_side

    except Exception as e:
        return f"  - Error: {e}", None, None

def start_escort_agent(order_id: int, account_id: int, contract_id: str, expected_side: str):
    """Запускает trade_escort_agent.py в фоновом режиме."""
    console.print(f"\n[bold magenta]🚀 Order #{order_id} uchun fon agentini ishga tushirish...[/bold magenta]")
    
    agent_script_path = Path(__file__).parent.parent / "monitors" / "trade_escort_agent.py"
    python_executable = sys.executable
    
    command = [
        python_executable, str(agent_script_path),
        "--order-id", str(order_id),
        "--account-id", str(account_id),
        "--contract-id", contract_id,
        "--expected-side", expected_side,
    ]

    try:
        subprocess.Popen(command, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        console.print(f"[green]✅ Order #{order_id} uchun agent muvaffaqiyatli ishga tushirildi.[/green]")
        speak_muxlisa_text(f"Agent {order_id} uchun ishga tushirildi.")
    except Exception as e:
        console.print(f"[red]❌ Fon agentini ishga tushirib bo'lmadi: {e}[/red]")
        send_long_telegram_message(f"🚨 **CRITICAL: Agent Start Failed**\nOrder ID: #{order_id}\nError: {e}")


def handle_order_result(order_result, account_id, contract_id, expected_side, order_type: int):
    """Обрабатывает результат размещения ордера и запускает агент, если нужно."""
    if order_result and order_result.get("success"):
        console.print("[bold green]✅ Buyurtma muvaffaqiyatli joylashtirildi![/bold green]")
    else:
        console.print("[bold red]❌ Buyurtma joylashtirishda xatolik.[/bold red]")
        
    if order_result:
        print_json(data=order_result)
        order_id = order_result.get("orderId")
        # Запускаем агент только для Limit и Stop ордеров, которые требуют ожидания
        if order_id and order_type in [1, 4]: # 1=Limit, 4=Stop
            start_escort_agent(order_id, account_id, contract_id, expected_side)

def run_ctrade_analysis(instrument_query: str, contract_symbol: str, screenshot_files: list[str]) -> dict:
    client = TopstepXClient()
    try:
        contract_info = client.search_contract(name=contract_symbol)
        active_contract = next((c for c in contract_info["contracts"] if c.get("activeContract")), None)
        if not active_contract: return {"status": "Ошибка", "full_analysis": f"Xatolik: '{contract_symbol}' uchun faol kontrakt topilmadi."}
        full_contract_id = active_contract.get("id")
        tick_size = active_contract.get("tickSize")
    except Exception as e:
        return {"status": "Ошибка", "full_analysis": f"Kontrakt qidirishda xatolik: {e}"}

    topstepx_data, primary_account, open_calculated_positions = get_formatted_topstepx_data(instrument_query, full_contract_id)
    if not primary_account:
        return {"status": "Ошибка", "full_analysis": "Xatolik: Riskni hisoblash uchun hisob ma'lumotlarini olib bo'lmadi."}

    current_position_size = open_calculated_positions.get(full_contract_id, 0)
    image_objects = [Image.open(p) for p in screenshot_files]
    current_session = get_current_trading_session()
    
    news_results, economic_calendar_data = "", ""
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_news = executor.submit(get_unified_news)
        future_calendar = executor.submit(fetch_economic_calendar_data)
        news_results = future_news.result()
        economic_calendar_data = future_calendar.result()

    if current_position_size != 0:
        position_side = "Long" if current_position_size > 0 else "Short"
        prompt = f"**MODE: OPEN POSITION MANAGEMENT**..." # Simplified for brevity
    else:
        prompt = f'''
        **MODE: NEW TRADE SEARCH**
        Instrument: {instrument_query}.
        **Current Trading Session:** {current_session}
        **DATA:**
        - Account Data: ```{topstepx_data}```
        - News: ```{news_results}```
        - Calendar: ```{economic_calendar_data}```
        **TASK:**
        1.  **Analyze:** Based on all data, determine trend, sentiment, key levels, and forecast confidence (A, B, C).
        2.  **Propose Risk:** Based on forecast confidence, propose a risk percentage (2% to 20%).
        3.  **Formulate Plan:** Formulate the primary trading plan. **`order_type` MUST be "LIMIT" or "STOP"**.
        4.  **Generate Uzbek Cyrillic Analysis:** Create `full_analysis_uzbek_cyrillic`. Format it beautifully with markdown.
        5.  **Generate Uzbek Latin Voice Summary:** Create `voice_summary_uzbek_latin`. It must be a concise, natural summary in UZBEK (LATIN) for voice output.
        **OUTPUT FORMAT (STRICTLY JSON):**
        ```json
        {{
          "full_analysis_uzbek_cyrillic": "...",
          "trade_data": {{
            "action": "BUY", "forecast_strength": "B", "risk_percent": 5.0,
            "order_type": "LIMIT", "entry_price": 2350.5, "stop_loss": 2335.0,
            "take_profits": {{ "tp1": 2365.0, "tp2": 2380.0 }}
          }},
          "voice_summary_uzbek_latin": "..."
        }}
        ```
        '''

    raw_response = ask_gemini_with_image(prompt, image_objects)
    try:
        json_match = re.search(r'```json\n({.*?})\n```', raw_response, re.DOTALL) or re.search(r'({.*?})', raw_response, re.DOTALL)
        if not json_match: raise ValueError("No JSON block found")
        analysis_data = json.loads(json_match.group(1))
    except (json.JSONDecodeError, ValueError) as e:
        return {"status": "Ошибка", "full_analysis": f"Xatolik: Gemini javobi yaroqli JSON formatida emas: {e}\nResponse: {raw_response}"}

    if trade_data := analysis_data.get("trade_data"):
        # Save the discovered levels to memory for the Super Agent
        save_key_levels_to_memory(contract_symbol, trade_data)
        
        action = trade_data.get("action", "").upper()
        order_type_str = trade_data.get("order_type", "LIMIT").upper()
        entry_price = trade_data.get("entry_price")

        if action in ["BUY", "SELL"] and entry_price:
            risk_percent = float(trade_data.get("risk_percent", 3.0))
            risk_percent = max(2.0, min(20.0, risk_percent))
            
            stop_loss = float(trade_data["stop_loss"])
            take_profit = float(trade_data["take_profits"]["tp1"])
            balance = primary_account.get("balance", 0.0)
            max_risk_for_trade = balance * (risk_percent / 100.0)
            contract_multiplier = active_contract.get("tickValue") / active_contract.get("tickSize")
            metrics = calculate_trade_metrics(entry_price, stop_loss, take_profit, contract_multiplier, max_risk_for_trade, contract_symbol)
            
            position_size = metrics.get("position_size", 1)
            if "error" in metrics:
                position_size = 1

            position_size = int(round(position_size))
            if position_size == 0:
                position_size = 1

            order_params = {
                "contract_id": full_contract_id, "account_id": primary_account["id"],
                "side": 0 if action == "BUY" else 1, "size": int(position_size),
                "stop_loss": stop_loss, "take_profit": take_profit, "tick_size": tick_size
            }
            if order_type_str == "LIMIT":
                order_params["order_type"] = 1
                order_params["limit_price"] = entry_price
            elif order_type_str == "STOP":
                order_params["order_type"] = 4
                order_params["stop_price"] = entry_price
            else: # Fallback to Market
                order_params["order_type"] = 2

            order_result = client.place_order(**order_params)
            handle_order_result(order_result, primary_account["id"], full_contract_id, action, order_params.get("order_type"))

    send_long_telegram_message(f"BTRADE TAHLILI ({instrument_query}):\n\n{analysis_data.get('full_analysis_uzbek_cyrillic', 'N/A')}")
    
    return {
        "status": "Успех",
        "full_analysis": analysis_data.get("full_analysis_uzbek_cyrillic", "Tahlil taqdim etilmagan."),
        "voice_summary": analysis_data.get("voice_summary_uzbek_latin")
    }

def speak_in_chunks(text: str, max_chunk_size: int = 500):
    if not text: return
    sentences = re.split(r'(?<=[.!?])\s+', text.replace('\n', ' '))
    current_chunk = ""
    for sentence in sentences:
        if not sentence: continue
        if len(current_chunk) + len(sentence) + 1 > max_chunk_size:
            speak_muxlisa_text(current_chunk.strip())
            current_chunk = sentence + " "
        else:
            current_chunk += sentence + " "
    if current_chunk.strip():
        speak_muxlisa_text(current_chunk.strip())

def ctrade_command(args: str = None):
    instrument_map = {"gold": "MGC", "mgc": "MGC", "oltin": "MGC", "zoloto": "MGC", "gc": "GC", "oil": "CL", "cl": "CL", "neft": "CL", "s&p": "ES", "es": "ES"}
    instrument_query = None
    if args:
        instrument_query = shlex.split(args)[0].lower()
    if not instrument_query:
        instrument_query = console.input("[bold yellow]Instrument (masalan, oltin): [/bold yellow]").lower()
    if not (contract_symbol := instrument_map.get(instrument_query)):
        console.print(f"[red]'{instrument_query}' uchun tiker topilmadi.[/red]"); return

    console.print(f"[cyan]Tahlil qilinmoqda: {instrument_query.capitalize()} ({contract_symbol})[/cyan]")
    
    screenshot_files = []
    current_batch_dir = SCREENSHOT_DIR / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    current_batch_dir.mkdir(parents=True, exist_ok=True)
    for i in range(3):
        time.sleep(3)
        path = current_batch_dir / f"screenshot_{i + 1}.png"
        os.system(f'screencapture -w "{str(path)}"')
        screenshot_files.append(str(path))

    analysis_result = run_ctrade_analysis(instrument_query, contract_symbol, screenshot_files)
    if analysis_result.get("status") == "Успех":
        console.print(f"\n[bold green]--- To'liq Tahlil (Kirillcha) ---[/bold green]\n{analysis_result.get('full_analysis', 'Mavjud emas.')}")
        if voice_summary := analysis_result.get("voice_summary"):
            processed_summary = convert_numbers_to_words_in_text(voice_summary)
            speak_in_chunks(processed_summary)
    else:
        console.print(f"\n[bold red]--- Tahlilda Xatolik ---[/bold red]\n{analysis_result.get('full_analysis', 'Noma`lum xatolik.')}")
