from typing import Any
from bluecon.storage.INotificationInfoStorage import INotificationInfoStorage
import json

class FileNotificationInfoStorage(INotificationInfoStorage):

    async def retrieveCredentials(self) -> dict[str, dict[str, Any]] | None:
        try:
            with open("credentials.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
    
    async def storeCredentials(self, credentials: dict[str, dict[str, Any]]):
        with open("credentials.json", "w") as f:
            json.dump(credentials, f)
    
    async def retrievePersistentIds(self) -> list[str] | None:
        try:
            with open("persistent_ids.txt", "r") as f:
                return [x.strip() for x in f]
        except FileNotFoundError:
            return None
    
    async def storePersistentId(self, persistentId: str):
        with open("persistent_ids.txt", "a") as f:
            f.write(persistentId + "\n")