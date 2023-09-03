from bluecon.oauth.OAuthToken import OAuthToken
from bluecon.storage.IOAuthTokenStorage import IOAuthTokenStorage


@IOAuthTokenStorage.register
class InMemoryOAuthTokenStorage(IOAuthTokenStorage):
    def retrieveOAuthToken(self) -> OAuthToken:
        return OAuthToken.fromJson(self.__oAuthToken)
    
    def storeOAuthToken(self, oAuthToken: OAuthToken):
        self.__oAuthToken = oAuthToken.toJson()