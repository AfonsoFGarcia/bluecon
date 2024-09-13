from bluecon.notifications.INotification import INotification


@INotification.register
class CallEndNotification(INotification):
    def __init__(self, notificationData: dict):
        self.deviceId = notificationData['DeviceId']
        self.notificationTitle = notificationData['NotificationTitle']
        self.notificationBody = notificationData['NotificationBody']
        self.callAs = notificationData['CallAs']
    
    def getNotificationType(self) -> str:
        return "CallEnd"
    
    def shouldAcknowledge(self) -> str:
        return False
    
    def getFcmMessageId(self) -> str:
        raise NotImplementedError
