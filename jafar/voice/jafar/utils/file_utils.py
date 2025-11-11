
import os
from rich.console import Console

console = Console()

def read_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        console.print(f"[red]❌ Ошибка чтения файла: {e}[/red]")
        return None

def write_file(file_path, content):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        console.print(f"[red]❌ Ошибка записи в файл: {e}[/red]")

def delete_file(file_path):
    try:
        os.remove(file_path)
        console.print(f"[green]✅ Файл {file_path} удалён.[/green]")
    except Exception as e:
        console.print(f"[red]❌ Ошибка удаления файла: {e}[/red]")

def find_file(file_name, search_path='.'):
    for root, dirs, files in os.walk(search_path):
        if file_name in files:
            return os.path.join(root, file_name)
    return None
