import aiohttp
import json
import datetime

class OAuthToken:
    def __init__(self, oauth_response):
        self.__accessToken = oauth_response['access_token']
        self.__refreshToken = oauth_response['refresh_token']
        self.__expiresIn = oauth_response['expires_in']
        self.__tokenType = oauth_response['token_type']
        self.__scope = oauth_response['scope']
        self.__jti = oauth_response['jti']
        self.__expiresOn = datetime.datetime.now() + datetime.timedelta(seconds = self.__expiresIn)
    
    async def getBearerAuthHeader(self):
        if self.__isExpired() == True:
            await self.__updateOAuthToken()
        
        return {
            'Authorization': f'Bearer {self.__accessToken}'
        }
    
    def __isExpired(self):
        return datetime.datetime.now() >= (self.__expiresOn - datetime.timedelta(hours = 1))
    
    async def __updateOAuthToken(self):
        async with aiohttp.ClientSession() as session:
            async with session.post('https://oauth.blue.fermax.com/oauth/token',
                                    data = aiohttp.FormData(fields = {
                                        "refresh_token": self.__refreshToken,
                                        "grant_type": "refresh_token"
                                    }),
                                    headers = {
                                        "Authorization": f'Basic {self.__authHeader}'
                                    }) as response:
                oauth_response = json.loads((await response.text()))
                self.__accessToken = oauth_response['access_token']
                self.__refreshToken = oauth_response['refresh_token']
                self.__expiresIn = oauth_response['expires_in']
                self.__tokenType = oauth_response['token_type']
                self.__scope = oauth_response['scope']
                self.__jti = oauth_response['jti']
                self.__expiresOn = datetime.datetime.now() + datetime.timedelta(seconds = self.__expiresIn)

    @classmethod
    async def create(cls, authHeader, username, password):
        async with aiohttp.ClientSession() as session:
            async with session.post('https://oauth.blue.fermax.com/oauth/token',
                                data = aiohttp.FormData(fields = {
                                    "username": username,
                                    "password": password,
                                    "grant_type": "password"
                                }),
                                headers = {
                                    "Authorization": f'Basic {authHeader}'
                                }) as response:
                self = OAuthToken(json.loads((await response.text())))
                self.__authHeader = authHeader
                return self