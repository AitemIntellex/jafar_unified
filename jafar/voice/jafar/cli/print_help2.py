from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


def print_help2():
    core_commands = [
        ("addfound <ticker> [path]", "Выполняет комплексный анализ, совмещая фундаментальные данные по тикеру с техническим анализом последних скриншотов."),
        ("scrn <path_to_image(s)>", "Анализирует скриншоты. Может генерировать торговый план (включая Stop-Loss/Take-Profit на основе ATR) или извлекать сырые данные индикаторов в формате JSON."),
        ("analyze [path_to_file] [--themes]", "Основной обработчик для анализа новостей. Принимает файл с новостями и готовит промпт для их анализа. Может также выделять ключевые темы."),
        ("intraday", "Интерактивно делает 4 скриншота и выполняет краткосрочный технический анализ."),
        ("intraday2", "Аналогично intraday, но дополнительно рассчитывает и добавляет в отчет торговые метрики (размер позиции, риск/прибыль в USD)."),
        ("fetch_calendar", "Получает данные экономического календаря с Investing.com и сохраняет их во временный файл для последующего анализа."),
    ]

    helper_commands = [
        ("addscrn", "Автоматически делает серию скриншотов с таймером."),
        ("set_default_screenshot_region", "Устанавливает область экрана по умолчанию для команды addscrn."),
        ("finalize <type> <text_or_path>", "Сохраняет отчет анализа в нужную директорию и отправляет его в Telegram."),
        ("send_latest", "Находит последний отчет по анализу и последние 4 скриншота и отправляет их вместе в Telegram."),
        ("speak <text_or_path>", "Озвучивает предоставленный текст или содержимое файла с помощью Google Text-to-Speech."),
        ("agent-mode <prompt>", "Выполняет последовательность команд Jafar CLI на основе запроса на естественном языке."),
    ]

    core_descriptions = "\n".join(f"- `{cmd}` — {desc}" for cmd, desc in core_commands)
    helper_descriptions = "\n".join(f"- `{cmd}` — {desc}" for cmd, desc in helper_commands)

    md = Markdown(
        f"# Jafar CLI — Справка по командам анализа\n\n### Основные команды анализа\n{core_descriptions}\n\n### Вспомогательные команды\n{helper_descriptions}\n"
    )

    console.print(
        Panel(
            md,
            title="Справка по аналитике (Help 2)",
            style="bold green",
        )
    )


if __name__ == "__main__":
    print_help2()