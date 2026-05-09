import aiohttp
import asyncio
import logging
from config import config

class TelegramBotService():
    def __init__(self):
        self.token = config.telegram_token
        self.base_url = f"https://api.telegram.org/bot{config.telegram_token}"

    def format_message(self, email: dict) -> str:
        return (
            f"*New important email*\n\n"
            f"*From:* {email['sender']}\n"
            f"*Subject:* {email['subject']}\n\n"
            f"*Preview:*\n{email['fragment']}"
        )

    async def send_telegram_msg(self, email, chat_id: str | None = None) -> bool:
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": self.format_message(email),
            "parse_mode": "Markdown"
        }
        timeout = aiohttp.ClientTimeout(total=10)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    data = await response.json()
                    if not data.get("ok"):
                        logging.error(f"Telegram error: {data.get('description')}")
                        return False
                    logging.info(f"Telegram message sent, status: {response.status}")
                    return True
        except aiohttp.ClientConnectionError:
            logging.error("No connection to Telegram")
            return False
        except asyncio.TimeoutError:
            logging.error("Timeout connecting to Telegram")
            return False
        except Exception as e:
            logging.error(f"Unexpected Error in Telegram {e}")