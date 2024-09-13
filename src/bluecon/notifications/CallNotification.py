from bluecon.notifications.INotification import INotification


@INotification.register
class CallNotification(INotification):
    def __init__(self, notificationData: dict, fcmMessageId: str):
        self.deviceId = notificationData['DeviceId']
        self.fermaxToken = notificationData['FermaxToken']
        self.socketUrl = notificationData['SocketUrl']
        self.notificationTitle = notificationData['NotificationTitle']
        self.notificationBody = notificationData['NotificationBody']
        self.callAs = notificationData['CallAs']
        self.roomId = notificationData['RoomId']
        self.sendAcknowledge = bool(notificationData['SendAcknowledge'])
        self.accessDoorKey = notificationData['AccessDoorKey']
        self.fcmMessageId = fcmMessageId
    
    def getNotificationType(self) -> str:
        return "Call"
    
    def shouldAcknowledge(self) -> str:
        return self.sendAcknowledge
    
    def getFcmMessageId(self) -> str:
        return self.fcmMessageId