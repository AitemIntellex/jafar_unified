import os
import shlex
import time
import traceback
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
import subprocess
import sys
import re

from jafar.assistant_core.assistant_api import ask_assistant
from jafar.assistant_core.structured_logger import log_action
from jafar.assistant_core.evolution_engine import analyze_logs, load_stats
from jafar.cli.ai_handlers import ai_command
from jafar.cli.chat_handlers import chat_command
from jafar.cli.check_handlers import check_command
from jafar.cli.code_handlers import code_command, extract_code_intent, show_code_help
from jafar.cli.file_handlers import file_command
from jafar.cli.game_handlers import game_mode_chat
from jafar.cli.github_handlers import (
    github_command,
    github_inspect,
    next_task,
    push_project,
    show_github_issues_and_prs,
    extract_repo_info,
    PROJECTS_ROOT,
)
from jafar.cli.intent_router import route_by_intent
from jafar.cli.print_help import print_help
from jafar.cli.project_handlers import projects_command
from jafar.cli.project_run_handler import run_project
from jafar.cli.agent_handlers import agent_mode_command
from jafar.cli.pytest_handlers import pytest_command
from jafar.cli.image_analysis_handler import analyze_screenshot_for_plan
from jafar.cli.fundamental_analysis_handler import analyze_with_fundamental_command
from jafar.cli.mt5_handlers import mt5_screenshot_command
from jafar.cli.qtrade_handlers import qtrade_command
from jafar.cli.scalp_handlers import scalp_command
from jafar.cli.intraday_handlers import intraday_command
from jafar.cli.atrade_handlers import atrade_command
from jafar.cli.interactive_analyzer import start_interactive_analysis
from jafar.cli.telegram_handler import send_telegram_message
from jafar.cli.finalize_handlers import finalize_analysis
from jafar.cli.economic_calendar_fetcher import fetch_and_save_economic_calendar_data

from jafar.cli.utils import multiline_input
from jafar.utils.config_manager import (
    load_config as load_jafar_config,
    save_config as save_jafar_config,
)

console = Console()


def jafar_print(message, **kwargs):
    console.print(message, **kwargs)


def _activate_safari_and_wait():
    """Activates Safari and waits for a moment."""
    jafar_print("[bold blue]Активация Safari...[/bold blue]")
    script = """
    tell application "Safari"
        activate
    end tell
    """
    os.system(f"osascript -e '{script}'")
    time.sleep(1)  # Даем время на активацию приложения и переключение рабочего стола


def _send_notification(title, message):
    """Sends a macOS notification."""
    script = f"""
    display notification \"{message}\" with title \"{title}\" 
    """
    os.system(f"osascript -e '{script}'")


def set_default_screenshot_region(args: str):
    parts = args.split()
    if len(parts) == 4 and all(p.isdigit() for p in parts):
        x, y, width, height = map(int, parts)
        config = load_jafar_config("screenshot_config")
        config["default_region"] = {"x": x, "y": y, "width": width, "height": height}
        save_jafar_config("screenshot_config", config)
        jafar_print(
            f"[bold green]Координаты области скриншота по умолчанию сохранены: x={x}, y={y}, width={width}, height={height}[/bold green]"
        )
    else:
        jafar_print(
            "[bold red]Неверный формат. Используйте: set_default_screenshot_region <x> <y> <width> <height>[/bold red]"
        )


