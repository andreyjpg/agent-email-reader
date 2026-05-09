from sqlmodel import SQLModel, Field, Column
from typing import Optional
from uuid import uuid4, UUID
from enum import Enum
from datetime import timezone, datetime
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import String


class EmailProvider(str, Enum):
    GMAIL = "gmail"
    OUTLOOK = "outlook"


class Client(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: Optional[str] = Field(default=None)
    email: str = Field(unique=True, max_length=254, index=True)
    email_provider: EmailProvider
    telegram_chat: Optional[str] = Field(default=None)
    active: bool = Field(default=True)
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    keywords: list[str] = Field(default=[], sa_column=Column(ARRAY(String)))
