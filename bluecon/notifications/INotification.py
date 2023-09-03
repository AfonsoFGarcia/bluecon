import abc

class INotification(metaclass = abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, __subclass: type) -> bool:
        return hasattr(__subclass, 'getNotificationType') and callable(__subclass.getNotificationType)

    @abc.abstractmethod
    def getNotificationType(self) -> str:
        """Retrieves the notification type for this notification"""

        raise NotImplementedError

    @abc.abstractmethod
    def shouldAcknowledge(self) -> str:
        """Should this notification be acknowledged"""

        raise NotImplementedError
    
    @abc.abstractmethod
    def getFcmMessageId(self) -> str:
        """Retrieves the FCM message ID for this notification"""

        raise NotImplementedError
