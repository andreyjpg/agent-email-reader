from readers.base_reader import BaseReader
from services.classifier import Classifier
from services.telegram import TelegramBotService

class Orchestrator:
    def __init__(self, reader: BaseReader, classifier: Classifier, bot: TelegramBotService):
        self.reader = reader
        self.classifier = classifier
        self.bot = bot

    async def run(self): 
        messages = await self.reader.get_new_messages()
        for msg in messages:
            classified_msg = await self.classifier.llm_chat_creation(msg)
            if classified_msg == "IMPORTANT":
                await self.bot.send_telegram_msg(msg)
