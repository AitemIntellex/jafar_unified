import json
import os

CONFIG_DIR = os.path.expanduser("~/.jafar_config")

def load_config(config_name: str) -> dict:
    config_path = os.path.join(CONFIG_DIR, f"{config_name}.json")
    if not os.path.exists(config_path):
        return {}
    with open(config_path, 'r') as f:
        return json.load(f)

def save_config(config_name: str, config_data: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    config_path = os.path.join(CONFIG_DIR, f"{config_name}.json")
    with open(config_path, 'w') as f:
        json.dump(config_data, f, indent=4)
