from bluecon.notifications.INotification import INotification

@INotification.register
class LoginInNewDevice(INotification):
    def __init__(self, notificationData: dict):
        self.sender_id = notificationData['google.c.sender.id']
        self.notificationTitle = notificationData['NotificationTitle']
        self.notificationBody = notificationData['NotificationBody']
        self.sendAcknowledge = bool(notificationData['SendAcknowledge'])

    def getNotificationType(self) -> str:
        return "Info"

    def shouldAcknowledge(self) -> str:
        return self.sendAcknowledge

    def getFcmMessageId(self) -> str:
        raise NotImplementedError
