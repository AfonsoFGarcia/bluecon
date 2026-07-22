import asyncio
import aiohttp
import base64
import json
import hashlib
import logging
from typing import Callable, List
from threading import Thread

_LOGGER = logging.getLogger(__name__)

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
    
    async def startNotificationListener(self, hass = None): #hass is an optional parameter for Home Assistant
        """Starts the notification listener to get notifications about calls"""

        def run_in_event_loop(coroutine):
            if hass:
                return asyncio.run_coroutine_threadsafe(coroutine, hass.loop).result()

            loop = asyncio.get_running_loop()
            if loop.is_running():
                return asyncio.ensure_future(coroutine)

            return asyncio.run_coroutine_threadsafe(coroutine, loop).result()

        def on_notification(blueConAPIClient: BlueConAPI, notification: dict, data_message):
            _LOGGER.debug("Received FCM notification: %s", notification)
            idstr = data_message.persistent_id
            received_persistent_ids = []


            received_persistent_ids = run_in_event_loop(blueConAPIClient.__notificationInfoStorage.retrievePersistentIds())

            if received_persistent_ids is not None and any(idstr in x for x in received_persistent_ids):
                _LOGGER.debug("Ignoring already-seen notification %s", idstr)
                return

            # TODO I commented this because it fails for me in Home Assistant
            #run_in_event_loop(blueConAPIClient.__notificationInfoStorage.storePersistentId(idstr))

            try:
                blueConNotification = NotificationBuilder.fromNotification(notification, data_message.id)
                run_in_event_loop(blueConAPIClient.acknowledgeNotification(blueConNotification))
                blueConAPIClient.notificationCallback(blueConNotification)
            except Exception:
                _LOGGER.exception("Failed to process FCM notification: %s", notification)

        def receiver_listen(blueConAPIClient: BlueConAPI):
            try:
                _LOGGER.info("FCM push receiver starting to listen")
                blueConAPIClient.receiver.listen(on_notification, blueConAPIClient)
            except Exception:
                _LOGGER.exception("FCM push receiver stopped unexpectedly")

        async def listener_thread(blueConAPIClient: BlueConAPI):
            def buildPackageCert():
                sha = hashlib.sha512()
                sha.update(str(blueConAPIClient.__senderId).encode('utf-8'))
                sha.update(blueConAPIClient.__appId.encode('utf-8'))
                sha.update(blueConAPIClient.__apiKey.encode('utf-8'))
                sha.update(blueConAPIClient.__projectId.encode('utf-8'))
                sha.update(blueConAPIClient.__packageName.encode('utf-8'))
                return sha.hexdigest()

            PACKAGE_CERT = buildPackageCert()

            credentials = await blueConAPIClient.__notificationInfoStorage.retrieveCredentials()
            if credentials is None:
                _LOGGER.info("No cached FCM credentials found, registering with Google/Firebase")
                try:
                    credentials = AndroidFCM.register(
                        api_key=blueConAPIClient.__apiKey,
                        project_id=blueConAPIClient.__projectId,
                        gcm_sender_id = blueConAPIClient.__senderId,
                        gms_app_id = blueConAPIClient.__appId,
                        android_package_name=blueConAPIClient.__packageName,
                        android_package_cert=PACKAGE_CERT
                    )
                except Exception:
                    _LOGGER.exception("FCM registration failed, notifications will not work")
                    return
                await blueConAPIClient.__notificationInfoStorage.storeCredentials(credentials)
            else:
                _LOGGER.info("Using cached FCM credentials")

            blueConAPIClient.deviceId = credentials["fcm"]["token"]
            registered = await blueConAPIClient.registerAppToken(True)
            if not registered:
                _LOGGER.error("Failed to register this device's FCM token with Fermax, notifications will not arrive")
            else:
                _LOGGER.info("Registered FCM token with Fermax successfully")

            received_persistent_ids = await blueConAPIClient.__notificationInfoStorage.retrievePersistentIds()

            if received_persistent_ids is None:
                blueConAPIClient.receiver = PushReceiver(credentials)
            else:
                blueConAPIClient.receiver = PushReceiver(credentials, received_persistent_ids)

            if hass:
                hass.async_add_executor_job(receiver_listen, blueConAPIClient)
            else:
                receiver_listen(blueConAPIClient)
        await listener_thread(self)
    
    async def stopNotificationListener(self) -> bool:
        self.__listenerThread.join(10.0)
        await self.registerAppToken(False)
        return self.__listenerThread.is_alive()
    
    async def getLastPicture(self, deviceId: str) -> bytes | None:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{FERMAX_BASE_URL}/callManager/api/v1/callregistry/participant',
                                    params = {
                                        "appToken": deviceId,
                                        "callRegistryType": "all"
                                    },
                                    headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                responseJson = await response.json()
            callLogs: List[CallLog] = [callLog for callLog in map(CallLog, responseJson) if callLog.deviceId == deviceId and callLog.photoId is not None]

            if (callLogs is None or len(callLogs) == 0):
                return None

            latestCallLog : CallLog | None = max(callLogs, key = lambda x: x.getCallDate())

            async with session.get(f'{FERMAX_BASE_URL}/callManager/api/v1/photocall',
                                    params = {
                                        "photoId": latestCallLog.photoId
                                    },
                                    headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                return base64.b64decode((await response.json())["image"]["data"])
    
    async def getDeviceInfo(self, deviceId: str) -> DeviceInfo | None:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{FERMAX_BASE_URL}/deviceaction/api/v1/device/{deviceId}',
                                   headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                if response.status == 200:
                    return DeviceInfo(await response.json())
                else:
                    return None

    async def getCallHistory(self, deviceId: str, limit: int = 20) -> List[CallLog]:
        """Get the most recent call history entries for the provided device, newest first"""

        async with aiohttp.ClientSession() as session:
            async with session.get(f'{FERMAX_BASE_URL}/callManager/api/v1/callregistry/participant',
                                    params = {
                                        "appToken": deviceId,
                                        "callRegistryType": "all"
                                    },
                                    headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                responseJson = await response.json()

        callLogs: List[CallLog] = [callLog for callLog in map(CallLog, responseJson) if callLog.deviceId == deviceId]
        callLogs.sort(key = lambda x: x.getCallDate(), reverse = True)
        return callLogs[:limit]

    async def getFirmwareUpdateStatus(self, deviceId: str) -> dict | None:
        """Get the firmware update status for the provided device.

        The response shape returned by Fermax's API for this endpoint has not been
        fully verified yet; this returns the raw JSON payload as-is so callers can
        inspect it and the mapping can be refined once confirmed against a real device.
        """

        async with aiohttp.ClientSession() as session:
            async with session.get(f'{FERMAX_BASE_URL}/update/api/v1/firmware-update-process',
                                    params = {
                                        "deviceId": deviceId
                                    },
                                    headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None
