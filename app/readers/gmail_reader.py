import logging
from app.readers.base_reader import BaseReader

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError, TransportError

SCOPES = ["openid email https://www.googleapis.com/auth/gmail.readonly"]

class GmailReader(BaseReader):
    def __init__(self, creds: Credentials):
        self.creds = creds
        if self.creds.expired and self.creds.refresh_token:
            self.creds.refresh(Request())
            logging.info("Gmail token refreshed during init")
        self.service = build("gmail", "v1", credentials=self.creds)
        logging.info("Gmail authenticated successfully")

    async def get_new_messages(self, sync_token: str | None = None) -> tuple[list, str | None]:
        try:
            if self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
                logging.info("Gmail token refreshed")

            if not sync_token:
                profile = self.service.users().getProfile(userId='me').execute()
                sync_token = profile['historyId']
                logging.info("No history_id in DB, fetched from Gmail profile")

            result_history = self.service.users().history().list(
                userId="me",
                startHistoryId=sync_token
            ).execute()

            new_history_id = result_history.get("historyId", sync_token)

            message_ids = []
            if 'history' in result_history:
                for register in result_history['history']:
                    if 'messagesAdded' in register:
                        for message in register['messagesAdded']:
                            message_ids.append(message["message"]["id"])

            if not message_ids:
                logging.info("No new emails found")
                return [], new_history_id

            emails_details = []
            for message_id in message_ids:
                detail = self.service.users().messages().get(
                    userId="me",
                    id=message_id
                ).execute()

                headers = detail.get("payload", {}).get("headers", [])
                subject = next((h["value"] for h in headers if h["name"] == "Subject"), None)
                sender = next((h["value"] for h in headers if h["name"] == "From"), None)

                emails_details.append({
                    "id": detail.get("id"),
                    "sender": sender,
                    "subject": subject,
                    "fragment": detail.get("snippet"),
                })

            logging.info(f"New emails found: {len(emails_details)}")
            return emails_details, new_history_id

        except HttpError as e:
            logging.error(f"Gmail API error {e.status_code}: {e}")
            return [], sync_token
        except RefreshError:
            logging.error("Gmail token expired, re-authentication required")
            return [], sync_token
        except TransportError:
            logging.error("No internet connection, retrying in next cycle")
            return [], sync_token
        except Exception as e:
            logging.error(f"Unexpected error in GmailReader: {e}")
            return [], sync_token
