from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


def print_help():
    commands = [
        ("ai <prompt> [--code|--plan|--json]", "быстрый умный ответ/анализ/генерация с указанием формата (код, план, JSON)"),
        ("chat <тема>", "начать диалог на тему (или продолжить)"),
        ("code <код>", "выполнить или объяснить код"),
        ("addscrn", "сделать скриншот текущего экрана"),
        ("analyze_screenshot <путь_к_изображению>", "использовать AI для анализа скриншота или изображения"),
        ("set_default_screenshot_region <x> <y> <width> <height>", "установить область скриншота по умолчанию"),
        ("file <action> <file>", "операции с файлами (review, edit, remember)"),
        ("github <action>", "управление git/AI-ревью"),
        ("project <action>", "управление проектами (init, start, stop)"),
        ("gamemode", "начать игру с Jafar-ассистентом"),
        ("evolution", "начать обучение Jafar-ассистента"),
        ("chatmode", "переключиться в режим чата с Jafar-ассистентом"),
        ("check <action>", "выполнить health-чеки (git, internet, process)"),
        ("tool <action>", "выполнить dev-утилиты (zip, init, start, …)"),
        ("mode <action>", "быстрый запуск game / trainer"),
        ("agent-mode <prompt>", "режим агента: Jafar выполняет команды по вашему запросу"),
        ("exit", "выйти из Jafar CLI"),
        ("quit", "выйти из Jafar CLI"),
        ("clear", "очистить экран терминала"),
        ("cls", "очистить экран терминала"),
        ("about", "информация о Jafar CLI"),
        ("version", "версия Jafar CLI"),
        ("help", "эта справка"),
    ]

    # Формируем markdown-список команд
    command_descriptions = "\n".join(f"- `{cmd}` — {desc}" for cmd, desc in commands)

    md = Markdown(
        f"""# Jafar CLI — поддерживаемые команды

{command_descriptions}
"""
    )

    console.print(
        Panel(
            md,
            title="Справка",
            style="bold cyan",
        )
    )
