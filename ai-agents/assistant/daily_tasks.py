import json
from pathlib import Path
from datetime import date

TASKS_FILE = Path(__file__).parent / "daily_tasks.json"


def save_daily_tasks(tasks: list[dict]):
    data = {"date": date.today().isoformat(), "tasks": tasks}
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_daily_tasks() -> list[dict]:
    if not TASKS_FILE.exists():
        return []
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("date") != date.today().isoformat():
        return []
    return data.get("tasks", [])
