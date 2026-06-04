from groq import Groq
from config import GROQ_API_KEY
from profile import profile_to_text

client = Groq(api_key=GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """Ты — личный AI-ассистент Станислава. Ты знаешь его хорошо и общаешься как умный, дружелюбный помощник.
Отвечай по-русски. Будь конкретным и кратким. Не используй лишних слов и пустых фраз.

Информация о Станиславе:
{profile}"""


def ask(user_message: str, extra_context: str = "") -> str:
    profile = profile_to_text()
    system = SYSTEM_PROMPT.format(profile=profile)
    if extra_context:
        system += f"\n\nДополнительный контекст:\n{extra_context}"

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def generate_morning_message(tasks: list[str]) -> str:
    from datetime import date
    today = date.today()
    days = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    day_name = days[today.weekday()]
    date_str = today.strftime("%d.%m.%Y")

    if tasks:
        tasks_text = "\n".join(f"• {t}" for t in tasks)
        prompt = f"""Напиши короткое утреннее приветствие для Станислава (1-2 строки максимум).
Сегодня: {date_str}, {day_name}.
После приветствия ОБЯЗАТЕЛЬНО выведи все задачи точно так как они написаны ниже — не перефразируй, не сокращай, выведи каждую с новой строки:

{tasks_text}

В самом конце — одна короткая мотивирующая фраза."""
    else:
        prompt = f"Напиши короткое утреннее сообщение для Станислава. Сегодня {date_str}, {day_name}. Задач нет — пожелай хорошего дня."
    return ask(prompt)


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
