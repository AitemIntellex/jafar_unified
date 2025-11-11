

import os
import json
import uuid
from datetime import datetime

LOG_FILE_PATH = os.path.expanduser("~/.jafar/structured_log.jsonl")

def log_action(command: str, status: str, duration: float, error_message: str = None):
    """
    Logs a structured event of a command execution.

    Args:
        command (str): The command that was executed.
        status (str): The execution status ('success' or 'failure').
        duration (float): The execution time in seconds.
        error_message (str, optional): The error message if the command failed.
    """
    log_dir = os.path.dirname(LOG_FILE_PATH)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_entry = {
        "operation_id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "command": command,
        "status": status,
        "duration": round(duration, 4),
        "error_message": error_message,
    }

    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except IOError as e:
        # If logging fails, we print an error but don't crash the application
        print(f"Critical: Failed to write to log file {LOG_FILE_PATH}. Error: {e}")


