import os
import tempfile

from prompt_toolkit import PromptSession

def multiline_input(prompt="Ввод (Ctrl+D чтобы закончить):"):
    session = PromptSession(multiline=True)
    print(prompt)
    lines = []
    while True:
        try:
            line = session.prompt("... ")
            lines.append(line)
        except EOFError:
            break
    return "\n".join(lines).strip()


def get_projects_root():
    current = os.path.abspath(__file__)
    projects_root = os.path.abspath(os.path.join(current, "..", "..", "..", ".."))
    return projects_root


def find_files_across_projects(target_filename):
    results = []
    projects_root = get_projects_root()
    # Просматриваем все подпапки (все проекты)
    for project_name in os.listdir(projects_root):
        project_path = os.path.join(projects_root, project_name)
        if not os.path.isdir(project_path):
            continue
        for root, dirs, files in os.walk(project_path):
            if target_filename in files:
                results.append(os.path.join(root, target_filename))
    return results


def find_file_in_projects(filename):
    """
    Расширенный поиск: сначала по всем папкам проектов, потом — по всей Projects,
    а если путь абсолютный — проверяем его напрямую.
    """
    projects_root = get_projects_root()

    # Абсолютный путь — сразу проверяем!
    if os.path.isabs(filename) and os.path.isfile(filename):
        return filename

    # Сначала ищем по базовым проектам
    for project_name in os.listdir(projects_root):
        project_path = os.path.join(projects_root, project_name)
        if not os.path.isdir(project_path):
            continue
        for root, dirs, files in os.walk(project_path):
            if os.path.basename(filename) in files:
                return os.path.join(root, os.path.basename(filename))

    # Дополнительно: ищем везде через glob (на случай если папки не учтены)
    import glob
    matches = glob.glob(os.path.join(projects_root, '**', os.path.basename(filename)), recursive=True)
    if matches:
        return matches[0]

    # Всё равно не найден — возвращаем None
    return None

def write_to_temp_file(content: str) -> str:
    """Записывает контент во временный файл и возвращает его путь."""
    temp_dir = os.path.join(get_projects_root(), "jafar", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    fd, path = tempfile.mkstemp(dir=temp_dir, text=True)
    with os.fdopen(fd, 'w', encoding='utf-8') as tmp:
        tmp.write(content)
    return path

def delete_temp_file(file_path: str):
    """Удаляет временный файл."""
    try:
        os.remove(file_path)
    except OSError as e:
        print(f"Ошибка удаления временного файла {file_path}: {e}")