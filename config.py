import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
GOOGLE_CREDS_FILE = os.getenv("GOOGLE_CREDS_FILE")
CONCURRENCY = int(os.getenv("CONCURRENCY", 5))
STEAM_CURRENCY = os.getenv("STEAM_CURRENCY", "5")
STEAM_COUNTRY = os.getenv("STEAM_COUNTRY", "RU")
UPDATE_PERIOD_MIN = int(os.getenv("UPDATE_PERIOD_MIN", 5))
RETRY_COUNT = int(os.getenv("RETRY_COUNT", 3))
RETRY_DELAY = float(os.getenv("RETRY_DELAY", 1.2))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 5))
BATCH_SLEEP = int(os.getenv("BATCH_SLEEP", 60))
