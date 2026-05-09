from sqlmodel import Session, select
from app.models.sync_state import SyncState
from uuid import UUID

class SyncStateRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_sync(self, new_sync_state: SyncState) -> SyncState:
        self.session.add(new_sync_state)
        self.session.commit()
        self.session.refresh(new_sync_state)
        return new_sync_state

    def get_by_client(self, client_id: UUID) -> SyncState | None:
        statement = select(SyncState).where(SyncState.client_id == client_id)
        return self.session.exec(statement).first()

    def update(self, sync_state: SyncState, data: dict) -> SyncState:
        for key, value in data.items():
            setattr(sync_state, key, value)
        self.session.add(sync_state)
        self.session.commit()
        self.session.refresh(sync_state)
        return sync_state
