import os
import time
from pathlib import Path
from datetime import datetime
from rich.console import Console
from PIL import Image
import io
import sys
from jafar.utils.gemini_api import ask_gemini_with_image
from jafar.utils.news_api import get_news
from jafar.cli.telegram_handler import (
    send_telegram_media_group,
    send_long_telegram_message,
)
from jafar.cli.voice_output_handler import speak_message
from jafar.cli.economic_calendar_fetcher import fetch_and_save_economic_calendar_data

console = Console()
SCREENSHOT_DIR = Path("screenshot")

DEPOSIT = 2000.0
MAX_RISK_PERCENT_DEFAULT = 0.02  # 2% риск по умолчанию ($40)
MAX_RISK_GROUP_A = 450.0  # $450 риск для группы А
WINNING_DAY_TARGET_USD = 150.0
MAX_CONTRACTS = 5  # Максимальный размер позиции по вашим правилам

CONTRACT_MULTIPLIERS = {
    "/GC": 100.0,
    "/MGC": 10.0,
    "EURUSD": 100000.0,
    "GBPUSD": 100000.0,
    "USDJPY": 100000.0,
    "SPX500": 50.0,
}


def calculate_trade_metrics(
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    contract_multiplier: float,
    max_risk_for_trade: float,
) -> dict:
    risk_per_unit = abs(entry_price - stop_loss)
    if risk_per_unit == 0:
        return {"error": "Risk per unit is zero."}

    risk_per_contract = risk_per_unit * contract_multiplier
    if risk_per_contract == 0:
        return {"error": "Risk per contract is zero."}

    calculated_position_size = max_risk_for_trade / risk_per_contract
    position_size = min(calculated_position_size, MAX_CONTRACTS)

    if position_size < 0.01:
        return {
            "error": f"Calculated position size ({position_size:.2f}) is too small."
        }

    profit_per_unit = abs(take_profit - entry_price)
    total_risk_usd = position_size * risk_per_contract
    total_profit_usd = position_size * profit_per_unit * contract_multiplier
    risk_reward_ratio = (
        total_profit_usd / total_risk_usd if total_risk_usd > 0 else float("inf")
    )
    meets_winning_day_target = total_profit_usd >= WINNING_DAY_TARGET_USD

    return {
        "position_size": round(position_size, 2),
        "total_risk_usd": round(total_risk_usd, 2),
        "total_profit_usd": round(total_profit_usd, 2),
        "risk_reward_ratio": round(risk_reward_ratio, 2),
        "meets_winning_day_target": meets_winning_day_target,
    }


