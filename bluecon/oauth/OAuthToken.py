from json import dumps, loads, JSONEncoder
import datetime

class OAuthToken:
    def __init__(self, oauth_response):
        self.accessToken = oauth_response['access_token']
        self.refreshToken = oauth_response['refresh_token']
        self.expiresIn = oauth_response['expires_in']
        self.__expiresOn = datetime.datetime.now() + datetime.timedelta(seconds = self.expiresIn)
    
    def getBearerAuthHeader(self) -> dict:
        """Get a dictionary containing the Authorization HTTP header for this token"""

        return {
            'Authorization': f'Bearer {self.accessToken}'
        }
    
    def isExpired(self) -> bool:
        """Check if the token has already expired (for safety, it is considered expired 1 hour before actual expiration)"""

        return datetime.datetime.now() >= (self.__expiresOn - datetime.timedelta(hours = 1))
    
    def getRefreshToken(self) -> str:
        """Get the refresh token for this OAuthToken"""
        
        return self.refreshToken

    def toJson(self) -> str:
        return dumps(self, cls = OAuthTokenJSONEncoder)
    
    @classmethod
    def fromJson(csl, json: str):
        return OAuthToken(loads(json))
    
class OAuthTokenJSONEncoder(JSONEncoder):
    def default(self, o: OAuthToken):
        return {
            "access_token": o.accessToken,
            "refresh_token": o.refreshToken,
            "expires_in": o.expiresIn
        }