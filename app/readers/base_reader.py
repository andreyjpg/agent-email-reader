from abc import ABC, abstractmethod

class BaseReader(ABC):

    @abstractmethod
    async def get_new_messages(self, sync_token: str | None = None) -> tuple[list, str | None]:
        pass
