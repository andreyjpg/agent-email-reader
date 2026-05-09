import json
import logging
import aiohttp
from pathlib import Path
from readers.base_reader import BaseReader
import msal
import asyncio

from storage import Storage
from config import Config

SCOPES = ["https://graph.microsoft.com/Mail.Read"]
GRAPH_API = "https://graph.microsoft.com/v1.0"

class OutlookReader(BaseReader):
    def __init__(self, storage: Storage):
        self.client_id = Config.OUTLOOK_CLIENT_ID
        self.tenant_id = Config.OUTLOOK_TENANT_ID
        self.storage = storage
        self.token = None
        self._authenticate()

    def _load_cache(self):
        cache = msal.SerializableTokenCache()
        token_path = Path("tokens/outlook_token.json")
        
        if token_path.exists():
            cache.deserialize(token_path.read_text())
        
        return cache

    def _save_cache(self, cache):
        token_path = Path("tokens/outlook_token.json")
        token_path.parent.mkdir(exist_ok=True)
        
        if cache.has_state_changed:
            token_path.write_text(cache.serialize())
            logging.info("Outlook token cache saved")

    def _authenticate(self):
        try:
            cache = self._load_cache()

            app = msal.PublicClientApplication(
                client_id=self.client_id,
                authority="https://login.microsoftonline.com/common",
                token_cache=cache
            )

            # Try cached token first
            accounts = app.get_accounts()
            result = None

            if accounts:
                result = app.acquire_token_silent(SCOPES, account=accounts[0])
                if result:
                    logging.info("Outlook authenticated from cache")

            # If no cached token use device flow
            if not result:
                flow = app.initiate_device_flow(scopes=SCOPES)

                if "user_code" not in flow:
                    raise Exception(f"Failed to create device flow: {flow.get('error')}")

                # This prints the code in VPS logs
                print(flow["message"], flush=True)
                logging.info("Waiting for device flow authentication...")

                result = app.acquire_token_by_device_flow(flow)

            if "access_token" in result:
                self.token = result["access_token"]
                self._save_cache(cache)
                logging.info("Outlook authenticated successfully")
            else:
                logging.error(f"Authentication error: {result.get('error_description')}")
                raise Exception("Authentication failed")

        except Exception as e:
            logging.error(f"Error in Outlook authentication: {e}")
            raise

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def get_history_id(self) -> str:
        # In Outlook it's called deltaToken instead of historyId
        ruta_json = Path(__file__).parent.parent / "data.json"

        try:
            with open(ruta_json, 'r') as file:
                data = json.load(file)

            outlook_data = data.get("outlook", {})
            return outlook_data.get("delta_token")

        except FileNotFoundError:
            logging.warning("data.json not found, initial delta will be used")
            return None
        except json.JSONDecodeError:
            logging.error("data.json corrupted")
            return None

    def _save_delta_token(self, delta_token: str):
        ruta_json = Path(__file__).parent.parent / "data.json"

        try:
            # Read existing file to not overwrite Gmail data
            try:
                with open(ruta_json, 'r') as file:
                    data = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError):
                data = {}

            data["outlook"] = {"delta_token": delta_token}

            with open(ruta_json, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=4, ensure_ascii=False)

        except Exception as e:
            logging.error(f"Error saving delta token: {e}")

    async def get_new_messages(self) -> list:
        try:
            delta_token = self.get_history_id()
            emails_details = []
            all_messages = []

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30, connect=10)) as session:
                # If no delta_token, get only recent unread messages
                if not delta_token:
                    url = f"{GRAPH_API}/me/mailFolders/inbox/messages/delta"
                    params = {
                        "$select": "id,subject,from,isRead,receivedDateTime,bodyPreview"
                    }
                else:
                    # Use delta_token to get only new changes
                    url = delta_token
                    params = {}

                while url:
                    async with session.get(
                        url, headers=self._get_headers(), params=params
                    ) as response:

                        if response.status == 401:
                            logging.error("Token expired, re-authenticating")
                            self._authenticate()
                            return []

                        if response.status != 200:
                            text = await response.text()
                            logging.error(f"Graph API error {response.status}: {text}")
                            return []

                        data = await response.json()
                        all_messages.extend(data.get("value", []))

                        if "@odata.deltaLink" in data:
                            # save whole url not only the token
                            self._save_delta_token(data["@odata.deltaLink"])
                            logging.info("Delta link saved ")
                            url = None

                        elif "@odata.nextLink" in data:
                            url = data["@odata.nextLink"]
                            params = {}  
                            logging.info("Fetching next page...")

                        else:
                            logging.warning("No deltaLink or nextLink found")
                            url = None

            for message in all_messages:
                if not message.get("isRead", True):
                    emails_details.append({
                        "id": message.get("id"),
                        "sender": message.get("from", {}).get("emailAddress", {}).get("address"),
                        "subject": message.get("subject"),
                        "fragment": message.get("bodyPreview"),
                    })

            if emails_details:
                logging.info(f"{len(emails_details)} new emails found in Outlook")
            else:
                logging.info("No new emails in Outlook")

            return emails_details

        except aiohttp.ClientConnectionError:
            logging.error("No connection to Microsoft Graph API")
            return []
        except asyncio.TimeoutError:
            logging.error("Timeout connecting to Microsoft Graph API")
            return []
        except Exception as e:
            logging.error(f"Unexpected error in OutlookReader: {e}")
            return []