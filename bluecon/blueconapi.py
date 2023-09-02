import aiohttp
import base64
import json

from bluecon.oauthtoken import OAuthToken

class BlueConAPI(object):
    @classmethod
    async def create(cls, username, password):
        self = BlueConAPI()
        self.__clientId = "oe87y4nj6a2vz3h63lrh8y1p8lp4zewrhymhwa6ngz5oxf0"
        self.__clientSecret = "8r1e8jo3dk32o5i0i1l89wcgapp05sp8ossrpjnxrodv0wr"
        self.__authHeader = base64.b64encode(bytes(f'{self.__clientId}:{self.__clientSecret}', 'utf-8')).decode('utf-8')
        self.__oauthToken = await OAuthToken.create(self.__authHeader, username, password)
        return self
    
    async def getPairings(self):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://blue.fermax.com/pairing/api/v3/pairings/me', headers = (await self.__oauthToken.getBearerAuthHeader())) as response:
                return json.loads(await response.text())
    
    async def getUserInfo(self):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://blue.fermax.com/user/api/v1/users/me', headers = (await self.__oauthToken.getBearerAuthHeader())) as response:
                return json.loads(await response.text())