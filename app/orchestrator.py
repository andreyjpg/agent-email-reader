import logging
from datetime import datetime, timezone

import asyncio
from sqlmodel import Session
from google.oauth2.credentials import Credentials

from app.repositories.client_repo import clientRepository
from app.repositories.token_repo import TokenRepository
from app.repositories.sync_state_repo import SyncStateRepository
from app.models.client import Client, EmailProvider
from app.models.sync_state import SyncState
from app.readers.gmail_reader import GmailReader
from app.readers.outlook_reader import OutlookReader
from app.services.classifier import Classifier
from app.services.telegram import TelegramBotService
from app.services.encryption import decrypt, encrypt
from config import config


class Orchestrator:
    def __init__(self, session: Session):
        self.session = session
        self.classifier = Classifier()
        self.bot = TelegramBotService()

    async def run(self):
        clients = clientRepository(self.session).get_all()
        logging.info(f"Processing {len(clients)} active client(s)")
        await asyncio.gather(
            *[self._process_client(client) for client in clients],
            return_exceptions=True
        )

    async def _process_client(self, client: Client):
        logging.info(f"Processing client: {client.email}")

        token_row = TokenRepository(self.session).get_by_client_id(client.id)
        if not token_row:
            logging.warning(f"No token found for client {client.email}, skipping")
            return
        if not client.telegram_chat:
            logging.warning(f"No telegram_chat set for client {client.email}, skipping")
            return

        access_token = decrypt(token_row.access_token)
        refresh_token = decrypt(token_row.refresh_token)
        original_access_token = access_token

        sync_repo = SyncStateRepository(self.session)
        sync_row = sync_repo.get_by_client(client.id)

        if client.email_provider == EmailProvider.GMAIL:
            sync_token = sync_row.history_id if sync_row else None
            expiry = token_row.token_expiry
            if expiry and expiry.tzinfo is not None:
                expiry = expiry.replace(tzinfo=None)
            creds = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                expiry=expiry,
                client_id=config.google_client_id,
                client_secret=config.google_client_secret,
                token_uri="https://oauth2.googleapis.com/token",
            )
            reader = GmailReader(creds)
        else:
            sync_token = sync_row.delta_token if sync_row else None
            reader = OutlookReader(
                access_token=access_token,
                refresh_token=refresh_token,
                token_expiry=token_row.token_expiry,
                client_id=config.outlook_client_id,
                client_secret=config.outlook_client_secret
            )

        messages, new_sync_token = await reader.get_new_messages(sync_token)

        for msg in messages:
            result = await self.classifier.llm_chat_creation(msg, client.keywords)
            if result == "IMPORTANT":
                await self.bot.send_telegram_msg(msg, chat_id=client.telegram_chat)

        if new_sync_token:
            sync_data = {"last_sync": datetime.now(timezone.utc)}
            if client.email_provider == EmailProvider.GMAIL:
                sync_data["history_id"] = new_sync_token
            else:
                sync_data["delta_token"] = new_sync_token

            if sync_row:
                sync_repo.update(sync_row, sync_data)
            else:
                sync_repo.create_sync(SyncState(client_id=client.id, **sync_data))

        self._update_token_if_refreshed(client, token_row, reader, original_access_token, refresh_token)

    def _update_token_if_refreshed(self, client: Client, token_row, reader, original_access_token: str, original_refresh_token: str):
        token_repo = TokenRepository(self.session)

        if client.email_provider == EmailProvider.GMAIL:
            new_token = reader.creds.token
            if new_token and new_token != original_access_token:
                expiry = reader.creds.expiry
                if expiry and expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                token_repo.update(token_row, {
                    "access_token": encrypt(new_token),
                    "token_expiry": expiry,
                    "updated_at": datetime.now(timezone.utc),
                })
                logging.info(f"Gmail token updated in DB for {client.email}")
        else:
            if reader.access_token != original_access_token:
                update_data = {
                    "access_token": encrypt(reader.access_token),
                    "token_expiry": reader.token_expiry,
                    "updated_at": datetime.now(timezone.utc),
                }
                if reader.refresh_token != original_refresh_token:
                    update_data["refresh_token"] = encrypt(reader.refresh_token)
                token_repo.update(token_row, update_data)
                logging.info(f"Outlook token updated in DB for {client.email}")
