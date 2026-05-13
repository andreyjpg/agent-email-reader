import logging
import asyncio
from app.readers.base_reader import BaseReader

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError, TransportError


class GmailReader(BaseReader):
    def __init__(self, creds: Credentials):
        self.creds = creds
        self.service = build("gmail", "v1", credentials=self.creds, cache_discovery=False)
        logging.info("GmailReader initialized")

    def _refresh_if_needed(self):
        if self.creds.expired and self.creds.refresh_token:
            self.creds.refresh(Request())
            logging.info("Gmail token refreshed")

    async def get_new_messages(self, sync_token: str | None = None) -> tuple[list, str | None]:
        try:
            loop = asyncio.get_running_loop()

            await loop.run_in_executor(None, self._refresh_if_needed)

            if not sync_token:
                profile = await loop.run_in_executor(
                    None, lambda: self.service.users().getProfile(userId="me").execute()
                )
                current_id = profile["historyId"]
                logging.info("No history_id in DB, saved current position from Gmail")
                return [], current_id

            result_history = await loop.run_in_executor(
                None, lambda: self.service.users().history().list(
                    userId="me",
                    startHistoryId=sync_token
                ).execute()
            )

            new_history_id = result_history.get("historyId", sync_token)

            message_ids = []
            if "history" in result_history:
                for record in result_history["history"]:
                    if "messagesAdded" in record:
                        for msg in record["messagesAdded"]:
                            message_ids.append(msg["message"]["id"])

            if not message_ids:
                logging.info("No new emails found in Gmail")
                return [], new_history_id

            emails_details = []
            for message_id in message_ids:
                detail = await loop.run_in_executor(
                    None, lambda mid=message_id: self.service.users().messages().get(
                        userId="me", id=mid
                    ).execute()
                )
                headers = detail.get("payload", {}).get("headers", [])
                subject = next((h["value"] for h in headers if h["name"] == "Subject"), None)
                sender = next((h["value"] for h in headers if h["name"] == "From"), None)
                emails_details.append({
                    "id": detail.get("id"),
                    "sender": sender,
                    "subject": subject,
                    "fragment": detail.get("snippet"),
                })

            logging.info(f"{len(emails_details)} new emails found in Gmail")
            return emails_details, new_history_id

        except HttpError as e:
            if e.status_code == 404:
                logging.warning("Gmail history_id expired or invalid, resetting sync position on next run")
                return [], None
            logging.error(f"Gmail API error {e.status_code}: {e}")
            return [], sync_token
        except RefreshError as e:
            logging.error(f"Gmail token expired, re-authentication required: {e}")
            return [], sync_token
        except TransportError:
            logging.error("No internet connection to Gmail API")
            return [], sync_token
        except Exception as e:
            logging.error(f"Unexpected error in GmailReader: {e}")
            return [], sync_token