def intraday5_command(args: str = None):
    """Супер-анализ: 3 скриншота, новости, календарь и динамический расчет риска."""

    instrument_query = console.input(
        "[bold yellow]Введите тикер или название инструмента для поиска новостей (например, Gold, EURUSD): [/bold yellow]"
    )
    if not instrument_query:
        console.print(
            "[red]Название инструмента не введено. Поиск новостей пропущен.[/red]"
        )
        news_results = "Новости не запрашивались."
    else:
        console.print(
            f"[bold blue]Поиск новостей по запросу: '{instrument_query}'...[/bold blue]"
        )
        try:
            search_data = get_news(symbols=instrument_query)
            if "error" in search_data:
                console.print(f"[bold red]Ошибка при поиске новостей: {search_data['error']}[/bold red]")
                news_results = "Ошибка при загрузке новостей."
            else:
                news_items = [
                    f"- {item.get('title')}\n  (Источник: {item.get('url')})"
                    for item in search_data.get("results", [])
                ]
                news_results = (
                    "\n".join(news_items) if news_items else "Свежих новостей не найдено."
                )
                console.print("[bold green]Новости успешно загружены.[/bold green]")
        except Exception as e:
            console.print(f"[bold red]Критическая ошибка при поиске новостей: {e}[/bold red]")
            news_results = "Ошибка при загрузке новостей."

    console.print("[bold blue]Запрос данных экономического календаря...[/bold blue]")
    fetch_and_save_economic_calendar_data()
    calendar_data_path = (
        Path(__file__).parent.parent.parent / "temp" / "economic_calendar_data.txt"
    )
    economic_calendar_data = (
        calendar_data_path.read_text(encoding="utf-8")
        if calendar_data_path.exists()
        else ""
    )
    if economic_calendar_data:
        console.print(
            "[bold green]Экономический календарь успешно загружен.[/bold green]"
        )
    else:
        console.print(
            "[bold yellow]Файл экономического календаря не найден.[/bold yellow]"
        )

    timestamp_folder = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_Intraday")
    current_batch_dir = SCREENSHOT_DIR / timestamp_folder
    current_batch_dir.mkdir(parents=True, exist_ok=True)
    console.print(
        f"[bold green]Скриншоты будут сохранены в папку:[/bold green] {current_batch_dir}"
    )
    screenshot_files = []
    num_screenshots = 3
    for i in range(num_screenshots):
        console.print(
            f"\n[bold cyan]Готовьтесь к скриншоту #{i + 1}/{num_screenshots}. (5 секунд)[/bold cyan]"
        )
        time.sleep(5)
        screenshot_path = current_batch_dir / f"intraday_screenshot_{i + 1}.png"
        command = f'screencapture -w "{str(screenshot_path)}"'
        console.print("[yellow]Кликните на окно с графиком...[/yellow]")
        os.system(command)
        if not screenshot_path.exists() or screenshot_path.stat().st_size == 0:
            console.print("[red]❌ Создание скриншота отменено.[/red]")
            sys.exit(1)
        console.print(f"[green]✅ Скриншот #{i + 1} сохранен![/green]")
        screenshot_files.append(str(screenshot_path))

    if len(screenshot_files) == num_screenshots:
        console.print("\n[bold blue]Запускаю супер-комплексный анализ...[/bold blue]")

        prompt = f"""Внимание: симуляция. Твоя задача — выступить в роли интрадей-трейдера и разработать торговый план на 2-4 часа.

**Входные данные:**
1. 3 скриншота актива.
2. Экономический календарь.
3. Свежие новости по инструменту.

**Лента новостей:**
```
{news_results}
```

**Экономический календарь:**
```
{economic_calendar_data}
```

**Техническое задание:**
1.  **Супер-комплексный анализ:** Проанализируй все 3 источника (новости, календарь, графики), определи тренд, точку входа, ATR.
2.  **Сила прогноза:** Оцени свою уверенность в прогнозе по шкале (A, B, C), где A - высокая уверенность.
3.  **Формулировка торгового плана:** Действие (Покупка / Продажа / Вне рынка), Точка входа, Stop-Loss, Take-Profit и Обоснование, синтезируя все данные.

**Обязательно включи в конце ответа JSON со значениями (или null):**
{{
  "entry_price": <...>, "stop_loss": <...>, "take_profit": <...>, "atr_value": <...>, "instrument": "<..._инструмента>", "contract_multiplier": <...>, "forecast_strength": "<A, B, или C>"
}} """

        try:
            image_objects = [
                Image.open(io.BytesIO(open(path, "rb").read()))
                for path in screenshot_files
            ]
            analysis_result = ask_gemini_with_image(prompt, image_objects)

            import re
            import json

            (
                entry_price,
                stop_loss,
                take_profit,
                atr_value,
                instrument,
                contract_multiplier,
                forecast_strength,
            ) = (None, None, None, None, None, None, None)

            json_match = re.search(r"(\{.*?\})", analysis_result, re.DOTALL)
            if json_match:
                try:
                    json_str = re.sub(
                        r"//.*?\n|/\*.*?\*/", "", json_match.group(1), flags=re.DOTALL
                    )
                    json_str = re.sub(r",\s*([\}\]])", r"\1", json_str)
                    parsed_data = json.loads(json_str)
                    entry_price = parsed_data.get("entry_price")
                    stop_loss = parsed_data.get("stop_loss")
                    take_profit = parsed_data.get("take_profit")
                    atr_value = parsed_data.get("atr_value")
                    instrument = parsed_data.get("instrument")
                    contract_multiplier = parsed_data.get("contract_multiplier")
                    forecast_strength = parsed_data.get("forecast_strength")
                except json.JSONDecodeError as e:
                    console.print(f"[red]Ошибка парсинга JSON: {e}[/red]")

            if json_match:
                if all(
                    val is not None
                    for val in [entry_price, stop_loss, take_profit, atr_value]
                ):
                    max_risk_for_trade = DEPOSIT * MAX_RISK_PERCENT_DEFAULT
                    risk_level_reason = "(стандартный)"
                    if forecast_strength == "A":
                        max_risk_for_trade = MAX_RISK_GROUP_A
                        risk_level_reason = "(группа А)"

                    final_contract_multiplier = (
                        contract_multiplier
                        or CONTRACT_MULTIPLIERS.get(instrument.upper(), 1.0)
                    )
                    metrics = calculate_trade_metrics(
                        entry_price,
                        stop_loss,
                        take_profit,
                        final_contract_multiplier,
                        max_risk_for_trade,
                    )

                    if "error" in metrics:
                        analysis_result += f"\n\n[bold red]Ошибка расчета метрик: {metrics['error']}[/bold red]"
                    else:
                        analysis_result += "\n\n--- Метрики торгового плана ---"
                        analysis_result += f"\n**Инструмент:** {instrument or 'N/A'}"
                        analysis_result += f"\n**Сила прогноза:** {forecast_strength or 'N/A'} -> **Уровень риска:** ${max_risk_for_trade:,.2f} {risk_level_reason}"
                        analysis_result += f"\n**Рассчитанный размер позиции:** {metrics['position_size']} контрактов"
                        analysis_result += f"\n**Общий риск по сделке:** ${metrics['total_risk_usd']:,.2f}"
                        analysis_result += f"\n**Потенциальная прибыль:** ${metrics['total_profit_usd']:,.2f}"
                        analysis_result += f"\n**Соотношение Риск/Прибыль:** 1:{metrics['risk_reward_ratio']}"
                        winning_day_status = (
                            "✅ Да" if metrics["meets_winning_day_target"] else "❌ Нет"
                        )
                        analysis_result += (
                            f"\n**Цель 'Winning Day' ($150.00):** {winning_day_status}"
                        )

                elif (
                    any(val is None for val in [entry_price, stop_loss, take_profit])
                    and "вне рынка" in analysis_result.lower()
                ):
                    analysis_result += "\n\n--- Метрики торгового плана ---\n**Рекомендация:** Оставаться вне рынка."
                else:
                    missing_data = [
                        k
                        for k, v in {
                            "entry_price": entry_price,
                            "stop_loss": stop_loss,
                            "take_profit": take_profit,
                            "atr_value": atr_value,
                        }.items()
                        if v is None
                    ]
                    analysis_result += f"\n\n[bold yellow]Внимание:[/bold yellow] Не удалось извлечь все данные для расчета метрик: {', '.join(missing_data)}."
            else:
                analysis_result += "\n\n[bold red]Ошибка:[/bold red] Не удалось найти блок JSON в ответе AI."

            short_caption = "Супер-комплексный анализ (техника + календарь + новости)."
            send_telegram_media_group(
                screenshot_files, short_caption, parse_mode="MarkdownV2"
            )
            send_long_telegram_message(analysis_result, parse_mode="MarkdownV2")

            return analysis_result
        except Exception as e:
            return f"Произошла ошибка при анализе: {e}"
    else:
        console.print("[red]Не удалось создать все необходимые скриншоты.[/red]")
    return None
