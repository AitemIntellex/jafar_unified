from datetime import datetime
from rich.console import Console
from rich.panel import Panel
import subprocess
import glob
import os
import time

try:
    from prompt_toolkit import PromptSession
except ImportError:
    PromptSession = None

from jafar.cli.evolution import log_evolution_event, start_learning
from jafar.cli.utils import (
    find_file_in_projects,
    find_files_across_projects,
    get_projects_root,
)
from jafar.assistant_core.assistant_api import ask_assistant
from jafar.cli.code_handlers import code_command
from jafar.cli.github_handlers import github_command

console = Console()

IGNORED_FOLDERS = {
    ".venv",
    "venv",
    "node_modules",
    ".pytest_cache",
    ".git",
    "site-packages",
    "__pycache__",
    "backups",
    "tests",
}


def evo_mode():
    project_root = get_projects_root()
    plan = traverse_project_smart(project_root)
    if not plan:
        console.print(Panel("❌ Проект пуст или не найден!", style="red"))
        return

    console.print(
        Panel(
            "🧬 [bold cyan]Jafar EVO Mode[/bold cyan]\n"
            "В этом режиме ты вручную управляешь каждым шагом.\n"
            "Доступны хэндлеры: code, github, file, project и др.\n"
            "Введи нужную команду для действия. Автоматического перехода нет.",
            title="Evo Branch / Lab",
            style="blue",
        )
    )

    idx = 0
    while idx < len(plan):
        cur_file = plan[idx]
        abs_path = os.path.join(project_root, cur_file)
        try:
            with open(abs_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            console.print(Panel(f"Ошибка чтения файла: {e}", style="red"))
            idx += 1
            continue

        # Анализ файла — но не делаем переход к следующему!
        prompt = f"""Ты AI-ревьюер... (твой промпт, как в предыдущих версиях)"""
        answer = ask_assistant(prompt)
        msg = answer.get("message") or answer.get("explanation") or str(answer)
        console.print(
            Panel(msg[:2500], title=f"🤖 AI анализ: {cur_file}", style="green")
        )
        log_evolution_event("evolution_step", f"{cur_file} | {msg}")

        # Ожидание явной команды!
        while True:
            console.print(
                Panel(
                    "🔸 [next] — следующий | [repeat] — ещё раз | [skip] — пропустить | "
                    "[code ...], [github ...], [file ...], [project ...] — запусти навык | [exit/stop] — выйти",
                    style="magenta",
                )
            )
            if PromptSession:
                session = PromptSession()
                user = session.prompt("[evo] > ").strip()
            else:
                user = input("[evo] > ").strip()

            user_lc = user.lower()
            if user_lc in ("exit", "stop", "quit"):
                console.print(Panel("🛑 EVO Mode завершён.", style="yellow"))
                return
            elif user_lc == "repeat":
                break  # Заново анализируем текущий файл
            elif user_lc == "skip":
                idx += 1
                break
            elif user_lc == "next":
                idx += 1
                break
            elif user_lc.startswith("code "):
                from jafar.cli.code_handlers import code_command

                code_command(user[5:].strip())
                continue
            elif user_lc.startswith("github "):
                from jafar.cli.github_handlers import github_command

                github_command(user[7:].strip())
                continue
            elif user_lc.startswith("file "):
                from jafar.cli.file_handlers import file_command

                file_command(user[5:].strip())
                continue
            elif user_lc.startswith("project "):
                from jafar.cli.project_handlers import project_command

                project_command(user[8:].strip())
                continue
            else:
                console.print(
                    Panel(
                        "Введи конкретную команду ([next], [skip], [code ...], ...)",
                        style="yellow",
                    )
                )
                continue


def traverse_project_smart(project_root):
    docs, entrypoints, configs, py_files, other_files = [], [], [], [], []

    for dirpath, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in IGNORED_FOLDERS]
        for fname in files:
            fpath = os.path.join(dirpath, fname)
            rel = os.path.relpath(fpath, project_root)
            if fname.lower() in ("readme.md", "readme.txt", "instructions.md"):
                docs.append(rel)
            elif fname.lower() in (
                "makefile",
                "pyproject.toml",
                "setup.py",
                "requirements.txt",
            ):
                configs.append(rel)
            elif fname.lower() in ("main.py", "manage.py", "app.py"):
                entrypoints.append(rel)
            elif fname.endswith(".py"):
                py_files.append(rel)
            else:
                other_files.append(rel)
    # Сначала jafar/jafar_v2, потом остальное
    plan = (
        [x for x in docs if x.startswith("jafar") or x.startswith("jafar_v2")]
        + [x for x in configs if x.startswith("jafar") or x.startswith("jafar_v2")]
        + [x for x in entrypoints if x.startswith("jafar") or x.startswith("jafar_v2")]
        + [x for x in py_files if x.startswith("jafar") or x.startswith("jafar_v2")]
        + [x for x in docs if not (x.startswith("jafar") or x.startswith("jafar_v2"))]
        + [
            x
            for x in configs
            if not (x.startswith("jafar") or x.startswith("jafar_v2"))
        ]
        + [
            x
            for x in entrypoints
            if not (x.startswith("jafar") or x.startswith("jafar_v2"))
        ]
        + [
            x
            for x in py_files
            if not (x.startswith("jafar") or x.startswith("jafar_v2"))
        ]
        + other_files
    )
    return plan


