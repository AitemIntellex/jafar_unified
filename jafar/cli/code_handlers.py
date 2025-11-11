from pathlib import Path
import os
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from prompt_toolkit import PromptSession
from rich.prompt import Confirm

from jafar.cli.utils import get_projects_root
from jafar.utils.assistant_api import ask_assistant

CODE_LOG_FILE = os.path.expanduser("~/.jafar/code_history.log")
AI_GEN_DIR = "generated_files"
os.makedirs(AI_GEN_DIR, exist_ok=True)
import shutil

console = Console()
global_last_code = None


def handle_code_command(args: str):
    """
    Универсальный обработчик команд code: объяснение, редактирование, сравнение, история и т.д.
    """
    global global_last_code

    args = (args or "").strip()
    if not args or args.lower() in ("help", "-h", "--help"):
        show_code_help()
        return

    if args == "log":
        show_code_log()
        return

    if args.startswith("save"):
        save_code(args)
        return

    if args.startswith("explain"):
        explain_code(args)
        return

    if args.startswith("edit"):
        edit_code(args)
        return

    if args.startswith("compare"):
        compare_code(args)
        return

    # — Новые под-команды —
    if args.startswith("image2dbml"):
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            console.print(
                "[yellow]Укажи путь к изображению: code image2dbml <path>[/yellow]"
            )
            return
        image_path = parts[1]
        prompt = (
            "Convert the ER diagram in the following markdown image link to DBML:\n"
            f"![]({image_path})"
        )
        resp = ask_assistant(prompt)
        msg = resp.get("command") or resp.get("message") or str(resp)
        console.print(Panel(Markdown(msg), title="DBML from image", style="magenta"))
        return

    if args.startswith("image2sql"):
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            console.print(
                "[yellow]Укажи путь к изображению: code image2sql <path>[/yellow]"
            )
            return
        image_path = parts[1]
        prompt = (
            "Convert the ER diagram in the following markdown image link to SQL DDL:\n"
            f"![]({image_path})"
        )
        resp = ask_assistant(prompt)
        msg = resp.get("command") or resp.get("message") or str(resp)
        console.print(Panel(Markdown(msg), title="SQL DDL from image", style="magenta"))
        return

    if args.startswith("generate-models"):
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            console.print(
                "[yellow]Укажи DBML или путь к файлу: code generate-models <dbml_or_path>[/yellow]"
            )
            return
        spec = parts[1]
        if Path(spec).is_file():
            content = Path(spec).read_text(encoding="utf-8")
        else:
            content = spec
        prompt = (
            f"Generate Django model classes from the following DBML schema:\n{content}"
        )
        resp = ask_assistant(prompt)
        code_text = resp.get("command") or resp.get("message") or str(resp)
        console.print(
            Panel(
                Markdown(f"```python\n{code_text}\n```"),
                title="Django Models",
                style="cyan",
            )
        )
        return

    if args.startswith("generate-views"):
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            console.print(
                "[yellow]Укажи модели или путь к файлу: code generate-views <models_or_path>[/yellow]"
            )
            return
        spec = parts[1]
        if Path(spec).is_file():
            content = Path(spec).read_text(encoding="utf-8")
        else:
            content = spec
        prompt = f"Generate Django view functions or class-based views for these models:\n{content}"
        resp = ask_assistant(prompt)
        code_text = resp.get("command") or resp.get("message") or str(resp)
        console.print(
            Panel(
                Markdown(f"```python\n{code_text}\n```"),
                title="Django Views",
                style="cyan",
            )
        )
        return

    if args.startswith("generate-api"):
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            console.print(
                "[yellow]Укажи модели или путь к файлу: code generate-api <models_or_path>[/yellow]"
            )
            return
        spec = parts[1]
        if Path(spec).is_file():
            content = Path(spec).read_text(encoding="utf-8")
        else:
            content = spec
        prompt = f"Generate Django REST Framework serializers and viewsets for these models:\n{content}"
        resp = ask_assistant(prompt)
        code_text = resp.get("command") or resp.get("message") or str(resp)
        console.print(
            Panel(
                Markdown(f"```python\n{code_text}\n```"),
                title="DRF API",
                style="cyan",
            )
        )
        return

    if args.startswith("generate-forms"):
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            console.print(
                "[yellow]Укажи модели или путь к файлу: code generate-forms <models_or_path>[/yellow]"
            )
            return
        spec = parts[1]
        if Path(spec).is_file():
            content = Path(spec).read_text(encoding="utf-8")
        else:
            content = spec
        prompt = f"Generate Django ModelForm classes for these models:\n{content}"
        resp = ask_assistant(prompt)
        code_text = resp.get("command") or resp.get("message") or str(resp)
        console.print(
            Panel(
                Markdown(f"```python\n{code_text}\n```"),
                title="Django Forms",
                style="cyan",
            )
        )
        return

    # Многострочный режим (без параметров или только пробелы)
    if not args:
        console.print(
            Panel(
                "Включён [bold cyan]многострочный режим[/bold cyan]. Заверши ввод через Ctrl+D"
            )
        )
        session = PromptSession(multiline=True)
        user_code = session.prompt()
        global_last_code = user_code
        log_code_action("input", user_code)
        try:
            exec_code(user_code)  # Будь осторожен — eval/exec всегда риск
        except Exception as e:
            console.print(f"[red]Ошибка выполнения кода: {e}[/red]")
            log_code_action("error", str(e))
        return

    # Неизвестная команда (fallback)
    console.print(
        Panel(
            "[yellow]Неизвестная подкоманда! Используй [cyan]code help[/cyan] для справки.[/yellow]",
            title="Ошибка",
            style="red",
        )
    )
    show_code_help()


