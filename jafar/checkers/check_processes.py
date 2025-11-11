# jafar/checkers/check_processes.py
import subprocess

def check_process(name):
    try:
        output = subprocess.check_output(["ps", "aux"]).decode()
        return "running" if name in output else "not running"
    except Exception:
        return "error"
