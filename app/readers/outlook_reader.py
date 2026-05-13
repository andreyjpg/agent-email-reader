import logging
import aiohttp
import asyncio
from datetime import datetime, timezone, timedelta
from app.readers.base_reader import BaseReader

TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
GRAPH_API = "https://graph.microsoft.com/v1.0"
SCOPE = "https://graph.microsoft.com/Mail.Read offline_access"


class OutlookReader(BaseReader):
    def __init__(self, access_token: str, refresh_token: str, token_expiry: datetime, client_id: str, client_secret: str):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expiry = token_expiry
        self.client_id = client_id
        self.client_secret = client_secret
        logging.info("OutlookReader initialized")

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    async def _refresh_access_token(self, session: aiohttp.ClientSession) -> bool:
        try:
            data = {
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "scope": SCOPE,
            }
            async with session.post(TOKEN_URL, data=data) as response:
                result = await response.json()
                if "access_token" in result:
                    self.access_token = result["access_token"]
                    if "refresh_token" in result:
                        self.refresh_token = result["refresh_token"]
                    expires_in = result.get("expires_in", 3600)
                    self.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                    logging.info("Outlook token refreshed successfully")
                    return True
                logging.error(f"Outlook token refresh failed: {result.get('error_description')}")
                return False
        except Exception as e:
            logging.error(f"Error refreshing Outlook token: {e}")
            return False

    async def _fetch_page(self, session: aiohttp.ClientSession, url: str, params: dict, already_refreshed: bool = False) -> dict | None:
        async with session.get(url, headers=self._get_headers(), params=params) as response:
            if response.status == 401 and not already_refreshed:
                logging.warning("Outlook token expired, refreshing...")
                if await self._refresh_access_token(session):
                    return await self._fetch_page(session, url, params, already_refreshed=True)
                return None
            if response.status != 200:
                text = await response.text()
                logging.error(f"Graph API error {response.status}: {text}")
                return None
            return await response.json()

    async def _get_initial_delta_token(self, session: aiohttp.ClientSession) -> str | None:
        url = f"{GRAPH_API}/me/mailFolders/inbox/messages/delta"
        params = {"$select": "id,subject,from,isRead,bodyPreview", "$top": "999"}

        while url:
            data = await self._fetch_page(session, url, params)
            if data is None:
                return None
            if "@odata.deltaLink" in data:
                logging.info("Outlook initial delta position set, skipping historical emails")
                return data["@odata.deltaLink"]
            url = data.get("@odata.nextLink")
            params = {}

        return None

    async def get_new_messages(self, sync_token: str | None = None) -> tuple[list, str | None]:
        try:
            all_messages = []
            new_delta_token = sync_token

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30, connect=10)) as session:
                if not sync_token:
                    new_delta_token = await self._get_initial_delta_token(session)
                    return [], new_delta_token

                url = sync_token
                params = {}

                while url:
                    data = await self._fetch_page(session, url, params)
                    if data is None:
                        return [], sync_token

                    all_messages.extend(data.get("value", []))

                    if "@odata.deltaLink" in data:
                        new_delta_token = data["@odata.deltaLink"]
                        logging.info("Delta link saved")
                        url = None
                    elif "@odata.nextLink" in data:
                        url = data["@odata.nextLink"]
                        params = {}
                        logging.info("Fetching next page...")
                    else:
                        logging.warning("No deltaLink or nextLink found")
                        url = None

            emails_details = [
                {
                    "id": msg.get("id"),
                    "sender": msg.get("from", {}).get("emailAddress", {}).get("address"),
                    "subject": msg.get("subject"),
                    "fragment": msg.get("bodyPreview"),
                }
                for msg in all_messages
                if not msg.get("isRead", True)
            ]

            if emails_details:
                logging.info(f"{len(emails_details)} new emails found in Outlook")
            else:
                logging.info("No new emails in Outlook")

            return emails_details, new_delta_token

        except aiohttp.ClientConnectionError:
            logging.error("No connection to Microsoft Graph API")
            return [], sync_token
        except asyncio.TimeoutError:
            logging.error("Timeout connecting to Microsoft Graph API")
            return [], sync_token
        except Exception as e:
            logging.error(f"Unexpected error in OutlookReader: {e}")
            return [], sync_token
