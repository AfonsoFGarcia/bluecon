import asyncio
import aiohttp
import base64
import json
from typing import Callable, List
from threading import Thread

from bluecon.model.AccessDoor import AccessDoor
from bluecon.model.Pairing import Pairing
from bluecon.model.User import User
from bluecon.notifications.INotification import INotification
from bluecon.notifications.NotificationBuilder import NotificationBuilder
from bluecon.oauth.OAuthService import OAuthService
from bluecon.oauth.OAuthToken import OAuthToken
from bluecon.storage.IOAuthTokenStorage import IOAuthTokenStorage
from bluecon.storage.InMemoryOAuthTokenStorage import InMemoryOAuthTokenStorage
from bluecon.push_receiver.push_receiver import PushReceiver
from bluecon.push_receiver.register import register

class BlueConAPI:
    @classmethod
    async def create(
        cls, 
        username: str, 
        password: str,
        notificationCallback: Callable[[INotification], None],
        oAuthTokenStorage: IOAuthTokenStorage = InMemoryOAuthTokenStorage()
    ):
        """Create instance of BlueConAPI for the provided username and password"""

        self = BlueConAPI(
            "oe87y4nj6a2vz3h63lrh8y1p8lp4zewrhymhwa6ngz5oxf0", 
            "8r1e8jo3dk32o5i0i1l89wcgapp05sp8ossrpjnxrodv0wr",
            notificationCallback,
            oAuthTokenStorage)
        oauthToken = await OAuthService.createOAuthToken(self.__getAuthHeader(), username, password)
        self.__oAuthTokenStorage.storeOAuthToken(oauthToken)
        return self
    
    def __init__(
            self, 
            clientId: str, 
            clientSecret: str, 
            notificationCallback: Callable[[INotification], None], 
            oAuthTokenStorage: IOAuthTokenStorage):
        self.__clientId = clientId
        self.__clientSecret = clientSecret
        self.__oAuthTokenStorage = oAuthTokenStorage
        self.receiver : PushReceiver = None
        self.deviceId : str = None
        self.notificationCallback = notificationCallback
    
    def __getAuthHeader(self) -> str:
        return base64.b64encode(bytes(f'{self.__clientId}:{self.__clientSecret}', 'utf-8')).decode('utf-8')
    
    async def __getOrRefreshOAuthToken(self) -> OAuthToken:
        oAuthToken = self.__oAuthTokenStorage.retrieveOAuthToken()
        if (oAuthToken.isExpired()):
            oAuthToken = await OAuthService.updateOAuthToken(self.__getAuthHeader(), oAuthToken)
            self.__oAuthTokenStorage.storeOAuthToken(oAuthToken)
        return oAuthToken
    
    async def getPairings(self) -> List[Pairing]:
        """Get list of pairings for the user"""

        async with aiohttp.ClientSession() as session:
            async with session.get('https://blue.fermax.com/pairing/api/v3/pairings/me', headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                return list(map(Pairing, json.loads(await response.text())))
    
    async def getUserInfo(self) -> User:
        """Get information about the user"""
        
        async with aiohttp.ClientSession() as session:
            async with session.get('https://blue.fermax.com/user/api/v1/users/me', headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                return User(json.loads(await response.text()))
    
    async def openDoor(self, deviceId: str, door: AccessDoor) -> bool:
        """Open the provided door"""

        async with aiohttp.ClientSession() as session:
            async with session.post(f'https://blue.fermax.com/deviceaction/api/v1/device/{deviceId}/directed-opendoor',
                                    json = door.getDirectOpenDoorParamsRequest(),
                                    headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                return response.status == 200
    
    async def acknowledgeNotification(self, notification: INotification) -> bool:
        """Acknowledges the provided notification if it should be acknowledged"""

        if notification.shouldAcknowledge():
            async with aiohttp.ClientSession() as session:
                async with session.post('https://blue.fermax.com/callmanager/api/v1/message/ack',
                                        json = {
                                            "attended": True,
                                            "fcmMessageId": notification.getFcmMessageId()
                                        },
                                        headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                    return response.status == 200

    async def registerAppToken(self, active: bool) -> bool:
        async with aiohttp.ClientSession() as session:
            async with session.post('https://blue.fermax.com/notification/api/v1/apptoken',
                                    json = {
                                        "token": self.deviceId,
                                        "appVersion": "3.3.2",
                                        "locale": "en",
                                        "os": "Android",
                                        "osVersion": "Android 13",
                                        "active": active
                                    },
                                    headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                return response.status == 200
    
    def startNotificationListener(self):
        """Starts the notification listener to get notifications about calls"""

        def listener_thread(blueConAPIClient: BlueConAPI):
            SENDER_ID = 879268374717
            APP_ID = "1:879268374717:android:b8e39b52f4a7452b926fd4"

            try:
                with open("credentials.json", "r") as f:
                    credentials = json.load(f)
            
            except FileNotFoundError:
                credentials = register(sender_id = SENDER_ID, app_id = APP_ID)
                with open("credentials.json", "w") as f:
                    json.dump(credentials, f)

            
            blueConAPIClient.deviceId = credentials["fcm"]["token"]
            asyncio.run(blueConAPIClient.registerAppToken(True))
            
            with open("persistent_ids.txt", "a+") as f:
                received_persistent_ids = [x.strip() for x in f]
            
            blueConAPIClient.receiver = PushReceiver(credentials, received_persistent_ids)
            blueConAPIClient.receiver.listen(on_notification, blueConAPIClient)
        
        def on_notification(blueConAPIClient: BlueConAPI, notification: dict, data_message):
            idstr = data_message.persistent_id + "\n"

            with open("persistent_ids.txt", "r") as f:
                if idstr in f:
                    return
            
            with open("persistent_ids.txt", "a") as f:
                f.write(idstr)
            
            blueConNotification = NotificationBuilder.fromNotification(notification)
            asyncio.run(blueConAPIClient.acknowledgeNotification(blueConNotification))
            blueConAPIClient.notificationCallback(blueConNotification)
        
        self.__listenerThread = Thread(target = listener_thread, args = (self, ))
        self.__listenerThread.daemon = True
        self.__listenerThread.start()
    
    async def stopNotificationListener(self) -> bool:
        self.receiver.stop()
        self.__listenerThread.join(10.0)
        await self.registerAppToken(False)
        return self.__listenerThread.is_alive()