def run_shell_command_for_screenshots(args: str = ""):
    try:
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        script_path = os.path.join(project_root, "take_screenshots.sh")
        base_screenshot_dir = os.path.join(project_root, "screenshot")
        timer_html_path = os.path.join(project_root, "jafar", "utils", "timer.html")

        os.chmod(script_path, 0o755)

        parts = args.split()
        if len(parts) >= 6 and all(p.isdigit() for p in parts[:6]):
            # Автоматический режим: count, delay, x, y, width, height
            count = int(parts[0])
            delay = int(parts[1])
            x = int(parts[2])
            y = int(parts[3])
            width = int(parts[4])
            height = int(parts[5])

            # Создаем уникальную папку для этой серии скриншотов
            timestamp_folder = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            current_batch_dir = os.path.join(base_screenshot_dir, timestamp_folder)
            os.makedirs(current_batch_dir, exist_ok=True)

            jafar_print(
                f"[bold green]Запуск автоматического захвата скриншотов: {count} снимков с задержкой {delay}с, область ({x},{y},{width},{height}). Сохранение в {current_batch_dir}[/bold green]"
            )

            screenshot_files = []
            for i in range(count):
                _activate_safari_and_wait()  # Активируем Safari перед каждым снимком

                # Открываем таймер в Safari
                os.system(f"open -a Safari '{timer_html_path}?delay={delay}'")

                jafar_print(
                    f"[bold green]Скриншот {i+1}/{count} будет сделан через {delay} секунд. Приготовьтесь.[/bold green]"
                )
                time.sleep(delay)

                # Вызываем скрипт take_screenshots.sh с параметрами
                command = (
                    f'{script_path} "{current_batch_dir}" {x} {y} {width} {height}'
                )
                os.system(command)
                jafar_print(f"[bold green]Скриншот {i+1}/{count} сделан![/bold green]")
                # Находим последний созданный файл
                list_of_files = os.listdir(current_batch_dir)
                full_path_files = [
                    os.path.join(current_batch_dir, f) for f in list_of_files
                ]
                if full_path_files:
                    latest_file = max(full_path_files, key=os.path.getctime)
                    screenshot_files.append(latest_file)

            jafar_print(
                "[bold green]Автоматический захват скриншотов завершен![/bold green]"
            )
            _send_notification("Jafar", "Автоматический захват скриншотов завершен!")

            if screenshot_files:
                jafar_print("[bold yellow]Готовы к анализу? (y/n)[/bold yellow]")
                user_input = input("> ").strip().lower()
                if user_input == "y":
                    jafar_print("[bold blue]Запуск анализа скриншотов...[/bold blue]")
                    analysis_result = analyze_screenshot_command(
                        " ".join(screenshot_files)
                    )
                    jafar_print(
                        Panel(
                            analysis_result,
                            title="🤖 Jafar - Анализ скриншота",
                            style="green",
                        )
                    )
                else:
                    jafar_print("[bold yellow]Анализ отменен.[/bold yellow]")

        else:
            # Упрощенный автоматический режим с использованием сохраненных координат
            config = load_jafar_config("screenshot_config")
            default_region = config.get("default_region")

            if default_region:
                x = default_region["x"]
                y = default_region["y"]
                width = default_region["width"]
                height = default_region["height"]
                count = 4  # По умолчанию 4 скриншота
                delay = 5  # По умолчанию 5 секунд задержки

                timestamp_folder = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                current_batch_dir = os.path.join(base_screenshot_dir, timestamp_folder)
                os.makedirs(current_batch_dir, exist_ok=True)

                jafar_print(
                    f"[bold green]Запуск автоматического захвата скриншотов: {count} снимков с задержкой {delay}с, область ({x},{y},{width},{height}). Сохранение в {current_batch_dir}[/bold green]"
                )

                screenshot_files = []
                for i in range(count):
                    _activate_safari_and_wait()  # Активируем Safari перед каждым снимком

                    # Открываем таймер в Safari
                    os.system(f"open -a Safari '{timer_html_path}?delay={delay}'")

                    jafar_print(
                        f"[bold green]Скриншот {i+1}/{count} будет сделан через {delay} секунд. Приготовьтесь.[/bold green]"
                    )
                    time.sleep(delay)

                    command = (
                        f'{script_path} "{current_batch_dir}" {x} {y} {width} {height}'
                    )
                    os.system(command)
                    jafar_print(
                        f"[bold green]Скриншот {i+1}/{count} сделан![/bold green]"
                    )
                    # Находим последний созданный файл
                    list_of_files = os.listdir(current_batch_dir)
                    full_path_files = [
                        os.path.join(current_batch_dir, f) for f in list_of_files
                    ]
                    if full_path_files:
                        latest_file = max(full_path_files, key=os.path.getctime)
                        screenshot_files.append(latest_file)

                jafar_print(
                    "[bold green]Автоматический захват скриншотов завершен![/bold green]"
                )
                _send_notification(
                    "Jafar", "Автоматический захват скриншотов завершен!"
                )

                if screenshot_files:
                    jafar_print("[bold yellow]Готовы к анализу? (y/n)[/bold yellow]")
                    user_input = input("> ").strip().lower()
                    if user_input == "y":
                        jafar_print(
                            "[bold blue]Запуск анализа скриншотов...[/bold blue]"
                        )
                        analysis_result = analyze_screenshot_command(
                            " ".join(screenshot_files)
                        )
                        jafar_print(
                            Panel(
                                analysis_result,
                                title="🤖 Jafar - Анализ скриншота",
                                style="green",
                            )
                        )
                    else:
                        jafar_print("[bold yellow]Анализ отменен.[/bold yellow]")

            else:
                jafar_print(
                    "[bold red]Координаты графика по умолчанию не установлены.[/bold red]"
                )
                jafar_print(
                    "[bold yellow]Пожалуйста, используйте: set_default_screenshot_region <x> <y> <width> <height> для сохранения координат.[/bold yellow]"
                )
    except Exception as e:
        jafar_print(f"[bold red]Ошибка при создании скриншотов: {e}[/bold red]")


