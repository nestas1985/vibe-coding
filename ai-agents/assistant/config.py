from dotenv import load_dotenv
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
TODOIST_API_KEY = os.getenv("TODOIST_API_KEY")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID") or "0")

MORNING_HOUR = 8
MORNING_MINUTE = 0
EVENING_HOUR = 21
EVENING_MINUTE = 0
WEEKLY_DAY = "sun"
WEEKLY_HOUR = 20
