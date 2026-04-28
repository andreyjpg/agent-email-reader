import json
import logging
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data.json"

class Storage:
    def __init__(self):
        self._ensure_file()

    def _ensure_file(self):
        # Create the file if it doesn't exist with base structure
        if not DATA_FILE.exists():
            self._write({})
            logging.info("data.json created")

    def _read(self) -> dict:
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError:
            logging.error("data.json corrupted, resetting file")
            self._write({})
            return {}

    def _write(self, data: dict):
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error writing data.json: {e}")

    def get_gmail_history_id(self) -> str | None:
        data = self._read()
        return data.get("gmail", {}).get("history_id")

    def save_gmail_history_id(self, history_id: str):
        data = self._read()
        data["gmail"] = {"history_id": history_id}
        self._write(data)
        logging.info(f"Gmail history_id updated: {history_id}")

    def get_outlook_delta_token(self) -> str | None:
        data = self._read()
        return data.get("outlook", {}).get("delta_token")

    def save_outlook_delta_token(self, delta_token: str):
        data = self._read()
        data["outlook"] = {"delta_token": delta_token}
        self._write(data)
        logging.info(f"Outlook delta_token updated")