from jafar.skills.project_manager.manager import (
    explain_makefile,
    explain_readme,
    load_config,
    project_list,
    project_run,
    project_status,
    project_update,
)
from jafar.skills.project_manager.project_analyzer import analyze_project


def handle_command(command: str, interactive_session: bool = True):
    if not command or not command.strip():
        return

    # --- СПЕЦИАЛЬНЫЙ ПЕРЕХВАТЧИК ДЛЯ QTRADE ---
    if command.strip().startswith('qtrade'):
        try:
            args = command.strip().split(' ', 1)[1]
        except IndexError:
            args = ""
        
        result = qtrade_command(args)
        if result:
            jafar_print(Panel(result, title="🤖 Jafar - QTrade Анализ", style="green"))
        return
    # --- КОНЕЦ ПЕРЕХВАТЧИКА ---

    start_time = time.time()
    status = "failure"
    error_message = None

    try:
        parts = shlex.split(command)
        if not parts:
            return
        action = parts[0].lower().lstrip("/")
        args = " ".join(parts[1:])

        # Проверка статистики ошибок перед выполнением команды
        stats = load_stats()
        if action in stats and stats[action]["failure_rate"] > 30:
            rate = stats[action]["failure_rate"]
            jafar_print(
                Panel(
                    f"⚠️ [bold yellow]Внимание:[/bold yellow] Команда '{action}' имеет высокий процент ошибок ({rate}%) в прошлом. Будьте осторожны.",
                    title="Jafar EVO",
                    style="yellow",
                )
            )

        command_handlers = {
            "ai": ai_command,
            "chat": chat_command,
            "gamemode": lambda _: game_mode_chat(),
            "chatmode": lambda _: chat_mode(),
            "github": github_command,
            "code": code_command,
            "projects": projects_command,
            "file": file_command,
            "project": project_command,
            "pytest": pytest_command,
            "evolve": lambda _: analyze_logs(),
            "help": lambda _: print_help(),
            "-h": lambda _: print_help(),
            "--help": lambda _: print_help(),
            "agent-mode": agent_mode_command,
            "analyze_screenshot": analyze_screenshot_for_plan,
            "scrn": analyze_screenshot_for_plan,
            "addscrn": lambda args: run_shell_command_for_screenshots(args),
            "mt5scrn": mt5_screenshot_command,
            "intraday": intraday_command,
            "qtrade": qtrade_command,
            "atrade": atrade_command,
            "scalp": scalp_command,
            "addfound": analyze_with_fundamental_command,
            "set_default_screenshot_region": lambda args: set_default_screenshot_region(
                args
            ),
            "analyze": start_interactive_analysis,
            "telegram": send_telegram_message,
            "finalize": finalize_analysis,
            "fetch_calendar": fetch_and_save_economic_calendar_data,
        }

        # --- Добавляем поддержку "run <project>" ---
        if action == "run" and args:
            # Универсальная точка: запуск проекта по имени через project_manager
            from jafar.skills.project_manager.manager import project_run

            project_run(args)
            status = "success"

        elif action == "tool":
            from jafar.cli.tool_handlers import tool_command

            tool_command(args)
            status = "success"
        elif action == "push" and args:
            push_project(args)
            status = "success"

        elif action == "next_task" and args:
            parts = args.split(" ")
            repo_identifier = parts[0]
            task_number = None
            if len(parts) > 1 and parts[1].isdigit():
                task_number = int(parts[1])
            next_task(repo_identifier, task_number=task_number)
            status = "success"

        elif action == "run":
            run_project(args.strip())
            status = "success"

        elif action == "prohub":
            if args:
                project_name = args.strip()
                project_path = PROJECTS_ROOT / project_name
                if not project_path.exists():
                    jafar_print(
                        Panel(f"❌ Проект '{project_name}' не найден.", style="red")
                    )
                    status = "failure"
                else:
                    owner, repo = extract_repo_info(str(project_path))
                    if owner and repo:
                        github_inspect(project_name)
                        show_github_issues_and_prs(owner, repo)
                        status = "success"
                    else:
                        jafar_print(
                            "[red]❌ Не удалось определить репозиторий GitHub для инспекции.[/red]"
                        )
                        status = "failure"
            else:
                jafar_print("[red]Укажи имя проекта: prohub tms_backend[/red]")
                status = "failure"
        elif action == "mode":
            from jafar.cli.mode_handlers import mode_command

            mode_command(args)
            status = "success"
        # --- Новый, улучшенный обработчик команд ---
        if action in command_handlers:
            handler = command_handlers[action]
            # Вызываем обработчик и сохраняем результат
            result = handler(args)
            # Если функция вернула что-то (отчет или ошибку), выводим это
            if result:
                # Определяем заголовок панели в зависимости от команды
                panel_title = "🤖 Jafar"
                if action == "analyze_screenshot" or action == "scrn":
                    panel_title = "🤖 Jafar - Анализ скриншота"
                elif action == "addfound":
                    panel_title = "🤖 Jafar - Комплексный анализ"
                
                jafar_print(Panel(result, title=panel_title, style="green"))
            status = "success"
        else:
            code_intent = extract_code_intent(command)
            if code_intent:
                subcmd, arguments = code_intent
                full_code_command = f"{subcmd} {arguments}".strip()
                code_command(full_code_command)
                status = "success"

            elif route_by_intent(command):
                status = "success"
            else:
                ai_response = ask_assistant(command)
                if isinstance(ai_response, dict):
                    explanation = ai_response.get("explanation")
                    command_str = ai_response.get("command")
                    note = ai_response.get("note")

                    message_parts = []
                    if explanation:
                        message_parts.append(str(explanation))
                    if command_str:
                        message_parts.append(f"\n```bash\n{str(command_str)}\n```")
                    if note:
                        message_parts.append(f"\n*Примечание:* {str(note)}")

                    if message_parts:
                        message = "\n".join(message_parts)
                    else:
                        message = repr(
                            ai_response
                        )  # Fallback if nothing useful extracted
                else:
                    message = str(ai_response)
                jafar_print(Panel(message, title="🤖 Jafar", style="green"))
                status = "success"
    except (ValueError, ImportError, KeyError) as e:
        error_message = str(e)
        jafar_print(Panel(f"❌ Ошибка: {e}", title="Исключение", style="bold red"))
        traceback.print_exc()
    finally:
        duration = time.time() - start_time
        log_action(
            command=command,
            status=status,
            duration=duration,
            error_message=error_message,
        )


