import os

from dotenv import load_dotenv

load_dotenv()

LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.5-flash")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CHAT_HISTORY_DIR = os.getenv("CHAT_HISTORY_DIR", "chat-history")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///database.db")

SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
ALGORITHM = os.getenv("ALGORITHM", "HS256")
