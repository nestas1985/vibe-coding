from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from config import ADMIN_CHAT_ID, MORNING_HOUR, MORNING_MINUTE, EVENING_HOUR, EVENING_MINUTE
from database import mark_morning_sent
from ai import generate_morning_message
from todoist import get_tasks_today
from datetime import date


async def send_morning(bot: Bot):
    tasks = get_tasks_today()
    text = generate_morning_message(tasks)
    await bot.send_message(ADMIN_CHAT_ID, text)
    mark_morning_sent()


async def send_evening(bot: Bot, storage: MemoryStorage):
    from bot import EveningDialog

    await bot.send_message(
        ADMIN_CHAT_ID,
        "Привет! Уже вечер 🌙\n\nРасскажи, как прошёл день? Что успел, что нет?\nМожет есть срочные задачи на завтра?"
    )

    key = StorageKey(bot_id=bot.id, chat_id=ADMIN_CHAT_ID, user_id=ADMIN_CHAT_ID)
    context = FSMContext(storage=storage, key=key)
    await context.set_state(EveningDialog.waiting_for_reply)


def setup_scheduler(bot: Bot, router, storage: MemoryStorage) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    scheduler.add_job(send_morning, "cron", hour=MORNING_HOUR, minute=MORNING_MINUTE, args=[bot])
    scheduler.add_job(send_evening, "cron", hour=EVENING_HOUR, minute=EVENING_MINUTE, args=[bot, storage])

    return scheduler
