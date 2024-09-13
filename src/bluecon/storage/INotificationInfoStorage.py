import abc
from typing import Any

class INotificationInfoStorage(metaclass = abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, __subclass: type) -> bool:
        return (
            hasattr(__subclass, 'retrieveCredentials') and callable(__subclass.retrieveCredentials) 
            and hasattr(__subclass, 'storeCredentials') and callable(__subclass.storeCredentials)
            and hasattr(__subclass, 'retrievePersistentIds') and callable(__subclass.retrievePersistentIds) 
            and hasattr(__subclass, 'storePersistentId') and callable(__subclass.storePersistentId)
        )

    @abc.abstractmethod
    async def retrieveCredentials(self) -> dict[str, dict[str, Any]] | None:
        """Retrieves the credentials from storage"""

        raise NotImplementedError
    
    @abc.abstractmethod
    async def storeCredentials(self, credentials: dict[str, dict[str, Any]]):
        """Stores the credentials"""
        
        raise NotImplementedError
    
    @abc.abstractmethod
    async def retrievePersistentIds(self) -> list[str] | None:
        """Retrieves the persistent IDs from storage"""

        raise NotImplementedError
    
    @abc.abstractmethod
    async def storePersistentId(self, persistentId: str):
        """Stores the persistent ID"""
        
        raise NotImplementedError