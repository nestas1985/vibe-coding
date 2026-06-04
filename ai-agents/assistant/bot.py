import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import TELEGRAM_TOKEN, ADMIN_CHAT_ID
from database import init_db, save_evening_reply
from profile import profile_to_text
from ai import generate_morning_message, process_evening_reply, process_general_message, transcribe_voice
from todoist import get_tasks_today, add_tasks

logging.basicConfig(level=logging.INFO)

router = Router()


class EveningDialog(StatesGroup):
    waiting_for_reply = State()


async def process_user_message(message: Message, text: str, state: FSMContext):
    current_state = await state.get_state()

    if current_state == EveningDialog.waiting_for_reply:
        save_evening_reply(text)
        await state.clear()
        result = process_evening_reply(text)
        tasks = result.get("tasks", [])
        response_text = result.get("response", "Записал! Хорошего вечера 🌙")
        if tasks:
            added = add_tasks(tasks)
            tasks_list = "\n".join(f"• {t}" for t in tasks)
            response_text += f"\n\nДобавил в Todoist ({added} из {len(tasks)}):\n{tasks_list}"
        await message.answer(response_text)
    else:
        result = process_general_message(text)
        tasks = result.get("tasks", [])
        response_text = result.get("response", "Понял!")
        if tasks:
            added = add_tasks(tasks)
            tasks_list = "\n".join(f"• {t}" for t in tasks)
            response_text += f"\n\nДобавил в Todoist ({added} из {len(tasks)}):\n{tasks_list}"
        await message.answer(response_text)


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет, Стас! Я твой личный ассистент. 👋\n\n"
        "Каждое утро в 8:00 буду присылать план дня.\n"
        "Каждый вечер в 21:00 спрошу как прошёл день.\n\n"
        "Можешь писать или отправлять голосовые — пойму оба формата.\n\n"
        "/morning — план на сегодня\n"
        "/profile — мой профиль о тебе\n"
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
        "/morning — план на сегодня\n"
        "/profile — мой профиль о тебе\n"
        "/help — помощь\n\n"
        "Или просто пиши / говори голосовым — отвечу."
    )


@router.message(F.voice)
async def handle_voice(message: Message, state: FSMContext, bot: Bot):
    await message.answer("Слушаю... 🎙")
    import tempfile
    file = await bot.get_file(message.voice.file_id)
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        audio_path = tmp.name
    try:
        await bot.download_file(file.file_path, audio_path)
        text = transcribe_voice(audio_path)
        await message.answer(f"Расслышал: _{text}_", parse_mode="Markdown")
        await process_user_message(message, text, state)
    except Exception as e:
        await message.answer(f"Не смог расшифровать голосовое: {e}")
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message, state: FSMContext):
    await process_user_message(message, message.text, state)


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
