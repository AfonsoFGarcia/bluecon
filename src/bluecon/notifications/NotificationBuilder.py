from bluecon.notifications.CallEndNotification import CallEndNotification
from bluecon.notifications.CallNotification import CallNotification
from bluecon.notifications.INotification import INotification
from bluecon.notifications.LoginInNewDevice import LoginInNewDevice


class NotificationBuilder:
    @classmethod
    def fromNotification(cls, notification: dict, notificationId: str) -> INotification:
        if notification['FermaxNotificationType'] == "Call":
            return CallNotification(notification, notificationId)
        elif notification['FermaxNotificationType'] == "CallEnd":
            return CallEndNotification(notification)
        elif notification['FermaxNotificationType'] == "Info":
            return LoginInNewDevice(notification)
        else:
            raise NotImplementedError