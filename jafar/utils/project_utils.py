# /home/jafar/Projects/jafar_v2/jafar/utils/project_utils.py
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "projects_config.json"


def get_project_info(project_name: str) -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = json.load(f)
    return config.get(project_name, {})
