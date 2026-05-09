from uuid import UUID
from app.models.client import Client
from sqlmodel import select, Session

class clientRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self):
        statement = select(Client).where(Client.active)
        return self.session.exec(statement).all()

    def get_by_email(self, email: str) -> Client | None:
        return self.session.exec(
            select(Client).where(Client.email == email)
        ).first()

    def get_by_id(self, client_id: UUID) -> Client | None:
        return self.session.exec(
            select(Client).where(Client.id == client_id)
        ).first()

