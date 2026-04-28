from abc import ABC, abstractmethod

class BaseReader(ABC):

    @abstractmethod
    async def get_new_messages(self) -> list:
        pass

    @abstractmethod
    def get_history_id(self) -> str:
        pass

