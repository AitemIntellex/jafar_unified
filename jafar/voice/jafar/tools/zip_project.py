import zipfile
import os
from datetime import datetime
from pathlib import Path

# Игнорируемые директории и файлы
EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    "infra",
    "jafar-old",
    "memory",
    f"jafar_backup_{datetime.now():%Y%m%d_%H%M}.zip",
    f"jafar_structure_{datetime.now():%Y%m%d_%H%M}.zip",
}
EXCLUDE_FILES = {
    "infra.zip",
    "Makefile-old",
    "jafar.db",
    ".DS_Store",
}

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT_DIR
ZIP_NAME = OUTPUT_DIR / f"jafar_structure_{datetime.now():%Y%m%d_%H%M}.zip"


def is_zip_file(filename):
    return filename.endswith(".zip")


# Переименованная функция для проверки исключений
def is_excluded(file_or_dir):
    # Проверка на папки и отдельные файлы
    if file_or_dir in EXCLUDE_DIRS or file_or_dir in EXCLUDE_FILES:
        return True
    # Проверка на расширение .zip
    if is_zip_file(file_or_dir):
        return True
    return False


def should_exclude(path: Path):
    if path.is_dir() and path.name in EXCLUDE_DIRS:
        return True
    if path.is_file() and path.name in EXCLUDE_FILES:
        return True
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return True
    return False


def zip_project():
    with zipfile.ZipFile(ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as zipf:
        for foldername, subfolders, filenames in os.walk(ROOT_DIR):
            folder_path = Path(foldername)
            if should_exclude(folder_path):
                continue
            for filename in filenames:
                file_path = folder_path / filename
                if should_exclude(file_path):
                    continue
                arcname = file_path.relative_to(ROOT_DIR)
                zipf.write(file_path, arcname)
    print(f"✅ Архив создан: {ZIP_NAME}")


if __name__ == "__main__":
    zip_project()
