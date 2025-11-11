from pathlib import Path
import os
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from jafar.cli.utils import get_projects_root
from jafar.utils.assistant_api import ask_assistant

console = Console()


def pytest_command(args: str):
    """
    Генерация и запуск pytest для указанного файла.
    usage: pytest <path/to/file.py>
    """
    if not args.strip():
        console.print(
            Panel(
                "[yellow]Укажи путь к Python-файлу: pytest <file.py>[/yellow]",
                title="Usage",
            )
        )
        return

    file_path = args.strip()
    # Если относительный путь, считаем от корня проекта
    if not os.path.isabs(file_path):
        file_path = os.path.join(get_projects_root(), file_path)

    if not os.path.exists(file_path):
        console.print(Panel(f"[red]Файл не найден: {file_path}[/red]", title="Error"))
        return

    # Читаем код и генерируем тесты через AI
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    prompt = f"""Сгенерируй pytest тесты для этого кода. Верни полный файл с тестами, включая импорты:

{code[:3000]}
"""
    response = ask_assistant(prompt) or {}
    test_code = response.get("command") or response.get("message") or str(response)

    # Сохраняем тест
    tests_dir = os.path.join(get_projects_root(), "tests")
    os.makedirs(tests_dir, exist_ok=True)
    filename = Path(file_path).stem
    test_file = os.path.join(tests_dir, f"test_{filename}.py")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(test_code)

    console.print(
        Panel(
            f"[green]Тесты сгенерированы и сохранены:[/green]\n{test_file}",
            title="Success",
        )
    )

    # Запускаем pytest для созданного теста
    console.print(
        Panel(f"Запуск pytest для {test_file}…", title="Running", style="cyan")
    )
    result = subprocess.run(["pytest", test_file], cwd=get_projects_root())
    if result.returncode == 0:
        console.print(
            Panel("[bold green]Все тесты прошли успешно![/bold green]", title="Done")
        )
    else:
        console.print(
            Panel(
                f"[bold red]Тесты завершились с ошибками (code {result.returncode})[/bold red]",
                title="Done",
            )
        )
