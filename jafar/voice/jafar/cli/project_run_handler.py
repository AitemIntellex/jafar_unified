import os
import re
from pathlib import Path
from rich.panel import Panel


def get_makefile_targets(makefile_path):
    targets = []
    if not os.path.exists(makefile_path):
        return targets
    with open(makefile_path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^([a-zA-Z0-9_\-]+):", line)
            if m:
                targets.append(m.group(1))
    return targets


def run_project(project_name):
    project_path = Path(f"/home/jafar/Projects/{project_name}")
    makefile_path = project_path / "Makefile"
    if not makefile_path.exists():
        print(f"❌ В проекте {project_name} нет Makefile!")
        return

    targets = get_make_targets(makefile_path)
    for preferred in ("run", "up", "start"):
        if preferred in targets:
            print(f"🚀 Запускаю {project_name} с помощью make {preferred}...")
            os.chdir(str(project_path))
            os.system(f"make {preferred}")
            return
    print(
        Panel(
            f"❌ Нет целей 'run', 'up' или 'start' в Makefile!\n"
            f"Доступные цели: {', '.join(targets)}",
            title="Makefile Error",
            style="red",
        )
    )