def smartevo_traverse():
    project_root = get_projects_root()
    plan = traverse_project_smart(project_root)
    if not plan:
        console.print(Panel("❌ Проект пуст или не найден!", style="red"))
        return

    console.print(
        Panel(
            "🧭 [bold cyan]Jafar SMART Traversal[/bold cyan]\n"
            "Анализ начинается с документации и точек входа проекта.\n"
            "Jafar предложит план, а ты сможешь скорректировать его вручную.",
            title="Smart Evolution",
            style="blue",
        )
    )

    console.print(
        Panel(
            "🔍 План обхода проекта:\n"
            + "\n".join(plan[:15])
            + ("\n..." if len(plan) > 15 else ""),
            title="Стартовый порядок анализа",
            style="yellow",
        )
    )

    idx = 0
    while idx < len(plan):
        cur_file = plan[idx]
        abs_path = os.path.join(project_root, cur_file)
        try:
            with open(abs_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            console.print(Panel(f"Ошибка чтения файла: {e}", style="red"))
            idx += 1
            continue

        # Универсальный промпт для экшн-айтомов!
        prompt = f"""
Ты AI-ревьюер и рефактор.
Вот файл: {cur_file}
---
{content[:3500]}
---
1. Дай краткое описание файла (1-2 предложения).
2. Есть ли проблемы, ошибки, недочеты?
3. Перечисли конкретные TODO/Action Items (отдельным списком) для улучшения этого файла, если нужно.
4. Как это связано с архитектурой jafar_v2/jafar?
Ответ верни в формате:
Описание: ...
TODO:
- ...
- ...
"""
        answer = ask_assistant(prompt)
        msg = answer.get("message") or answer.get("explanation") or str(answer)
        console.print(
            Panel(msg[:2500], title=f"🤖 AI анализ: {cur_file}", style="green")
        )
        log_evolution_event("evolution_step", f"{cur_file} | {msg}")

        # ------ КОНТРОЛЬ/РОУТИНГ ------
        console.print(
            Panel(
                "🔸 [next] — следующий | [repeat] — ещё раз | [skip] — пропустить | "
                "[code ...] — запустить code-хэндлер | [exit/stop] — выйти",
                style="magenta",
            )
        )

        if PromptSession:
            session = PromptSession()
            user = session.prompt("[smartevo] > ").strip()
        else:
            user = input("[smartevo] > ").strip()

        user_lc = user.lower()
        if user_lc in ("exit", "stop", "quit"):
            console.print(Panel("🛑 Evolution Mode завершён.", style="yellow"))
            break
        elif user_lc == "repeat":
            continue
        elif user_lc == "skip":
            idx += 1
            continue
        elif user_lc.startswith("code "):
            # --- Вызов code-хэндлера прямо тут! ---
            from jafar.cli.code_handlers import code_command

            code_command(user[5:].strip())
            continue
        # Добавляй любые другие навыки по аналогии:
        elif user_lc.startswith("github "):
            from jafar.cli.github_handlers import github_command

            github_command(user[7:].strip())
            continue
        elif user_lc == "next":
            idx += 1
            continue

    console.print(
        Panel(
            "Обход текущего проекта завершён. Перейти к соседнему проекту? [y/n]",
            style="cyan",
        )
    )
    answer = input("[smartevo] > ").strip().lower()
    if answer == "y":
        # TODO: реализуй свою логику выбора другого проекта
        pass


def autonomous_evolution_mode():
    """Автоматический режим: просто логирует шаги или вызывает evolution.py по таймеру."""
    project_root = get_projects_root()
    evolution_script = None
    for root, dirs, files in os.walk(project_root):
        if "evolution.py" in files:
            evolution_script = os.path.join(root, "evolution.py")
            break

    if not evolution_script:
        console.print(Panel("Файл evolution.py не найден в проекте!", style="red"))
        return

    console.print(
        Panel(
            "🚀 [bold cyan]Evolution Mode[/bold cyan]\n"
            "Автоматический запуск evolution.py по шагам.\n"
            "Остановить — Ctrl+C.",
            title="Autonomous Evolution",
            style="blue",
        )
    )

    step = 1
    while True:
        try:
            console.print(Panel(f"[Step {step}] Запуск evolution.py…", style="cyan"))
            result = subprocess.run(
                ["python3", evolution_script],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(evolution_script),
            )
            output = (result.stdout or "") + (
                "\n[stderr]\n" + result.stderr if result.stderr else ""
            )
            console.print(
                Panel(output[:5000], title=f"🧬 Evolution step {step}", style="magenta")
            )
            step += 1
            console.print(Panel("Пауза перед следующим шагом (5 сек)...", style="dim"))
            time.sleep(5)
        except KeyboardInterrupt:
            console.print(
                Panel("🛑 Evolution Mode остановлен пользователем.", style="yellow")
            )
            break
        except Exception as e:
            console.print(Panel(f"Ошибка в Evolution Mode: {e}", style="red"))
            break


def find_py_files(pattern="*.py"):
    project_root = get_projects_root()
    return [
        os.path.relpath(f, project_root)
        for f in glob.glob(f"{project_root}/**/{pattern}", recursive=True)
    ]


def run_py_file(filename):
    project_root = get_projects_root()
    matches = glob.glob(f"{project_root}/**/{filename}", recursive=True)
    if not matches:
        console.print(
            Panel(
                f"Файл {filename} не найден. Попробуй 'run ?' для списка.", style="red"
            )
        )
        return
    filepath = matches[0]
    result = subprocess.run(["python3", filepath], capture_output=True, text=True)
    out = result.stdout
    err = result.stderr
    title = f"💻 Output: {os.path.relpath(filepath, project_root)}"
    msg = out + (("\n[stderr]\n" + err) if err else "")
    console.print(Panel(msg[:5000], title=title, style="magenta"))


def handle_run_command(args):
    if not args or args.strip() == "?":
        files = find_py_files()
        if not files:
            console.print(Panel("Python-файлы не найдены!", style="yellow"))
            return
        out = "\n".join(files)
        console.print(Panel(out, title="🗂 Все доступные .py-файлы", style="cyan"))
        return
    run_py_file(args.strip())


def game_mode_chat():
    console.print(
        Panel(
            "🎮 [bold cyan]Jafar Game Mode[/bold cyan]\n"
            "[yellow]Локальные команды: ls, cd <dir>, run <py>, evolution, smartevo, ...\n"
            "AI — просто набери вопрос или команду на любом языке.[/yellow]\n"
            "exit/выход/quit — выход | help/помощь — справка.",
            title="AI GameMode | Игровой режим",
            style="blue",
        )
    )

    cwd = os.path.basename(os.getcwd())
    while True:
        try:
            prompt = f"[{cwd}] > "
            user_input = input(prompt).strip()
            if user_input in ("/ml", "/multiline"):
                if PromptSession:
                    session = PromptSession(multiline=True)
                    user_input = session.prompt("... (Ctrl+D — отправить)\n").strip()
                else:
                    console.print(
                        Panel(
                            "prompt_toolkit не установлен — только однострочный режим.",
                            style="yellow",
                        )
                    )
                    continue
            if not user_input:
                continue

            if user_input.lower() in ("exit", "выход", "quit"):
                console.print(
                    Panel("💤 Выход из AI-GameMode | Exit AI-GameMode", style="dim")
                )
                break

            if user_input.lower() in ("help", "помощь"):
                console.print(
                    Panel(
                        "[cyan]Локальные команды:\n"
                        "- ls, dir — список файлов\n"
                        "- cd <dir> — смена директории\n"
                        "- run <file.py> — запуск .py\n"
                        "- evolution — автоматическая эволюция\n"
                        "- smartevo — умный AI-проход по всем .py\n"
                        "- /ml — многострочный ввод\n"
                        "- exit — выход\n"
                        "Просто текст — AI чат/анализ\n"
                        "[/cyan]",
                        style="cyan",
                    )
                )
                continue

            # Локальные команды
            if user_input in ("ls", "dir"):
                files = os.listdir(os.getcwd())
                console.print(
                    Panel("\n".join(files), title=f"📂 {os.getcwd()}", style="blue")
                )
                continue

            if user_input.lower() in ("evo", "evo_mode", "evobranch"):
                evo_mode()
                continue

            if user_input.startswith("cd "):
                new_dir = user_input[3:].strip()
                try:
                    os.chdir(new_dir)
                    cwd = os.path.basename(os.getcwd())
                    console.print(
                        Panel(f"📂 Текущая директория: {os.getcwd()}", style="blue")
                    )
                except Exception as e:
                    console.print(Panel(f"Ошибка смены директории: {e}", style="red"))
                continue

            if user_input.startswith("run"):
                args = user_input[3:].strip()
                handle_run_command(args)
                continue

            if user_input.lower() in ("evolution", "эволюция"):
                autonomous_evolution_mode()
                continue

            if user_input.lower() in ("smartevo", "умнаяэволюция", "smart_evo"):
                smartevo_traverse()
                continue
            if user_input.startswith("code "):
                code_command(user_input[5:].strip())
                continue

            if user_input.startswith("github "):
                github_command(user_input[7:].strip())
                continue

            if user_input.startswith("python ") and user_input.endswith(".py"):
                py_file = user_input.split(" ", 1)[1].strip()
                if not os.path.isfile(py_file):
                    console.print(Panel(f"Файл {py_file} не найден.", style="red"))
                    continue
                result = subprocess.run(
                    ["python3", py_file], capture_output=True, text=True
                )
                console.print(
                    Panel(
                        result.stdout
                        + (("\n" + result.stderr) if result.stderr else ""),
                        title=f"💻 Output: {py_file}",
                        style="magenta",
                    )
                )
                continue

            if user_input.startswith(("файл ", "file ")):
                tokens = user_input.split(" ", 2)
                filename = tokens[1].strip()
                extra_instruction = tokens[2].strip() if len(tokens) > 2 else ""
                path = find_file_in_projects(filename)
                if path:
                    with open(path, encoding="utf-8") as f:
                        content = f.read()
                    console.print(
                        Panel(
                            content[:3000], title=f"Файл/File: {path}", style="magenta"
                        )
                    )
                    instruction = (
                        extra_instruction + "\n\n" if extra_instruction else ""
                    ) + f"Вот содержимое файла:\n\n{content[:3000]}"
                    answer = ask_assistant(instruction)
                    msg = answer.get("message") or str(answer)
                    console.print(
                        Panel(
                            msg,
                            title="🤖 AI анализ файла | File analysis",
                            style="green",
                        )
                    )
                else:
                    console.print(
                        Panel(
                            f"Файл/File '{filename}' не найден/not found.", style="red"
                        )
                    )
                continue

            if user_input.startswith(("поиск ", "find ")):
                filename = user_input.split(" ", 1)[1].strip()
                paths = find_files_across_projects(filename)
                if paths:
                    found = "\n".join(paths)
                    console.print(
                        Panel(
                            found,
                            title="🔍 Найдено файлов | Files found",
                            style="yellow",
                        )
                    )
                else:
                    console.print(
                        Panel(
                            f"Файлы/Files '{filename}' не найдены/not found.",
                            style="red",
                        )
                    )
                continue

            if user_input.startswith("calc "):
                expr = user_input[5:].strip()
                try:
                    result = eval(expr, {"__builtins__": {}}, {})
                    console.print(
                        Panel(str(result), title="🧮 Calculator", style="yellow")
                    )
                except Exception as e:
                    console.print(Panel(f"Ошибка калькулятора: {e}", style="red"))
                continue

            # Всё остальное — AI-чат/анализ!
            answer = ask_assistant(user_input)
            msg = (
                answer.get("message")
                or answer.get("explanation")
                or answer.get("command")
                or answer.get("note")
                or str(answer)
            )
            console.print(Panel(msg, title="🤖 Jafar (AI-чат/Chat)", style="green"))

        except (KeyboardInterrupt, EOFError):
            console.print(
                Panel("💤 Выход из AI-GameMode | Exit AI-GameMode", style="dim")
            )
            break
        except Exception as e:
            console.print(Panel(f"Ошибка/Error: {e}", style="red"))
