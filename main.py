import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from readers.gmail_reader import GmailReader
from readers.outlook_reader import OutlookReader
from orchestrator import Orchestrator
from services.classifier import Classifier
from services.telegram import TelegramBotService
from config import Config
from storage import Storage
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        RotatingFileHandler(
            "logs/agent.log",
            maxBytes=5_000_000,  # 5MB max per file
            backupCount=3,        # keeps last 3 files
            encoding="utf-8"
        ),
        # Also prints to console
        logging.StreamHandler()
    ]
)

async def main():
    storage = Storage()

    # Select reader based on config
    if Config.EMAIL_PROVIDER == "gmail":
        reader = GmailReader(storage=storage)
    elif Config.EMAIL_PROVIDER == "outlook":
        reader = OutlookReader(storage=storage)
    else:
        logging.error(f"Unknown email provider: {Config.EMAIL_PROVIDER}")
        return
    
    classifier = Classifier(model=Config.OLLAMA_MODEL)
    bot = TelegramBotService(token=Config.TELEGRAM_TOKEN, chat_id=Config.TELEGRAM_CHAT_ID)

    orchestrator = Orchestrator(reader, classifier, bot)

    #scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(orchestrator.run, 'interval', minutes=Config.POLLING_INTERVAL, max_instances=1, misfire_grace_time=30)
    scheduler.start()
    logging.info("Agent started, wating for emails...")

    await asyncio.Event().wait()

asyncio.run(main())