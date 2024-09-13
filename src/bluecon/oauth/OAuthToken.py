from json import dumps, loads, JSONEncoder
import datetime
from dateutil.parser import isoparse

class OAuthToken:
    def __init__(self, oauth_response: dict):
        self.accessToken = oauth_response['access_token']
        self.refreshToken = oauth_response['refresh_token']
        if (oauth_response.get('expires_in') is not None):
            self.expiresIn = oauth_response['expires_in']
        if (oauth_response.get('expires_on') is not None):
            self.expiresOn = isoparse(oauth_response['expires_on'])
        else:
            self.expiresOn = datetime.datetime.now() + datetime.timedelta(seconds = self.expiresIn)
    
    def getBearerAuthHeader(self) -> dict:
        """Get a dictionary containing the Authorization HTTP header for this token"""

        return {
            'Authorization': f'Bearer {self.accessToken}'
        }
    
    def isExpired(self) -> bool:
        """Check if the token has already expired (for safety, it is considered expired 1 hour before actual expiration)"""

        return datetime.datetime.now() >= (self.expiresOn - datetime.timedelta(hours = 1))
    
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
            "expires_on": o.expiresOn.isoformat()
        }
