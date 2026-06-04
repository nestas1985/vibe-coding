from todoist_api_python.api import TodoistAPI
from config import TODOIST_API_KEY
from datetime import date

api = TodoistAPI(TODOIST_API_KEY)


def _all_tasks():
    pages = list(api.get_tasks())
    return [t for page in pages for t in page]


def get_tasks_today() -> list[str]:
    try:
        today = date.today()
        tasks = _all_tasks()
        result = []
        for t in tasks:
            if t.due and t.due.date <= today:
                result.append(t.content)
        return result
    except Exception as e:
        print(f"Todoist error: {e}")
        return []


def add_task(text: str) -> bool:
    try:
        api.add_task(content=text, due_string="today")
        return True
    except Exception as e:
        print(f"Todoist add error: {e}")
        return False


def add_tasks(texts: list[str]) -> int:
    return sum(1 for t in texts if add_task(t))
