import aiohttp
import base64
import json
from typing import List

from bluecon.model.Pairing import Pairing
from bluecon.model.User import User
from bluecon.oauth.OAuthService import OAuthService
from bluecon.oauth.OAuthToken import OAuthToken
from bluecon.storage.IOAuthTokenStorage import IOAuthTokenStorage
from bluecon.storage.InMemoryOAuthTokenStorage import InMemoryOAuthTokenStorage

class BlueConAPI(object):
    @classmethod
    async def create(cls, username: str, password: str, oAuthTokenStorage: IOAuthTokenStorage = InMemoryOAuthTokenStorage()):
        self = BlueConAPI("oe87y4nj6a2vz3h63lrh8y1p8lp4zewrhymhwa6ngz5oxf0", "8r1e8jo3dk32o5i0i1l89wcgapp05sp8ossrpjnxrodv0wr", oAuthTokenStorage)
        oauthToken = await OAuthService.createOAuthToken(self.__getAuthHeader(), username, password)
        self.__oAuthTokenStorage.storeOAuthToken(oauthToken)
        return self
    
    def __init__(self, clientId: str, clientSecret: str, oAuthTokenStorage: IOAuthTokenStorage):
        self.__clientId = clientId
        self.__clientSecret = clientSecret
        self.__oAuthTokenStorage = oAuthTokenStorage
    
    def __getAuthHeader(self) -> str:
        return base64.b64encode(bytes(f'{self.__clientId}:{self.__clientSecret}', 'utf-8')).decode('utf-8')
    
    async def __getOrRefreshOAuthToken(self) -> OAuthToken:
        oAuthToken = self.__oAuthTokenStorage.retrieveOAuthToken()
        if (oAuthToken.isExpired()):
            oAuthToken = await OAuthService.updateOAuthToken(self.__getAuthHeader(), oAuthToken)
            self.__oAuthTokenStorage.storeOAuthToken(oAuthToken)
        return oAuthToken
    
    async def getPairings(self) -> List[Pairing]:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://blue.fermax.com/pairing/api/v3/pairings/me', headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                return list(map(Pairing, json.loads(await response.text())))
    
    async def getUserInfo(self) -> User:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://blue.fermax.com/user/api/v1/users/me', headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                return User.fromJson(await response.text())