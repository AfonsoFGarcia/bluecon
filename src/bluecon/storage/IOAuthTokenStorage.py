import abc

from bluecon.oauth.OAuthToken import OAuthToken

class IOAuthTokenStorage(metaclass = abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, __subclass: type) -> bool:
        return hasattr(__subclass, 'retrieveOAuthToken') and callable(__subclass.retrieveOAuthToken) and hasattr(__subclass, 'storeOAuthToken') and callable(__subclass.storeOAuthToken)

    @abc.abstractmethod
    async def retrieveOAuthToken(self) -> OAuthToken | None:
        """Retrieves the OAuthToken from storage"""

        raise NotImplementedError
    
    @abc.abstractmethod
    async def storeOAuthToken(self, oAuthToken: OAuthToken):
        """Stores the OAuthToken"""
        
        raise NotImplementedError