# checkers/check_git.py
import subprocess

def check_git_status():
    try:
        result = subprocess.check_output(["git", "status", "-s"]).decode()
        return "clean" if result.strip() == "" else "changes"
    except Exception:
        return "not a repo"
