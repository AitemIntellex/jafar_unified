import os
import time
from pathlib import Path
from datetime import datetime
from rich.console import Console
from PIL import Image
import io
import sys
from jafar.utils.gemini_api import ask_gemini_with_image
from jafar.cli.telegram_handler import send_telegram_media_group, send_long_telegram_message
from jafar.cli.voice_output_handler import speak_message

console = Console()
SCREENSHOT_DIR = Path("screenshot")

DEPOSIT = 2000.0  # Депозит для расчета риска
MAX_RISK_PERCENT = 0.02  # Максимальный риск на сделку в %
WINNING_DAY_TARGET_USD = 150.0  # Цель по правилам Topstep
MAX_CONTRACTS = 5  # Максимальный размер позиции по вашим правилам

# Add this dictionary near the top, after DEPOSIT, MAX_RISK_PERCENT, etc.
CONTRACT_MULTIPLIERS = {
    "/GC": 100.0,  # Gold Futures (standard contract)
    "/MGC": 10.0,  # Micro Gold Futures
    "EURUSD": 100000.0, # Standard Forex Lot
    "GBPUSD": 100000.0,
    "USDJPY": 100000.0,
    "SPX500": 50.0, # S&P 500 Futures (E-mini)
    # Add more as needed
}

def calculate_trade_metrics(entry_price: float, stop_loss: float, take_profit: float, position_size: float, contract_multiplier: float = 1.0) -> dict:
    risk_per_unit = abs(entry_price - stop_loss)
    profit_per_unit = abs(take_profit - entry_price)

    if risk_per_unit == 0:
        return {"error": "Risk per unit is zero, cannot calculate metrics."}

    # Calculate total risk and profit for the fixed position size
    total_risk_usd = position_size * risk_per_unit * contract_multiplier
    total_profit_usd = position_size * profit_per_unit * contract_multiplier
    
    # Calculate risk/reward
    risk_reward_ratio = total_profit_usd / total_risk_usd if total_risk_usd > 0 else float('inf')
    
    # Check against Topstep and personal rules
    meets_winning_day_target = total_profit_usd >= WINNING_DAY_TARGET_USD
    max_risk_allowed_usd = DEPOSIT * MAX_RISK_PERCENT
    is_within_max_risk = total_risk_usd <= max_risk_allowed_usd

    return {
        "total_risk_usd": round(total_risk_usd, 2),
        "total_profit_usd": round(total_profit_usd, 2),
        "risk_reward_ratio": round(risk_reward_ratio, 2),
        "meets_winning_day_target": meets_winning_day_target,
        "is_within_max_risk": is_within_max_risk,
        "max_risk_allowed_usd": round(max_risk_allowed_usd, 2),
        "points_to_stop": round(risk_per_unit, 2),
        "points_to_target": round(profit_per_unit, 2)
    }

