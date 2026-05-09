from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from uuid import uuid4, UUID
from typing import Optional

class SyncState(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    history_id: Optional[str] = Field(default=None)
    delta_token: Optional[str] = Field(default=None)
    last_sync:Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))  # bien
    client_id: UUID = Field(foreign_key="client.id")

