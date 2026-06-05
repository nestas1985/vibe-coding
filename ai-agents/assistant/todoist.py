from todoist_api_python.api import TodoistAPI
from config import TODOIST_API_KEY
from datetime import date

api = TodoistAPI(TODOIST_API_KEY)


def _all_tasks():
    pages = list(api.get_tasks())
    return [t for page in pages for t in page]


def get_tasks_today() -> list[dict]:
    try:
        today = date.today()
        tasks = _all_tasks()
        result = []
        for t in tasks:
            if t.due and t.due.date <= today:
                result.append({
                    "id": t.id,
                    "content": t.content,
                    "recurring": t.due.is_recurring if t.due else False,
                    "priority": t.priority,
                })
        return result
    except Exception as e:
        print(f"Todoist error: {e}")
        return []


def add_task(text: str, due_string: str = "today") -> bool:
    try:
        api.add_task(content=text, due_string=due_string)
        return True
    except Exception as e:
        print(f"Todoist add error: {e}")
        return False


def add_tasks(texts: list[str]) -> int:
    return sum(1 for t in texts if add_task(t))


def complete_task(task_id: str) -> bool:
    try:
        api.close_task(task_id=task_id)
        return True
    except Exception as e:
        print(f"Todoist complete error: {e}")
        return False


def set_priority(task_id: str) -> bool:
    try:
        api.update_task(task_id=task_id, priority=4)
        return True
    except Exception as e:
        return False


def set_recurring(task_id: str, due_string: str) -> bool:
    try:
        api.update_task(task_id=task_id, due_string=due_string)
        return True
    except Exception as e:
        print(f"Todoist recurring error: {e}")
        return False


def get_task_id_by_index(tasks: list[dict], index: int) -> str | None:
    if 0 <= index < len(tasks):
        return tasks[index]["id"]
    return None
