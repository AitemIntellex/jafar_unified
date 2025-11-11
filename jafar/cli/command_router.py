import os
import shlex
import time
import traceback
from datetime import datetime
import subprocess
import sys

from rich.console import Console
from rich.panel import Panel

console = Console()

from jafar.utils.assistant_api import ask_assistant
from jafar.utils.structured_logger import log_action
from jafar.utils.evolution_engine import analyze_logs, load_stats
from .ai_handlers import ai_command
from .chat_handlers import chat_command
from .check_handlers import check_command
from .code_handlers import code_command, extract_code_intent, show_code_help
from .file_handlers import file_command
from .game_handlers import game_mode_chat
from .github_handlers import (
    github_command,
    github_inspect,
    next_task,
    push_project,
    show_github_issues_and_prs,
)
from .intent_router import route_by_intent
from .print_help import print_help
from .project_handlers import projects_command
from .project_run_handler import run_project
from .agent_handlers import agent_mode_command
from .pytest_handlers import pytest_command
from .image_analysis_handler import analyze_screenshot_command
from .news_handler import process_news_command
from .atrade_handlers import atrade_command
from .interactive_analyzer import start_interactive_analysis
from .order_handlers import list_orders_command, cancel_order_command, modify_order_command
from .utils import multiline_input
from ..utils.config_manager import load_config as load_jafar_config, save_config as save_jafar_config

def _activate_safari_and_wait():
    pass
def handle_command(command: str, interactive_session: bool = True):
    if not command or not command.strip():
        return

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
            console.print(
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
            "analyze_screenshot": analyze_screenshot_command,
            "scrn": analyze_screenshot_command,
            "addscrn": lambda args: run_shell_command_for_screenshots(args),
            "set_default_screenshot_region": lambda args: set_default_screenshot_region(args),
            "news": process_news_command,
            "atrade": atrade_command,
            "analyze": start_interactive_analysis,
            "orders": list_orders_command,
            "order_cancel": cancel_order_command,
            "order_modify": modify_order_command,
        }

        # --- Добавляем поддержку "run <project>" ---
        if action == "run" and args:
            # Универсальная точка: запуск проекта по имени через project_manager
            from .project_run_handler import run_project as project_run

            project_run(args)
            status = "success"

        elif action == "tool":
            from .tool_handlers import tool_command

            tool_command(args)
            status = "success"
        elif action == "push" and args:
            push_project(args)
            status = "success"

        elif action == "next_task" and args:
            parts = args.split(" ")
            project_name = parts[0]
            task_number = None
            if len(parts) > 1 and parts[1].isdigit():
                task_number = int(parts[1])
            next_task(project_name, task_number=task_number)
            status = "success"

        elif action == "run":
            run_project(args.strip())
            status = "success"

        elif action == "prohub":
            if args:
                github_inspect(args)
                show_github_issues_and_prs(args)
            else:
                console.print("[red]Укажи имя проекта: prohub tms_backend[/red]")
            status = "success"
        elif action == "mode":
            from .mode_handlers import mode_command

            mode_command(args)
            status = "success"
        elif action == "analyze_screenshot":
            result = command_handlers[action](args)
            console.print(
                Panel(result, title="🤖 Jafar - Анализ скриншота", style="green")
            )
            status = "success"
        elif action in command_handlers:
            command_handlers[action](args)
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
                    message = (
                        ai_response.get("message")
                        or ai_response.get("explanation")
                        or ai_response.get("command")
                        or ai_response.get("note")
                        or repr(ai_response)
                    )
                else:
                    message = str(ai_response)
                console.print(Panel(message, title="🤖 Jafar", style="green"))
                status = "success"
    except (ValueError, ImportError, KeyError) as e:
        error_message = str(e)
        console.print(Panel(f"❌ Ошибка: {e}", title="Исключение", style="bold red"))
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
    console.print(
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
                console.print(Panel("👋 Выход из AI-чата", style="dim"))
                break

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
            console.print(Panel(message, title="🤖 Jafar", style="green"))

        except (KeyboardInterrupt, EOFError):
            console.print(Panel("💤 Выход из AI-чата", style="dim"))
            break


def project_command(args):
    config = load_config()
    if not config:
        console.print("[red]Конфигурация пуста.[/red]")
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
            console.print(
                Panel(
                    f"Проект {name} не найден в конфиге.", title="⚠️ Ошибка", style="red"
                )
            )
            console.print("[yellow]Перейти в AI-режим для уточнения? (y/n)[/yellow]")
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
        from .project_handlers import project_summary_command

        project_summary_command(name)
        return

    if args and args in config:
        from .project_handlers import project_summary_command

        project_summary_command(args)
        return

    if args == "help":
        console.print(
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
    console.print(
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
