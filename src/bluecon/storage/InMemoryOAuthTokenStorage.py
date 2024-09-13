from bluecon.oauth.OAuthToken import OAuthToken
from bluecon.storage.IOAuthTokenStorage import IOAuthTokenStorage


@IOAuthTokenStorage.register
class InMemoryOAuthTokenStorage(IOAuthTokenStorage):
    async def retrieveOAuthToken(self) -> OAuthToken | None:
        if self.__oAuthToken is None:
            return None
        else:
            return OAuthToken.fromJson(self.__oAuthToken)
    
    async def storeOAuthToken(self, oAuthToken: OAuthToken):
        self.__oAuthToken = oAuthToken.toJson()