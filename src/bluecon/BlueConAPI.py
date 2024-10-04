import asyncio
import aiohttp
import base64
import json
import hashlib
from typing import Callable, List
from threading import Thread

from bluecon.model.AccessDoor import AccessDoor
from bluecon.model.Pairing import Pairing
from bluecon.model.User import User
from bluecon.model.CallLog import CallLog
from bluecon.model.DeviceInfo import DeviceInfo
from bluecon.notifications.INotification import INotification
from bluecon.notifications.NotificationBuilder import NotificationBuilder
from bluecon.oauth.OAuthService import OAuthService
from bluecon.oauth.OAuthToken import OAuthToken
from bluecon.storage.IOAuthTokenStorage import IOAuthTokenStorage
from bluecon.storage.InMemoryOAuthTokenStorage import InMemoryOAuthTokenStorage
from bluecon.storage.INotificationInfoStorage import INotificationInfoStorage
from bluecon.storage.FileNotificationInfoStorage import FileNotificationInfoStorage

from push_receiver import PushReceiver
from push_receiver.android_fcm_register import AndroidFCM

FERMAX_BASE_URL = "https://blue.fermax.io"

class BlueConAPI:
    @classmethod
    async def create(
        cls, 
        username: str, 
        password: str,
        clientId: str,
        clientSecret: str,
        senderId: int,
        apiKey: str,
        projectId: str,
        appId: str,
        packageName: str,
        notificationCallback: Callable[[INotification], None],
        oAuthTokenStorage: IOAuthTokenStorage = InMemoryOAuthTokenStorage(),
        notificationInfoStorage: INotificationInfoStorage = FileNotificationInfoStorage()
    ):
        """Create instance of BlueConAPI for the provided username and password"""

        self = BlueConAPI(clientId, clientSecret, senderId, apiKey, projectId, appId, packageName, notificationCallback, oAuthTokenStorage, notificationInfoStorage)
        oauthToken = await OAuthService.createOAuthToken(self.__getAuthHeader(), username, password)
        await self.__oAuthTokenStorage.storeOAuthToken(oauthToken)
        return self
    
    @classmethod
    async def create_already_authed(
        cls,
        clientId: str,
        clientSecret: str,
        senderId: int,
        apiKey: str,
        projectId: str,
        appId: str,
        packageName: str,
        notificationCallback: Callable[[INotification], None],
        oAuthTokenStorage: IOAuthTokenStorage,
        notificationInfoStorage: INotificationInfoStorage = FileNotificationInfoStorage()
    ):
        """Create instance of BlueConAPI with the OAuth token stored in the provided storage"""
        if await oAuthTokenStorage.retrieveOAuthToken() is not None:
            return BlueConAPI(clientId, clientSecret, senderId, apiKey, projectId, appId, packageName, notificationCallback, oAuthTokenStorage, notificationInfoStorage)
        else:
            raise RuntimeError("Provided IOAuthTokenStorage does not contain a token")
    
    def __init__(
            self, 
            clientId: str,
            clientSecret: str,
            senderId: int,
            apiKey: str,
            projectId: str,
            appId: str,
            packageName: str,
            notificationCallback: Callable[[INotification], None], 
            oAuthTokenStorage: IOAuthTokenStorage,
            notificationInfoStorage: INotificationInfoStorage):
        self.__clientId = clientId
        self.__clientSecret = clientSecret
        self.__senderId = senderId
        self.__apiKey = apiKey
        self.__projectId = projectId
        self.__appId = appId
        self.__packageName = packageName
        self.__oAuthTokenStorage = oAuthTokenStorage
        self.__notificationInfoStorage = notificationInfoStorage
        self.receiver : PushReceiver = None
        self.deviceId : str = None
        self.notificationCallback = notificationCallback
    
    def __getAuthHeader(self) -> str:
        return base64.b64encode(bytes(f'{self.__clientId}:{self.__clientSecret}', 'utf-8')).decode('utf-8')
    
    async def __getOrRefreshOAuthToken(self) -> OAuthToken:
        oAuthToken = await self.__oAuthTokenStorage.retrieveOAuthToken()
        if (oAuthToken.isExpired()):
            oAuthToken = await OAuthService.updateOAuthToken(self.__getAuthHeader(), oAuthToken)
            await self.__oAuthTokenStorage.storeOAuthToken(oAuthToken)
        return oAuthToken
    
    async def getPairings(self) -> List[Pairing]:
        """Get list of pairings for the user"""

        async with aiohttp.ClientSession() as session:
            async with session.get(f'{FERMAX_BASE_URL}/pairing/api/v3/pairings/me', headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                return list(map(Pairing, json.loads(await response.text())))
    
    async def getUserInfo(self) -> User:
        """Get information about the user"""
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{FERMAX_BASE_URL}/user/api/v1/users/me', headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                return User(json.loads(await response.text()))
    
    async def openDoor(self, deviceId: str, door: AccessDoor) -> bool:
        """Open the provided door"""

        async with aiohttp.ClientSession() as session:
            async with session.post(f'{FERMAX_BASE_URL}/deviceaction/api/v1/device/{deviceId}/directed-opendoor',
                                    json = door.getDirectOpenDoorParamsRequest(),
                                    headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                return response.status == 200
    
    async def acknowledgeNotification(self, notification: INotification) -> bool:
        """Acknowledges the provided notification if it should be acknowledged"""

        if notification.shouldAcknowledge():
            async with aiohttp.ClientSession() as session:
                async with session.post(f'{FERMAX_BASE_URL}/callmanager/api/v1/message/ack',
                                        json = {
                                            "attended": True,
                                            "fcmMessageId": notification.getFcmMessageId()
                                        },
                                        headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                    return response.status == 200

    async def registerAppToken(self, active: bool) -> bool:
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{FERMAX_BASE_URL}/notification/api/v1/apptoken',
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

            def buildPackageCert():
                sha = hashlib.sha512()
                sha.update(str(blueConAPIClient.__senderId).encode('utf-8'))
                sha.update(blueConAPIClient.__appId.encode('utf-8'))
                sha.update(blueConAPIClient.__apiKey.encode('utf-8'))
                sha.update(blueConAPIClient.__projectId.encode('utf-8'))
                sha.update(blueConAPIClient.__packageName.encode('utf-8'))
                return sha.hexdigest()

            PACKAGE_CERT = buildPackageCert()

            credentials = asyncio.run(blueConAPIClient.__notificationInfoStorage.retrieveCredentials())
            if credentials is None:
                credentials = AndroidFCM.register(
                    api_key=blueConAPIClient.__apiKey,
                    project_id=blueConAPIClient.__projectId,
                    gcm_sender_id = blueConAPIClient.__senderId, 
                    gms_app_id = blueConAPIClient.__appId,
                    android_package_name=blueConAPIClient.__packageName,
                    android_package_cert=PACKAGE_CERT
                )
                asyncio.run(blueConAPIClient.__notificationInfoStorage.storeCredentials(credentials))
            
            blueConAPIClient.deviceId = credentials["fcm"]["token"]
            asyncio.run(blueConAPIClient.registerAppToken(True))
            
            received_persistent_ids = asyncio.run(blueConAPIClient.__notificationInfoStorage.retrievePersistentIds())

            if received_persistent_ids is None:
                blueConAPIClient.receiver = PushReceiver(credentials)
            else:
                blueConAPIClient.receiver = PushReceiver(credentials, received_persistent_ids)

            blueConAPIClient.receiver.listen(on_notification, blueConAPIClient)
        
        def on_notification(blueConAPIClient: BlueConAPI, notification: dict, data_message):
            idstr = data_message.persistent_id

            received_persistent_ids = asyncio.run(blueConAPIClient.__notificationInfoStorage.retrievePersistentIds())

            if received_persistent_ids is not None and any(idstr in x for x in received_persistent_ids):
                return
            
            asyncio.run(blueConAPIClient.__notificationInfoStorage.storePersistentId(idstr))
            
            blueConNotification = NotificationBuilder.fromNotification(notification, data_message.id)
            asyncio.run(blueConAPIClient.acknowledgeNotification(blueConNotification))
            blueConAPIClient.notificationCallback(blueConNotification)
        
        self.__listenerThread = Thread(target = listener_thread, args = (self, ))
        self.__listenerThread.daemon = True
        self.__listenerThread.start()
    
    async def stopNotificationListener(self) -> bool:
        self.__listenerThread.join(10.0)
        await self.registerAppToken(False)
        return self.__listenerThread.is_alive()
    
    async def getLastPicture(self, deviceId: str) -> bytes | None:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{FERMAX_BASE_URL}/callManager/api/v1/callregistry/participant',
                                    params = {
                                        "appToken": self.deviceId,
                                        "callRegistryType": "all"
                                    },
                                    headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                responseJson = await response.json()
            callLogs: List[CallLog] = [callLog for callLog in map(CallLog, responseJson) if callLog.deviceId == deviceId and callLog.photoId is not None]
            latestCallLog : CallLog | None = max(callLogs or None, key = lambda x: x.getCallDate())

            if latestCallLog is not None:
                async with session.get(f'{FERMAX_BASE_URL}/callManager/api/v1/photocall',
                                       params = {
                                           "photoId": latestCallLog.photoId
                                       },
                                       headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                    return base64.b64decode((await response.json())["image"]["data"])
            else:
                return None
    
    async def getDeviceInfo(self, deviceId: str) -> DeviceInfo | None:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{FERMAX_BASE_URL}/deviceaction/api/v1/device/{deviceId}',
                                   headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                if response.status == 200:
                    return DeviceInfo(await response.json())
                else:
                    return None
