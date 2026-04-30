import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", 5))
    EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER")
    OUTLOOK_CLIENT_ID = os.getenv("OUTLOOK_CLIENT_ID")
    OUTLOOK_TENANT_ID = os.getenv("OUTLOOK_TENANT_ID")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")