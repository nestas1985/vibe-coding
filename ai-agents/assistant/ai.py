import requests
import time
from config import MISTRAL_API_KEY, ASSEMBLYAI_API_KEY
from profile import profile_to_text

MODEL = "mistral-small-latest"
API_URL = "https://api.mistral.ai/v1/chat/completions"


def transcribe_voice(audio_path: str) -> str:
    headers = {"authorization": ASSEMBLYAI_API_KEY}

    with open(audio_path, "rb") as f:
        upload = requests.post(
            "https://api.assemblyai.com/v2/upload",
            headers=headers,
            data=f,
            timeout=30,
        )
    audio_url = upload.json()["upload_url"]

    response = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        headers=headers,
        json={"audio_url": audio_url, "language_code": "ru"},
        timeout=30,
    )
    transcript_id = response.json()["id"]

    for _ in range(30):
        time.sleep(2)
        result = requests.get(
            f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
            headers=headers,
            timeout=10,
        )
        status = result.json()["status"]
        if status == "completed":
            return result.json().get("text", "")
        if status == "error":
            return "[ошибка расшифровки]"

    return "[расшифровка заняла слишком долго]"

SYSTEM_PROMPT = """Ты — личный AI-ассистент Станислава. Ты знаешь его хорошо и общаешься как умный, дружелюбный помощник.
Отвечай по-русски. Будь конкретным и кратким. Не используй лишних слов и пустых фраз.

Информация о Станиславе:
{profile}"""


def ask(user_message: str, extra_context: str = "") -> str:
    profile = profile_to_text()
    system = SYSTEM_PROMPT.format(profile=profile)
    if extra_context:
        system += f"\n\nДополнительный контекст:\n{extra_context}"

    response = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.7,
            "max_tokens": 1024,
        },
        timeout=30,
    )
    return response.json()["choices"][0]["message"]["content"]


PRIORITY_EMOJI = {4: "🔴", 3: "🟠", 2: "🔵", 1: ""}


def format_task(i: int, task: dict) -> str:
    priority_icon = PRIORITY_EMOJI.get(task.get("priority", 1), "")
    recurring_icon = " 🔁" if task.get("recurring") else ""
    prefix = f"{priority_icon} " if priority_icon else ""
    return f"{i+1}. {prefix}{task['content']}{recurring_icon}"


def generate_morning_message(tasks: list[dict]) -> str:
    from datetime import date
    today = date.today()
    days = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    day_name = days[today.weekday()]
    date_str = today.strftime("%d.%m.%Y")

    if tasks:
        prompt = f"Напиши одну строку — короткое бодрое утреннее приветствие для Станислава. Сегодня {date_str}, {day_name}. Только приветствие, без задач."
        greeting = ask(prompt)
        tasks_text = "\n".join(format_task(i, t) for i, t in enumerate(tasks))
        return f"{greeting}\n\nУ тебя {len(tasks)} задач на сегодня:\n{tasks_text}\n\n💪"
    else:
        prompt = f"Напиши короткое утреннее сообщение для Станислава. Сегодня {date_str}, {day_name}. Задач нет — пожелай хорошего дня."
        return ask(prompt)


def parse_task_action(text: str) -> dict:
    prompt = f"""Станислав написал: "{text}"

Определи что он хочет сделать с задачами. Варианты:
1. Отметить задачи выполненными — верни {{"action": "complete", "numbers": [1, 3, 5]}}
2. Сделать задачу повторяющейся — верни {{"action": "recurring", "number": 2, "due_string": "every day"}}
3. Добавить новую повторяющуюся задачу — верни {{"action": "add_recurring", "text": "почистить зубы", "due_string": "every day"}}
4. Ничего из этого — верни {{"action": "none"}}

due_string должен быть на английском для Todoist API: "every day", "every monday", "every week", "every month", "every 2 days" и т.д.

Ответь строго в формате JSON."""
    import json
    raw = ask(prompt)
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {"action": "none"}


def process_general_message(text: str) -> dict:
    prompt = f"""Станислав написал: "{text}"

Определи что он хочет:
1. Если просит добавить задачу/задачи — выдели их в список под ключом "tasks", напиши подтверждение под ключом "response".
2. Если задаёт вопрос или просто разговаривает — "tasks" пустой список, ответь под ключом "response".

Ответь строго в формате JSON:
{{"tasks": ["задача 1"], "response": "текст ответа"}}"""
    import json
    raw = ask(prompt)
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {"tasks": [], "response": raw}


def process_evening_reply(reply: str) -> dict:
    prompt = f"""Станислав написал вечером:
"{reply}"

Сделай два дела:
1. Выдели список новых задач которые нужно добавить в планировщик (если есть). Формат: JSON список строк под ключом "tasks".
2. Напиши короткий (2-3 строки) тёплый ответ под ключом "response" — подтверди что записал, скажи что-то поддерживающее.

Ответь строго в формате JSON:
{{"tasks": ["задача 1", "задача 2"], "response": "текст ответа"}}

Если новых задач нет — tasks будет пустым списком."""
    import json
    raw = ask(prompt)
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {"tasks": [], "response": raw}


def analyze_week_for_balance(logs: list) -> dict:
    logs_text = "\n".join(
        f"День {l[0]}: {'ответил вечером' if l[2] else 'нет ответа'}. Текст: {l[2] or '—'}"
        for l in logs
    )
    prompt = f"""Вот записи Станислава за последние 7 дней:
{logs_text}

Оцени каждую сферу его жизни от 1 до 10 на основе того что он писал.
Сферы: Работа, Здоровье, Семья, Саморазвитие, Финансы, Отдых

Ответь строго в формате JSON:
{{"Работа": 7, "Здоровье": 5, "Семья": 8, "Саморазвитие": 6, "Финансы": 4, "Отдых": 3, "summary": "Краткий вывод о неделе в 2-3 предложения"}}"""
    import json
    raw = ask(prompt)
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {}
