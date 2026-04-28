import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
    POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", 5))
    EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER")
    OUTLOOK_CLIENT_ID = os.getenv("OUTLOOK_CLIENT_ID")
    OUTLOOK_TENANT_ID = os.getenv("OUTLOOK_TENANT_ID")