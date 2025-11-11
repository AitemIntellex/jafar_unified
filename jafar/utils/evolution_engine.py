
import os
import json
from collections import defaultdict

LOG_FILE_PATH = os.path.expanduser("~/.jafar/structured_log.jsonl")
STATS_FILE_PATH = os.path.expanduser("~/.jafar/evolution_stats.json")

def analyze_logs():
    """
    Analyzes the structured logs to generate command execution statistics.
    """
    if not os.path.exists(LOG_FILE_PATH):
        print("Log file not found. Nothing to analyze.")
        return

    command_stats = defaultdict(lambda: {"total_runs": 0, "success": 0, "failure": 0, "total_duration": 0.0})

    with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                log_entry = json.loads(line)
                command = log_entry.get("command", "unknown_command").strip()
                base_command = command.split(" ")[0]

                stats = command_stats[base_command]
                stats["total_runs"] += 1
                stats["total_duration"] += log_entry.get("duration", 0.0)
                if log_entry.get("status") == "success":
                    stats["success"] += 1
                else:
                    stats["failure"] += 1
            except json.JSONDecodeError:
                # Ignore corrupted log lines
                continue

    # Calculate averages and failure rates
    for command, stats in command_stats.items():
        stats["average_duration"] = round(stats["total_duration"] / stats["total_runs"], 4)
        failure_rate = (stats["failure"] / stats["total_runs"]) * 100
        stats["failure_rate"] = round(failure_rate, 2)

    # Save the analysis results
    save_stats(command_stats)
    print(f"Log analysis complete. Stats saved to {STATS_FILE_PATH}")

def save_stats(stats: dict):
    """
    Saves the generated statistics to a file.
    """
    stats_dir = os.path.dirname(STATS_FILE_PATH)
    if not os.path.exists(stats_dir):
        os.makedirs(stats_dir)

    with open(STATS_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4, ensure_ascii=False)

def load_stats() -> dict:
    """
    Loads the generated statistics from a file.
    """
    if not os.path.exists(STATS_FILE_PATH):
        return {}
    with open(STATS_FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

if __name__ == "__main__":
    # This allows running the analysis manually
    analyze_logs()
