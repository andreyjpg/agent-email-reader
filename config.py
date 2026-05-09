import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    env: str = "development"
    telegram_token: str
    polling_interval: int
    outlook_client_id: str
    outlook_tenant_id: str  
    outlook_client_secret: str
    gemini_api_key: str
    gemini_model: str
    sentry_dsn: str
    encryption_key: str
    google_client_id: str
    google_client_secret: str
    database_url: str

    model_config = SettingsConfigDict(
        env_file=(".env", f".env.{os.getenv('ENV', 'development')}"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

config = Settings()
