import os
import glob
import zipfile
from rich.console import Console
from rich.panel import Panel
from jafar.cli.utils import find_file_in_projects
from jafar.assistant_core.assistant_api import ask_assistant

console = Console()

def smart_file_handler(user_input):
    # Пример: "файл file1.py file2.py *.md архив.zip опиши структуру"
    tokens = user_input.split()
    if len(tokens) < 2:
        console.print(Panel("Нужно указать хотя бы один файл или шаблон!", style="red"))
        return

    # Отделяем все "файлы/шаблоны" и возможную инструкцию
    patterns = []
    for i, token in enumerate(tokens[1:], 1):
        # Если явно инструкция (ключевое слово или длинный текст)
        if token.startswith("опиши") or token.startswith("explain") or token.startswith("analyze") or len(token) > 20:
            break
        patterns.append(token)
    # Остальные токены — это уже инструкция
    instruction = " ".join(tokens[i:]).strip() if i < len(tokens) else ""

    # Расширяем паттерны (wildcard, список)
    found_files = []
    for pattern in patterns:
        # Абсолютный путь? — Используй как есть.
        if os.path.isabs(pattern) and os.path.exists(pattern):
            found_files.append(pattern)
        else:
            # wildcard (glob по всем подпапкам проекта)
            matches = glob.glob(f"**/{pattern}", recursive=True)
            found_files.extend(matches)

    if not found_files:
        console.print(Panel(f"Файлы по шаблону/имени не найдены: {' '.join(patterns)}", style="red"))
        return

    for filepath in found_files:
        if filepath.endswith(".zip"):
            # Анализ zip-архива
            try:
                with zipfile.ZipFile(filepath) as zf:
                    filelist = zf.namelist()
                    tree_view = "\n".join(filelist)
                    # Можем взять только первые N файлов для анализа, если архив большой
                    sample_files = filelist[:5]
                    files_content = ""
                    for name in sample_files:
                        if name.endswith(('.py', '.md', '.txt')):
                            try:
                                with zf.open(name) as f:
                                    content = f.read().decode("utf-8", errors="ignore")
                                    files_content += f"\n--- {name} ---\n{content[:1000]}"
                            except Exception:
                                pass
                    message = f"ZIP-архив: {filepath}\n\nСписок файлов:\n{tree_view}\n\nОбразцы файлов:\n{files_content}"
                    task = f"{instruction or 'Проанализируй структуру архива и опиши архитектуру проекта.'}\n\n{message}"
                    answer = ask_assistant(task)
                    msg = answer.get("message") or str(answer)
                    console.print(Panel(msg, title=f"🤖 Анализ архива: {os.path.basename(filepath)}", style="green"))
            except Exception as e:
                console.print(Panel(f"Ошибка при анализе zip: {e}", style="red"))
            continue

        # Анализ обычных файлов (текстовых, py, md и т.д.)
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
            preview = content[:3000]
            console.print(Panel(preview, title=f"Файл: {filepath}", style="magenta"))
            task = f"{instruction or 'Поясни/опиши этот файл.'}\n\n{preview}"
            answer = ask_assistant(task)
            msg = answer.get("message") or str(answer)
            console.print(Panel(msg, title=f"🤖 Анализ файла: {os.path.basename(filepath)}", style="green"))
        except Exception as e:
            console.print(Panel(f"Ошибка при чтении файла {filepath}: {e}", style="red"))
