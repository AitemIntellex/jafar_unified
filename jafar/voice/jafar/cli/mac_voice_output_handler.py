import os
import shlex
import subprocess
import time
import re
from rich.console import Console

console = Console()

VOICE_NAME = "Yuri (Enhanced)"
SPEAKING_RATE = 140 # Слов в минуту

def speak_mac_text(text: str):
    """
    Озвучивает текст, используя системную команду 'say' в macOS.
    Ожидает завершения и может быть прервана с помощью Ctrl+C.
    """
    if not text.strip():
        return

    try:
        clean_text = re.sub(r'<[^>]+>', '', text)
        safe_text = shlex.quote(clean_text)
        command = f"say -v '{VOICE_NAME}' -r {SPEAKING_RATE} {safe_text}"
        
        # Используем subprocess.run, чтобы дождаться завершения
        # и позволить Ctrl+C прервать процесс
        subprocess.run(command, shell=True, check=True, capture_output=True)
        
        console.print(f"[green]✅ Сообщение озвучено.[/green]")

    except subprocess.CalledProcessError:
        # Эта ошибка возникает, если процесс был прерван (например, Ctrl+C)
        console.print("\n[yellow]Озвучивание прервано.[/yellow]")
    except KeyboardInterrupt:
        # Дополнительная обработка на случай, если прерывание "просочится" сюда
        console.print("\n[yellow]Озвучивание прервано пользователем.[/yellow]")
    except Exception as e:
        console.print(f"[bold red]❌ Ошибка при озвучивании системным голосом: {e}[/bold red]")
