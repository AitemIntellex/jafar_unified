import subprocess
import sys
import os
from pathlib import Path
from rich.console import Console

console = Console()

# Define a file to store the PID of the background process
PID_FILE = Path("/Users/macbook/.gemini/tmp/super_agent.pid")

def start_super_agent_command(args: str = None):
    console.print("[bold blue]Jafar Super Agentni fon rejimida ishga tushirish...[/bold blue]")
    
    if PID_FILE.exists():
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            # Check if the process is actually running
            if os.kill(pid, 0) is None: # os.kill(pid, 0) checks if process exists without sending a signal
                console.print(f"[yellow]Super Agent allaqachon fon rejimida ishlamoqda (PID: {pid}).[/yellow]")
                return
        except (ValueError, OSError):
            console.print("[yellow]Eski PID fayli topildi, lekin jarayon ishlamayapti. O'chirilmoqda.[/yellow]")
            PID_FILE.unlink(missing_ok=True)

    agent_script_path = Path(__file__).parent.parent / "monitors" / "super_agent.py"
    python_executable = sys.executable

    command = [
        python_executable,
        str(agent_script_path),
        "start" # Argument for the super_agent.py script itself
    ]

    try:
        # Start the process in the background, fully detached
        # For Unix-like systems (macOS/Linux)
        if sys.platform != "win32":
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
        else:
            # For Windows
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        
        pid = process.pid
        with open(PID_FILE, "w") as f:
            f.write(str(pid))
            
        console.print(f"[green]Jafar Super Agent fon rejimida ishga tushirildi! (PID: {pid})[/green]")
        console.print(f"[green]Agentni to'xtatish uchun 'jafar superagent stop' buyrug'idan foydalaning.[/green]")

    except Exception as e:
        console.print(f"[red]❌ Jafar Super Agentni ishga tushirishda xatolik: {e}[/red]")

def stop_super_agent_command(args: str = None):
    console.print("[bold blue]Jafar Super Agentni to'xtatish...[/bold blue]")
    
    if not PID_FILE.exists():
        console.print("[yellow]Super Agent fon rejimida ishlamayapti (PID fayli topilmadi).[/yellow]")
        return

    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        
        # Attempt to terminate the process group to ensure all child processes are killed
        if sys.platform != "win32":
            os.killpg(os.getpgid(pid), 9) # SIGKILL
        else:
            # For Windows, direct process termination
            subprocess.call(['taskkill', '/F', '/PID', str(pid), '/T'])
            
        PID_FILE.unlink(missing_ok=True)
        console.print(f"[green]Jafar Super Agent (PID: {pid}) muvaffaqiyatli to'xtatildi.[/green]")

    except (ValueError, OSError) as e:
        console.print(f"[red]❌ Super Agentni to'xtatishda xatolik: {e}. PID fayli o'chirilmoqda.[/red]")
        PID_FILE.unlink(missing_ok=True)


def status_super_agent_command(args: str = None):
    console.print("[bold blue]Jafar Super Agent holatini tekshirish...[/bold blue]")

    if not PID_FILE.exists():
        console.print("[yellow]Super Agent fon rejimida ishlamayapti (PID fayli topilmadi).[/yellow]")
        return

    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        
        if os.kill(pid, 0) is None: # Check if process exists
            console.print(f"[green]Super Agent fon rejimida ishlamoqda (PID: {pid}).[/green]")
        else:
            console.print("[yellow]Super Agent ishlamayapti (PID fayli mavjud, lekin jarayon topilmadi). PID fayli o'chirilmoqda.[/yellow]")
            PID_FILE.unlink(missing_ok=True)
    except (ValueError, OSError) as e:
        console.print(f"[red]❌ Super Agent holatini tekshirishda xatolik: {e}. PID fayli o'chirilmoqda.[/red]")
        PID_FILE.unlink(missing_ok=True)
