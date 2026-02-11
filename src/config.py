from __future__ import annotations
import os
from typing import List

from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class MySQLSettings:
    host: str
    port: int
    user: str
    password: str
    database: str

def load_settings() -> MySQLSettings:
    return MySQLSettings(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "test_db"),
    )

# Load config from .env
API_ID          = int(os.getenv('TELEGRAM_API_ID'))
API_HASH        = os.getenv('TELEGRAM_API_HASH')
BOT_TOKEN       = os.getenv('TELEGRAM_BOT_TOKEN')
PHONE           = os.getenv('TELEGRAM_PHONE_NUMBER')
SELF_USER_ID    = int(os.getenv('TELEGRAM_SELF_ID'))

OWNERS: List[int] = [int(x.strip()) for x in os.getenv('TELEGRAM_OWNER_IDS').split(',') if x.strip()]

# ------- Session paths -------
SESSIONS_DIR = 'sessions'
os.makedirs(SESSIONS_DIR, exist_ok=True)
USER_SESSION = os.path.join(SESSIONS_DIR, 'userbot.session')
BOT_SESSION  = os.path.join(SESSIONS_DIR, 'bot_helper.session')