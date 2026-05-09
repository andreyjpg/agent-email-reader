from sqlmodel import Session, select
from app.models.token import Token
from uuid import UUID

class TokenRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_client_id(self, client_id: UUID) -> Token | None:
        return self.session.exec(
            select(Token).where(Token.client_id == client_id)
        ).first()


    def update(self, token: Token, data: dict) -> Token:
        for key, value in data.items():
            setattr(token, key, value)
        self.session.add(token)
        self.session.commit()
        self.session.refresh(token)
        return token