code_command = handle_code_command


def extract_code_intent(text: str) -> tuple[str, str] | None:
    """Парсит неформальную команду и возвращает (подкоманда, аргументы)."""
    text = text.strip().lower()

    if text.startswith("code "):
        parts = text.split(maxsplit=2)
        return (parts[1], parts[2]) if len(parts) > 2 else (parts[1], "")

    if "объясни" in text:
        return "explain", text.split("объясни", 1)[-1].strip()
    if "измени" in text or "отредактируй" in text:
        return "edit", text.split("измени", 1)[-1].strip()
    if "сравни" in text:
        files = text.split("и")
        if len(files) == 2:
            return "compare", f"{files[0].strip()} {files[1].strip()}"
    if "создай форму" in text:
        return "generate-forms", text.split("создай", 1)[-1].strip()
    if "создай вью" in text or "создай views" in text:
        return "generate-views", text.split("создай", 1)[-1].strip()
    if "сделай api" in text or "генерируй api" in text:
        return "generate-api", text.split("api", 1)[-1].strip()

    return None


def show_code_help():
    md = Markdown(
        """
## 🧠 Команды `code` — AI и работа с файлами

- `code` — многострочный ввод Python-кода (Ctrl+D для завершения)
- `code explain <файл>` — AI объясняет содержимое файла
- `code edit <файл>` — AI предлагает правки кода
- `code compare <файл1> <файл2>` — сравнение содержимого двух файлов
- `code save <имя>` — сохранить последний ввод в `generated_files/`
- `code log` — история действий

---
Примеры:
- `code explain main.py`
- `code compare models.py old_models.py`
- `code save awesome_script.py`
"""
    )
    console.print(Panel(md, title="📘 Code Handler — помощь"))


def show_code_log():
    if not os.path.exists(CODE_LOG_FILE):
        console.print(Panel("Лог пуст. Пока нет истории.", style="dim"))
        return
    content = Path(CODE_LOG_FILE).read_text(encoding="utf-8")
    md = Markdown("## 📜 История кода\n\n```\n" + content[-3000:] + "\n```")
    console.print(Panel(md, title="Code History"))


