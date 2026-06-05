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
from ai import generate_morning_message, process_evening_reply, process_general_message, transcribe_voice, parse_task_action
from todoist import get_tasks_today, add_tasks, set_priority, complete_task, set_recurring, add_task, get_task_id_by_index

logging.basicConfig(level=logging.INFO)

router = Router()


class EveningDialog(StatesGroup):
    waiting_for_reply = State()


class MorningDialog(StatesGroup):
    waiting_for_priorities = State()


async def send_morning_message(bot_or_message, state: FSMContext, tasks: list[str]):
    text = await asyncio.to_thread(generate_morning_message, tasks)

    if isinstance(bot_or_message, Bot):
        await bot_or_message.send_message(ADMIN_CHAT_ID, text)
        if tasks:
            await bot_or_message.send_message(
                ADMIN_CHAT_ID,
                "Есть приоритетные задачи из этого списка?\nНазови номера через запятую (например: 1, 3) или напиши «нет»"
            )
    else:
        await bot_or_message.answer(text)
        if tasks:
            await bot_or_message.answer(
                "Есть приоритетные задачи из этого списка?\nНазови номера через запятую (например: 1, 3) или напиши «нет»"
            )

    if tasks:
        await state.set_state(MorningDialog.waiting_for_priorities)
        await state.update_data(tasks=tasks)


@router.message(MorningDialog.waiting_for_priorities)
async def handle_priorities(message: Message, state: FSMContext):
    data = await state.get_data()
    tasks = data.get("tasks", [])
    text = message.text.strip().lower()

    if text in ["нет", "no", "не", "-"]:
        await state.clear()
        await message.answer("Окей, удачного дня! 💪")
        return

    await state.clear()
    try:
        numbers = [int(n.strip()) - 1 for n in text.replace(",", " ").split() if n.strip().isdigit()]
        priority_tasks = [tasks[i] for i in numbers if 0 <= i < len(tasks)]

        if not priority_tasks:
            await message.answer("Не понял номера. Попробуй ещё раз или напиши «нет».")
            return

        marked = [t for t in priority_tasks if set_priority(t)]
        tasks_list = "\n".join(f"🔴 {t}" for t in marked)
        await message.answer(f"Отметил как приоритетные в Todoist:\n{tasks_list}\n\nУдачного дня! 💪")
    except Exception:
        await message.answer("Не смог разобрать — попробуй написать номера цифрами через запятую.")


async def process_user_message(message: Message, text: str, state: FSMContext):
    current_state = await state.get_state()

    if current_state == EveningDialog.waiting_for_reply:
        save_evening_reply(text)
        await state.clear()
        result = await asyncio.to_thread(process_evening_reply, text)
        tasks = result.get("tasks", [])
        response_text = result.get("response", "Записал! Хорошего вечера 🌙")
        if tasks:
            added = await asyncio.to_thread(add_tasks, tasks)
            tasks_list = "\n".join(f"• {t}" for t in tasks)
            response_text += f"\n\nДобавил в Todoist ({added} из {len(tasks)}):\n{tasks_list}"
        await message.answer(response_text)

    elif current_state == MorningDialog.waiting_for_priorities:
        await handle_priorities(message, state)

    else:
        # Сначала проверяем — вдруг это команда выполнения или повторения
        action_result = await asyncio.to_thread(parse_task_action, text)
        action = action_result.get("action", "none")

        if action == "complete":
            numbers = [n - 1 for n in action_result.get("numbers", [])]
            today_tasks = await asyncio.to_thread(get_tasks_today)
            done = []
            for idx in numbers:
                task_id = get_task_id_by_index(today_tasks, idx)
                if task_id and complete_task(task_id):
                    done.append(f"✅ {today_tasks[idx]['content']}")
            if done:
                await message.answer("Выполнено:\n" + "\n".join(done))
            else:
                await message.answer("Не нашёл такие задачи. Попробуй ещё раз.")

        elif action == "recurring":
            idx = action_result.get("number", 1) - 1
            due_string = action_result.get("due_string", "every day")
            today_tasks = await asyncio.to_thread(get_tasks_today)
            task_id = get_task_id_by_index(today_tasks, idx)
            if task_id and set_recurring(task_id, due_string):
                await message.answer(f"🔁 Сделал задачу повторяющейся: {today_tasks[idx]['content']}")
            else:
                await message.answer("Не смог найти задачу.")

        elif action == "add_recurring":
            task_text = action_result.get("text", "")
            due_string = action_result.get("due_string", "every day")
            if add_task(task_text, due_string):
                await message.answer(f"🔁 Добавил повторяющуюся задачу: {task_text}")
            else:
                await message.answer("Не смог добавить задачу.")

        else:
            result = await asyncio.to_thread(process_general_message, text)
            tasks = result.get("tasks", [])
            response_text = result.get("response", "Понял!")
            if tasks:
                added = await asyncio.to_thread(add_tasks, tasks)
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
async def cmd_morning(message: Message, state: FSMContext):
    await message.answer("Генерирую... ⏳")
    tasks = await asyncio.to_thread(get_tasks_today)
    await send_morning_message(message, state, tasks)


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
