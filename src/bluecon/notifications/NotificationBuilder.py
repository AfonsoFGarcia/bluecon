from bluecon.notifications.CallEndNotification import CallEndNotification
from bluecon.notifications.CallNotification import CallNotification
from bluecon.notifications.INotification import INotification


class NotificationBuilder:
    @classmethod
    def fromNotification(cls, notification: dict) -> INotification:
        if notification['data']['FermaxNotificationType'] == "Call":
            return CallNotification(notification['data'], notification['fcmMessageId'])
        elif notification['data']['FermaxNotificationType'] == "CallEnd":
            return CallEndNotification(notification['data'])
        else:
            raise NotImplementedError