import os

from dotenv import load_dotenv

load_dotenv()

GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
GOOGLE_CREDS_FILE = os.getenv("GOOGLE_CREDS_FILE")
CONCURRENCY = int(os.getenv("CONCURRENCY", "5"))
STEAM_CURRENCY = os.getenv("STEAM_CURRENCY", "5")
STEAM_COUNTRY = os.getenv("STEAM_COUNTRY", "RU")
UPDATE_PERIOD_MIN = int(os.getenv("UPDATE_PERIOD_MIN", "5"))
RETRY_COUNT = int(os.getenv("RETRY_COUNT", "3"))
RETRY_DELAY = float(os.getenv("RETRY_DELAY", "1.2"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))
BATCH_SLEEP = int(os.getenv("BATCH_SLEEP", "5"))

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://caseparser:caseparser123@localhost:5432/caseparser")

# Authentication
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change_me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# CORS / API
_origins_raw = os.getenv("API_ALLOWED_ORIGINS", "*")
API_ALLOWED_ORIGINS = [origin.strip() for origin in _origins_raw.split(",") if origin.strip()] or ["*"]