def chat_mode(start_with=None):
    jafar_print(
        Panel(
            "🌐 [bold cyan]Jafar Chat Mode[/bold cyan]\nПиши, чтобы болтать с ассистентом. Введите [yellow]exit[/yellow] для выхода.",
            title="AI Chat",
            style="blue",
        )
    )
    while True:
        try:
            user_input = start_with if start_with else input("[ты] > ").strip()
            start_with = None  # чтобы не повторилось

            if user_input.lower() in ("exit", "выход", "quit"):
                jafar_print(Panel("👋 Выход из AI-чата", style="dim"))

            if not user_input:
                continue

            response = ask_assistant(user_input)
            message = (
                response.get("message")
                or response.get("explanation")
                or response.get("command")
                or response.get("note")
                or repr(response)
            )
            jafar_print(Panel(message, title="🤖 Jafar", style="green"))

        except (KeyboardInterrupt, EOFError):
            jafar_print(Panel("💤 Выход из AI-чата", style="dim"))
            break


def project_command(args):
    config = load_config()
    if not config:
        jafar_print("[red]Конфигурация пуста.[/red]")
        return

    if args == "list":
        project_list()
        return

    if args == "update":
        project_update()
        return

    if args.startswith("run "):
        name = args.split(" ", 1)[1]
        project_run(name)
        return

    if args == "status":
        project_status()
        return

    if args.startswith("makefile "):
        name = args.split(" ", 1)[1]
        explain_makefile(name)
        return

    if args.startswith("readme "):
        name = args.split(" ", 1)[1]
        explain_readme(name)
        return

    if args.startswith("analyze"):
        parts = shlex.split(args)
        if len(parts) < 2:
            raise ValueError("Укажи имя проекта для анализа.")
        name = parts[1]
        flags = parts[2:] if len(parts) > 2 else []

        if name not in config:
            jafar_print(
                Panel(
                    f"Проект {name} не найден в конфиге.", title="⚠️ Ошибка", style="red"
                )
            )
            jafar_print("[yellow]Перейти в AI-режим для уточнения? (y/n)[/yellow]")
            if input(">> ").strip().lower() == "y":
                return chat_mode()
            else:
                return

        path = config[name]["path"]
        force = "--force" in flags
        reset = "--reset" in flags
        analyze_project(name, path, force=force, reset=reset)
        return

    if args.startswith("summary "):
        name = args.split(" ", 1)[1]
        from jafar.cli.project_handlers import project_summary_command

        project_summary_command(name)
        return

    if args and args in config:
        from jafar.cli.project_handlers import project_summary_command

        project_summary_command(args)
        return

    if args == "help":
        jafar_print(
            Panel(
                "[bold]Доступные команды:[/bold]\n"
                "- [cyan]project list[/cyan] — список проектов\n"
                "- [cyan]project update[/cyan] — обновление всех веток\n"
                "- [cyan]project run <имя>[/cyan] — запуск make run\n"
                "- [cyan]project status[/cyan] — статус файлов проекта\n"
                "- [cyan]project makefile <имя>[/cyan] — объяснение Makefile\n"
                "- [cyan]project readme <имя>[/cyan] — объяснение README.md\n"
                "- [cyan]project analyze <имя> [--force] [--reset][/cyan] — анализ проекта с AI\n"
                "- [cyan]project summary <имя>[/cyan] — сводка по проекту (git + GitHub)",
                title="📦 Project CLI",
                style="cyan",
            )
        )
        return

    # если ничего не подошло — выводим справку
    jafar_print(
        Panel(
            "[bold]Доступные команды:[/bold]\n"
            "- [cyan]project list[/cyan] — список проектов\n"
            "- [cyan]project update[/cyan] — обновление всех веток\n"
            "- [cyan]project run <имя>[/cyan] — запуск make run\n"
            "- [cyan]project status[/cyan] — статус файлов проекта\n"
            "- [cyan]project makefile <имя>[/cyan] — объяснение Makefile\n"
            "- [cyan]project readme <имя>[/cyan] — объяснение README.md\n"
            "- [cyan]project analyze <имя> [--force] [--reset][/cyan] — анализ проекта с AI\n"
            "- [cyan]project summary <имя>[/cyan] — сводка по проекту (git + GitHub)",
            title="📦 Project CLI",
            style="cyan",
        )
    )