def intraday2_command(args: str = None):
    """Интерактивно делает 4 скриншота и выполняет краткосрочный технический анализ."""
    
    # 1. Создаем уникальную папку для сессии
    timestamp_folder = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_Intraday")
    current_batch_dir = SCREENSHOT_DIR / timestamp_folder
    current_batch_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold green]Скриншоты будут сохранены в папку:[/bold green] {current_batch_dir}")

    screenshot_files = []
    num_screenshots = 4

    # 2. Цикл для создания 4 скриншотов
    for i in range(num_screenshots):
        console.print(f"\n[bold cyan]Готовьтесь к скриншоту #{i + 1}/{num_screenshots}.[/bold cyan]")
        console.print("У вас есть 5 секунд, чтобы переключиться на нужный график...")
        time.sleep(5)

        screenshot_path = current_batch_dir / f"intraday_screenshot_{i + 1}.png"
        command = f"screencapture -w \"{str(screenshot_path)}\""
        
        console.print("[yellow]Курсор превратился в камеру. Кликните на окно с графиком.[/yellow]")
        os.system(command)
        
        if not screenshot_path.exists() or screenshot_path.stat().st_size == 0:
            console.print("[red]❌ Создание скриншота было отменено. Прерываю процесс.[/red]")
            sys.exit(1)
        
        console.print(f"[green]✅ Скриншот #{i + 1} успешно сохранен![/green]")
        screenshot_files.append(str(screenshot_path))

    # 3. Анализ после создания скриншотов
    if len(screenshot_files) == num_screenshots:
        console.print("\n[bold blue]Запускаю краткосрочный технический анализ...[/bold blue]")
        
        prompt = """Внимание: это симуляция для тестирования системы краткосрочного технического анализа. Твоя задача — выступить в роли интрадей-трейдера и разработать торговый план на ближайшие 2-4 часа.

**Входные данные:** 4 скриншота одного актива на разных таймфреймах.

**Техническое задание:**
1.  **Анализ данных:**
    *   **Найди панель 'Окно данных'** в правой части экрана. Используй ее как основной источник числовых значений.
    *   **Правила чтения цен:** Цены на этот актив являются **ШЕСТИЗНАЧНЫМИ** (например, `116885.57`). **Не отбрасывай первую цифру!**
    *   **Определи тренд** по MA(21) и MA(50) на старших таймфреймах.
    *   **Найди точку входа** по Stochastic на младших таймфреймах.
    *   **Извлеки значение ATR** для расчета рисков.
2.  **Формулировка торгового плана:**
    *   **Действие:** (Покупка / Продажа)
    *   **Точка входа:** (Конкретная цена и тип ордера)
    *   **Stop-Loss:** (Рассчитан как `Цена входа - 1.5 * ATR`)
    *   **Take-Profit:** (Рассчитан как `Цена входа + 2 * ATR`)
    *   **Обоснование:** Кратко объясни, почему план именно такой, ссылаясь на сигналы с разных таймфреймов.

**Требования к симуляции:**
*   Фокус — **только на ближайшие 2-4 часа**.\n*   Ответ должен быть четким, структурированным торговым планом.
*   Не давать финансовых советов.

**Обязательно включи в конце ответа следующие числовые значения в формате JSON. Формат должен быть строго таким:**
{
  "entry_price": <значение>,
  "stop_loss": <значение>,
  "take_profit": <значение>,
  "atr_value": <значение>,
  "instrument": "<идентификатор_инструмента>",
  "contract_multiplier": <значение>
}"""
        
        try:
            # --- Читаем изображения в объекты PIL ---
            image_objects = []
            for path in screenshot_files:
                with open(path, "rb") as f:
                    image_bytes = f.read()
                img = Image.open(io.BytesIO(image_bytes))
                image_objects.append(img)
            
            analysis_result = ask_gemini_with_image(prompt, image_objects)
            
            # --- Парсим значения из analysis_result ---
            import re
            import json

            entry_price = None
            stop_loss = None
            take_profit = None
            atr_value = None
            instrument = None
            contract_multiplier = None

            json_match = re.search(r'(\{.*?\})', analysis_result, re.DOTALL)
            if json_match:
                try:
                    parsed_data = json.loads(json_match.group(1))
                    entry_price = parsed_data.get("entry_price")
                    stop_loss = parsed_data.get("stop_loss")
                    take_profit = parsed_data.get("take_profit")
                    atr_value = parsed_data.get("atr_value")
                    instrument = parsed_data.get("instrument")
                    contract_multiplier = parsed_data.get("contract_multiplier")
                except json.JSONDecodeError:
                    console.print("[red]Ошибка парсинга JSON из ответа Gemini.[/red]")

            if all([entry_price, stop_loss, take_profit, atr_value]):
                # Determine contract_multiplier
                final_contract_multiplier = contract_multiplier
                if final_contract_multiplier is None and instrument:
                    # Try to look up from pre-defined mapping
                    final_contract_multiplier = CONTRACT_MULTIPLIERS.get(instrument.upper(), 1.0)
                    if final_contract_multiplier == 1.0 and instrument.upper() not in CONTRACT_MULTIPLIERS:
                        console.print(f"[bold yellow]Предупреждение: Множитель контракта для инструмента '{instrument}' не найден в базе данных. Используется значение по умолчанию 1.0. Расчеты могут быть неточными.[/bold yellow]")
                elif final_contract_multiplier is None:
                    final_contract_multiplier = 1.0 # Default if instrument not identified either

                if final_contract_multiplier == 1.0 and (contract_multiplier is None or (instrument and instrument.upper() not in CONTRACT_MULTIPLIERS)):
                    console.print(f"[bold yellow]Множитель контракта для инструмента '{instrument}' не был автоматически определен. Пожалуйста, введите его вручную.[/bold yellow]")
                    try:
                        user_input_multiplier = float(input("Введите множитель контракта: ").strip())
                        if user_input_multiplier > 0:
                            final_contract_multiplier = user_input_multiplier
                            console.print(f"[bold green]Используется множитель контракта: {final_contract_multiplier}[/bold green]")
                        else:
                            console.print("[bold red]Неверный ввод. Используется значение по умолчанию 1.0.[/bold red]")
                    except ValueError:
                        console.print("[bold red]Неверный ввод. Используется значение по умолчанию 1.0.[/bold red]")

                # Используем фиксированный размер позиции
                position_size = MAX_CONTRACTS
                
                metrics = calculate_trade_metrics(entry_price, stop_loss, take_profit, position_size, final_contract_multiplier)
                
                if "error" in metrics:
                    analysis_result += f"\n\n[bold red]Ошибка расчета метрик: {metrics['error']}[/bold red]"
                else:
                    analysis_result += "\n\n--- Метрики торгового плана (Topstep Rules) ---"
                    if instrument:
                        analysis_result += f"**Инструмент:** {instrument}\n"
                    analysis_result += f"**Размер позиции:** {position_size} контрактов (фиксированный)\n"
                    analysis_result += f"**Множитель контракта:** {final_contract_multiplier}\n"
                    analysis_result += f"**Депозит для расчета риска:** ${DEPOSIT:,.2f}\n"
                    analysis_result += "---"
                    
                    risk_status = "✅ OK" if metrics['is_within_max_risk'] else "❌ ПРЕВЫШЕН"
                    analysis_result += f"**Общий риск по сделке:** ${metrics['total_risk_usd']:,.2f} (Макс. допуст.: ${metrics['max_risk_allowed_usd']:,.2f}) -> {risk_status}\n"
                    analysis_result += f"**Потенциальная прибыль:** ${metrics['total_profit_usd']:,.2f}\n"
                    analysis_result += f"**Соотношение Риск/Прибыль:** 1:{metrics['risk_reward_ratio']}\n"
                    analysis_result += "---"
                    
                    winning_day_status = "✅ Да" if metrics['meets_winning_day_target'] else "❌ Нет"
                    analysis_result += f"**Цель 'Winning Day' ($150.00):** {winning_day_status}\n"
            else:
                missing_data = []
                if entry_price is None: missing_data.append("entry_price")
                if stop_loss is None: missing_data.append("stop_loss")
                if take_profit is None: missing_data.append("take_profit")
                if atr_value is None: missing_data.append("atr_value")
                if instrument is None: missing_data.append("instrument")
                if contract_multiplier is None: missing_data.append("contract_multiplier") # Check if Gemini provided it

                analysis_result += f"\n\n[bold red]Не удалось извлечь следующие данные для расчета метрик: {', '.join(missing_data)}. Пожалуйста, убедитесь, что Gemini предоставил их в JSON-формате.[/bold red]"
            
            # Отправка в Telegram
            short_caption = "Краткосрочный технический анализ. Подробности ниже."
            send_telegram_media_group(screenshot_files, short_caption, parse_mode="MarkdownV2")
            send_long_telegram_message(analysis_result, parse_mode="MarkdownV2")
            
            # Озвучиваем анализ (перенесено в command_router.py)
            # speak_message(analysis_result) 

            return analysis_result
        except Exception as e:
            return f"Произошла ошибка при анализе: {e}"
    else:
        console.print("[red]Не удалось создать все необходимые скриншоты.[/red]")

    return None
