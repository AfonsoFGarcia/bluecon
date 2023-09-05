from bluecon.oauth.OAuthToken import OAuthToken
from bluecon.storage.IOAuthTokenStorage import IOAuthTokenStorage


@IOAuthTokenStorage.register
class InMemoryOAuthTokenStorage(IOAuthTokenStorage):
    def retrieveOAuthToken(self) -> OAuthToken | None:
        if self.__oAuthToken is None:
            return None
        else:
            return OAuthToken.fromJson(self.__oAuthToken)
    
    def storeOAuthToken(self, oAuthToken: OAuthToken):
        self.__oAuthToken = oAuthToken.toJson()