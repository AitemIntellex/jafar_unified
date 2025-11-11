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
from jafar.cli.economic_calendar_fetcher import fetch_and_save_economic_calendar_data

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

def intraday4_command(args: str = None):
    """Интерактивно делает 3 скриншота, анализирует их вместе с экономическим календарем."""
    
    # 1. Получаем данные экономического календаря
    console.print("[bold blue]Запрос данных экономического календаря...[/bold blue]")
    fetch_and_save_economic_calendar_data()
    calendar_data_path = Path(__file__).parent.parent.parent / "temp" / "economic_calendar_data.txt"
    economic_calendar_data = ""
    if calendar_data_path.exists():
        with open(calendar_data_path, "r", encoding="utf-8") as f:
            economic_calendar_data = f.read()
        console.print("[bold green]Экономический календарь успешно загружен.[/bold green]")
    else:
        console.print("[bold yellow]Файл экономического календаря не найден.[/bold yellow]")

    # 2. Создаем уникальную папку для сессии
    timestamp_folder = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_Intraday")
    current_batch_dir = SCREENSHOT_DIR / timestamp_folder
    current_batch_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold green]Скриншоты будут сохранены в папку:[/bold green] {current_batch_dir}")

    screenshot_files = []
    num_screenshots = 3

    # 3. Цикл для создания 3 скриншотов
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

    # 4. Анализ после создания скриншотов
    if len(screenshot_files) == num_screenshots:
        console.print("\n[bold blue]Запускаю комплексный анализ (техника + фундамент)...[/bold blue]")
        
        prompt = f"""Внимание: это симуляция для тестирования системы комплексного анализа. Твоя задача — выступить в роли интрадей-трейдера и разработать торговый план на ближайшие 2-4 часа.

**Входные данные:**
1.  3 скриншота одного актива на разных таймфреймах.
2.  Данные экономического календаря на сегодня.

**Экономический календарь:**
```
{economic_calendar_data}
```

**Техническое задание:**
1.  **Комплексный анализ:**
    *   **Проанализируй экономический календарь:** Есть ли важные новости (3 звезды), которые могут повлиять на актив в ближайшие часы? Как они могут повлиять на волатильность и направление цены?
    *   **Проанализируй скриншоты:** 
        *   **Найди панель 'Окно данных'** в правой части экрана. Используй ее как основной источник числовых значений.
        *   **Правила чтения цен:** Цены на этот актив являются **ШЕСТИЗНАЧНЫМИ** (например, `116885.57`). **Не отбрасывай первую цифру!**
        *   **Определи тренд** по MA(21) и MA(50) на старших таймфреймах.
        *   **Найди точку входа** по Stochastic на младших таймфреймах.
        *   **Извлеки значение ATR** для расчета рисков.
2.  **Формулировка торгового плана:**
    *   **Действие:** (Покупка / Продажа / Вне рынка)
    *   **Точка входа:** (Конкретная цена и тип ордера)
    *   **Stop-Loss:** (Рассчитан как `Цена входа - 1.5 * ATR`)
    *   **Take-Profit:** (Рассчитан как `Цена входа + 2 * ATR`)
    *   **Обоснование:** Кратко объясни, почему план именно такой, **обязательно учитывая как технические сигналы, так и предстоящие экономические новости**. Если из-за новостей лучше остаться вне рынка, обоснуй это.

**Требования к симуляции:**
*   Фокус — **только на ближайшие 2-4 часа**.
*   Ответ должен быть четким, структурированным торговым планом.
*   Не давать финансовых советов.

**Обязательно включи в конце ответа следующие числовые значения в формате JSON. Формат должен быть строго таким:**
{{
  "entry_price": <значение_или_null>,
  "stop_loss": <значение_или_null>,
  "take_profit": <значение_или_null>,
  "atr_value": <значение>,
  "instrument": "<идентификатор_инструмента>",
  "contract_multiplier": <значение>
}}"""
        
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
                    # Sanitize the JSON string: remove comments, trailing commas
                    json_str = re.sub(r'//.*?\n|/\*.*?\*/', '', json_match.group(1), flags=re.DOTALL)
                    json_str = re.sub(r',\s*([\}\]])', r'\1', json_str)
                    
                    parsed_data = json.loads(json_str)
                    entry_price = parsed_data.get("entry_price")
                    stop_loss = parsed_data.get("stop_loss")
                    take_profit = parsed_data.get("take_profit")
                    atr_value = parsed_data.get("atr_value")
                    instrument = parsed_data.get("instrument")
                    contract_multiplier = parsed_data.get("contract_multiplier")
                except json.JSONDecodeError as e:
                    console.print(f"[red]Ошибка парсинга JSON из ответа Gemini: {e}[/red]")
                    console.print(f"[red]Полученный JSON-подобный текст: {json_match.group(1)}[/red]")


            # --- Новая логика обработки результата ---
            if json_match:
                # Если JSON найден, пытаемся рассчитать метрики
                if all(val is not None for val in [entry_price, stop_loss, take_profit, atr_value]):
                    # --- Расчет и добавление метрик ---
                    final_contract_multiplier = contract_multiplier
                    if final_contract_multiplier is None and instrument:
                        final_contract_multiplier = CONTRACT_MULTIPLIERS.get(instrument.upper(), 1.0)
                        if final_contract_multiplier == 1.0 and instrument.upper() not in CONTRACT_MULTIPLIERS:
                            console.print(f"[bold yellow]Предупреждение: Множитель контракта для инструмента '{instrument}' не найден. Используется 1.0.[/bold yellow]")
                    elif final_contract_multiplier is None:
                        final_contract_multiplier = 1.0

                    position_size = MAX_CONTRACTS
                    metrics = calculate_trade_metrics(entry_price, stop_loss, take_profit, position_size, final_contract_multiplier)

                    if "error" in metrics:
                        analysis_result += f"\n\n[bold red]Ошибка расчета метрик: {metrics['error']}[/bold red]"
                    else:
                        analysis_result += "\n\n--- Метрики торгового плана (Topstep Rules) ---"
                        if instrument:
                            analysis_result += f"\n**Инструмент:** {instrument}"
                        analysis_result += f"\n**Размер позиции:** {position_size} контрактов"
                        analysis_result += f"\n**Множитель контракта:** {final_contract_multiplier}"
                        analysis_result += f"\n**Депозит для расчета риска:** ${DEPOSIT:,.2f}"
                        analysis_result += "\n---"
                        risk_status = "✅ OK" if metrics['is_within_max_risk'] else "❌ ПРЕВЫШЕН"
                        analysis_result += f"\n**Общий риск по сделке:** ${metrics['total_risk_usd']:,.2f} (Макс. допуст.: ${metrics['max_risk_allowed_usd']:,.2f}) -> {risk_status}"
                        analysis_result += f"\n**Потенциальная прибыль:** ${metrics['total_profit_usd']:,.2f}"
                        analysis_result += f"\n**Соотношение Риск/Прибыль:** 1:{metrics['risk_reward_ratio']}"
                        analysis_result += "\n---"
                        winning_day_status = "✅ Да" if metrics['meets_winning_day_target'] else "❌ Нет"
                        analysis_result += f"\n**Цель 'Winning Day' ($150.00):** {winning_day_status}"

                elif any(val is None for val in [entry_price, stop_loss, take_profit]) and "вне рынка" in analysis_result.lower():
                    # --- Случай "Вне рынка" ---
                    analysis_result += "\n\n--- Метрики торгового плана ---"
                    analysis_result += "\n**Рекомендация:** Оставаться вне рынка."
                    analysis_result += "\n**Причина:** Высокая волатильность из-за новостей или отсутствие четких сигналов."
                    analysis_result += "\n**Расчет метрик:** Не производится."
                
                else:
                    # --- Случай, когда данные неполные, но это не "Вне рынка" ---
                    missing_data = [k for k, v in {"entry_price": entry_price, "stop_loss": stop_loss, "take_profit": take_profit, "atr_value": atr_value}.items() if v is None]
                    analysis_result += f"\n\n[bold yellow]Внимание:[/bold yellow] Не удалось извлечь все ключевые данные для расчета метрик: {', '.join(missing_data)}. Расчет не произведен."

            else:
                # --- Случай, когда JSON вообще не найден ---
                analysis_result += "\n\n[bold red]Ошибка:[/bold red] Не удалось найти блок JSON в ответе AI. Расчет метрик невозможен."
            
            # Отправка в Telegram
            short_caption = "Комплексный анализ (техника + фундамент). Подробности ниже."
            send_telegram_media_group(screenshot_files, short_caption, parse_mode="MarkdownV2")
            send_long_telegram_message(analysis_result, parse_mode="MarkdownV2")
            
            return analysis_result
        except Exception as e:
            return f"Произошла ошибка при анализе: {e}"
    else:
        console.print("[red]Не удалось создать все необходимые скриншоты.[/red]")

    return None

