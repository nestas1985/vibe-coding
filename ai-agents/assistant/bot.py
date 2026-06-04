import asyncio
import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import TELEGRAM_TOKEN, ADMIN_CHAT_ID
from database import init_db, save_evening_reply
from profile import profile_to_text
from ai import generate_morning_message, process_evening_reply
from todoist import get_tasks_today, add_tasks

logging.basicConfig(level=logging.INFO)

router = Router()


class EveningDialog(StatesGroup):
    waiting_for_reply = State()


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет, Стас! Я твой личный ассистент. 👋\n\n"
        "Каждое утро в 8:00 буду присылать план дня.\n"
        "Каждый вечер в 21:00 спрошу как прошёл день.\n\n"
        "/profile — посмотреть мой профиль о тебе\n"
        "/morning — получить утреннее сообщение прямо сейчас\n"
        "/help — список команд"
    )


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    await message.answer(f"Вот что я знаю о тебе:\n\n{profile_to_text()}")


@router.message(Command("morning"))
async def cmd_morning(message: Message):
    await message.answer("Генерирую... ⏳")
    tasks = get_tasks_today()
    text = generate_morning_message(tasks)
    await message.answer(text)


@router.message(Command("myid"))
async def cmd_myid(message: Message):
    await message.answer(f"Твой Telegram ID: `{message.chat.id}`", parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Команды:\n"
        "/start — начать\n"
        "/morning — план на сегодня прямо сейчас\n"
        "/profile — мой профиль о тебе\n"
        "/help — помощь"
    )


@router.message(EveningDialog.waiting_for_reply)
async def handle_evening_reply(message: Message, state: FSMContext):
    save_evening_reply(message.text)
    await state.clear()

    result = process_evening_reply(message.text)
    tasks = result.get("tasks", [])
    response_text = result.get("response", "Записал! Хорошего вечера 🌙")

    if tasks:
        added = add_tasks(tasks)
        tasks_list = "\n".join(f"• {t}" for t in tasks)
        response_text += f"\n\nДобавил в Todoist ({added} из {len(tasks)}):\n{tasks_list}"

    await message.answer(response_text)


async def main():
    init_db()
    bot = Bot(token=TELEGRAM_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)

    from scheduler import setup_scheduler
    scheduler = setup_scheduler(bot, router, storage)
    scheduler.start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
