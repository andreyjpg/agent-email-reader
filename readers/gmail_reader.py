import os.path
import logging
from readers.base_reader import BaseReader
from storage import Storage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError, TransportError

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

class GmailReader(BaseReader):
    def __init__(self, storage: Storage):
        self.creds = None
        self.service = None
        self.storage = storage
        self._authenticate()

    def _authenticate(self):
        try:
            if os.path.exists("token.json"):
                self.creds = Credentials.from_authorized_user_file("token.json", SCOPES)

            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        "credentials.json", SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)

                with open("token.json", "w") as token:
                    token.write(self.creds.to_json())

            self.service = build("gmail", "v1", credentials=self.creds)
            logging.info("Gmail authenticated successfully")

        except RefreshError:
            logging.error("Invalid credentials, delete token.json and re-authenticate")
            raise
        except FileNotFoundError:
            logging.error("credentials.json not found")
            raise

    def get_history_id(self) -> str:
        # Ask storage first
        history_id = self.storage.get_gmail_history_id()

        # If storage has no history_id, fetch it from Gmail profile
        if not history_id:
            logging.info("No history_id found in storage, fetching from Gmail profile")
            profile = self.service.users().getProfile(userId='me').execute()
            history_id = profile['historyId']
            self.storage.save_gmail_history_id(history_id)

        return history_id

    async def get_new_messages(self) -> list:
      try:
        history_id = self.get_history_id()

        result_history = self.service.users().history().list(
            userId="me",
            startHistoryId=history_id
        ).execute()

        self.storage.save_gmail_history_id(result_history["historyId"])

        message_ids = []
        if 'history' in result_history:
            for register in result_history['history']:
                if 'messagesAdded' in register:
                    for message in register['messagesAdded']:
                        message_ids.append(message["message"]["id"])

        if not message_ids:
            logging.info("No new emails found")
            return []

        emails_details = []
        for message_id in message_ids:
            detail = self.service.users().messages().get(
                userId="me",
                id=message_id
            ).execute()

            # Extract headers from email
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
        return emails_details

      except HttpError as e:
          logging.error(f"Gmail API error {e.status_code}: {e}")
          return []
      except RefreshError:
          logging.error("Token expired, re-authentication required")
          return []
      except TransportError:
          logging.error("No internet connection, retrying in next cycle")
          return []
      except Exception as e:
          logging.error(f"Unexpected error in GmailReader: {e}")
          return []