import zipfile
import os
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_FILE = ROOT_DIR / f"devdrive_backup_{datetime.now():%Y%m%d_%H%M}.zip"

EXCLUDED_DIRS = {
    ".git", ".venv", "__pycache__", ".pytest_cache",
    "tms_backend", "tms_frontend", ".mypy_cache"
}
EXCLUDED_FILES = {
    "infra.zip", "Makefile-old", "jafar.db", ".DS_Store"
}
EXCLUDED_EXT = {".pyc", ".log", ".sqlite3", ".zip"}

def should_exclude(path: Path):
    if path.is_dir() and path.name in EXCLUDED_DIRS:
        return True
    if path.is_file() and (path.name in EXCLUDED_FILES or path.suffix in EXCLUDED_EXT):
        return True
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return True
    return False

def zip_devdrive():
    with zipfile.ZipFile(OUTPUT_FILE, "w", zipfile.ZIP_DEFLATED) as zipf:
        for foldername, _, filenames in os.walk(ROOT_DIR):
            folder_path = Path(foldername)
            if should_exclude(folder_path):
                continue
            for filename in filenames:
                file_path = folder_path / filename
                if should_exclude(file_path):
                    continue
                arcname = file_path.relative_to(ROOT_DIR)
                zipf.write(file_path, arcname)
    print(f"✅ Архив создан: {OUTPUT_FILE}")

if __name__ == "__main__":
    zip_devdrive()