def log_code_action(label: str, content: str):
    with open(CODE_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n\n[{label.upper()}]\n{content}\n")


def save_code(args: str):
    global global_last_code
    parts = args.split()
    if len(parts) < 2:
        console.print("[yellow]Укажи имя файла: code save <имя.py>[/yellow]")
        return
    if not global_last_code:
        console.print("[red]Нет кода для сохранения. Введи сначала через `code`.[/red]")
        return
    filename = parts[1].strip()
    path = os.path.join(AI_GEN_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(global_last_code)
    console.print(Panel(f"[green]Код сохранён:[/green] {path}"))


def explain_code(args: str):
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        console.print("[yellow]Укажи файл: code explain <имя.py>[/yellow]")
        return
    file_path = parts[1]
    full_path = os.path.join(get_projects_root(), file_path)
    if not os.path.exists(full_path):
        console.print(f"[red]Файл не найден: {file_path}[/red]")
        return
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()

    prompt = f"Объясни, что делает этот код:\n\n```python\n{content[:3000]}\n```"
    response = ask_assistant(prompt)
    msg = response.get("message") or str(response)
    console.print(
        Panel(Markdown(msg), title=f"📘 Объяснение: {file_path}", style="green")
    )


def edit_code(args: str):
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        console.print("[yellow]Укажи файл: code edit <имя.py>[/yellow]")
        return
    file_path = parts[1]
    full_path = os.path.join(get_projects_root(), file_path)
    if not os.path.exists(full_path):
        console.print(f"[red]Файл не найден: {file_path}[/red]")
        return

    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()

    prompt = f"Предложи улучшения к этому коду и верни обновлённый вариант:\n\n```python\n{content[:3000]}\n```"
    response = ask_assistant(prompt)
    if isinstance(response, dict):
        code_text = response.get("command", "") or response.get("message", "")
        explanation = response.get("explanation", "")
    else:
        code_text = str(response)
        explanation = ""

    console.print(
        Panel(
            Markdown(code_text[:3000]),
            title=f"🛠 Редактирование: {file_path}",
            style="cyan",
        )
    )

    if Confirm.ask("💾 Сохранить изменения?", default=True):
        import shutil

        backup_path = full_path + ".bak"
        shutil.copy(full_path, backup_path)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(code_text)

        console.print(
            Panel(
                f"✅ Файл [green]{file_path}[/green] обновлён.\n📦 Бэкап создан: [dim]{backup_path}[/dim]",
                title="Изменения сохранены",
                style="green",
            )
        )
    else:
        console.print("[yellow]❌ Изменения не сохранены[/yellow]")


def compare_code(args: str):
    parts = args.split()
    if len(parts) < 3:
        console.print("[yellow]Пример: code compare file1.py file2.py[/yellow]")
        return
    f1 = os.path.join(get_projects_root(), parts[1])
    f2 = os.path.join(get_projects_root(), parts[2])
    if not os.path.exists(f1) or not os.path.exists(f2):
        console.print("[red]Один из файлов не найден[/red]")
        return
    t1 = Path(f1).read_text(encoding="utf-8").splitlines()
    t2 = Path(f2).read_text(encoding="utf-8").splitlines()

    diffs = []
    for i, (a, b) in enumerate(zip(t1, t2)):
        if a != b:
            diffs.append(f"{i+1:03d}: [-] {a}\n     [+] {b}")
    if len(t1) > len(t2):
        diffs += [f"{i+1:03d}: [-] {line}" for i, line in enumerate(t1[len(t2) :])]
    elif len(t2) > len(t1):
        diffs += [f"{i+1:03d}: [+] {line}" for i, line in enumerate(t2[len(t1) :])]

    if not diffs:
        console.print(Panel("[green]Файлы идентичны[/green]"))
    else:
        md = Markdown("## 🔍 Отличия\\n\\n```\n" + "\\n".join(diffs[:100]) + "\\n```")
        console.print(Panel(md, title="📄 Различия в файлах", style="yellow"))


def edit_file_by_path(filepath: str):
    """
    AI-редактирование файла по абсолютному пути с подтверждением.
    """
    if not Path(filepath).exists():
        console.print(Panel(f"[red]Файл не найден: {filepath}[/red]"))
        return

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    prompt = f"""Файл вызывает ошибки. Предложи улучшения и верни только исправленный код:
```python
{content[:3000]}
```"""

    response = ask_assistant(prompt)
    code_text = response.get("command") or response.get("message") or str(response)

    console.print(
        Panel(
            Markdown(f"```python\n{code_text}\n```"),
            title="🔧 Исправленный код",
            style="cyan",
        )
    )

    if Confirm.ask("💾 Заменить оригинальный файл?", default=False):
        backup_path = filepath + ".bak"
        shutil.copy(filepath, backup_path)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code_text)

        console.print(
            Panel(
                f"✅ Файл [green]{filepath}[/green] обновлён.\n📦 Бэкап создан: [dim]{backup_path}[/dim]",
                title="Сохранено",
                style="green",
            )
        )
    else:
        console.print("[yellow]❌ Изменения не сохранены[/yellow]")
