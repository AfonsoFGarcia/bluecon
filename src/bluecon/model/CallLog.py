from datetime import datetime as DateTime
from dateutil.parser import isoparse

class CallLog:
    def __init__(self, callLogResponse: dict):
        self.deviceId: str = callLogResponse['deviceId']
        self.callDate: str = callLogResponse['callDate']
        self.photoId: str | None = callLogResponse['photoId']
    
    def getCallDate(self) -> DateTime:
        return isoparse(self.callDate)
