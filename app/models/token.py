from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional

class Token(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    client_id: UUID = Field(foreign_key="client.id")
    access_token: str
    refresh_token: str
    token_expiry: datetime
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))  # bien