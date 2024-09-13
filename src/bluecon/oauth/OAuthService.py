from bluecon.oauth.OAuthToken import OAuthToken
from aiohttp import ClientSession, FormData

FERMAX_OAUTH_BASE_URL = "https://oauth-blue.fermax.io"

class OAuthService:
    @classmethod
    async def createOAuthToken(cls, authHeader: str, username: str, password: str) -> OAuthToken:
        """Call Fermax Blue OAuth endpoint and generate an OAuthToken from the result"""

        async with ClientSession() as session:
            async with session.post(f'{FERMAX_OAUTH_BASE_URL}/oauth/token',
                                data = FormData(fields = {
                                    "username": username,
                                    "password": password,
                                    "grant_type": "password"
                                }),
                                headers = {
                                    "Authorization": f'Basic {authHeader}'
                                }) as response:
                if response.status == 200:
                    return OAuthToken.fromJson(await response.text())
                else:
                    raise RuntimeError(f"Could not login: {(await response.text())}")
    
    @classmethod
    async def updateOAuthToken(cls, authHeader: str, oAuthToken: OAuthToken) -> OAuthToken:
        """Refresh the OAuthToken by calling the Fermax Blue OAuth endpoint and generating a new OAuthToken from the result"""
        
        async with ClientSession() as session:
            async with session.post(f'{FERMAX_OAUTH_BASE_URL}/oauth/token',
                                    data = FormData(fields = {
                                        "refresh_token": oAuthToken.getRefreshToken(),
                                        "grant_type": "refresh_token"
                                    }),
                                    headers = {
                                        "Authorization": f'Basic {authHeader}'
                                    }) as response:
                return OAuthToken.fromJson(await response.text())