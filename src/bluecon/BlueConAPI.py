import asyncio
import aiohttp
import base64
import json
import hashlib
import logging
from typing import Callable, List
from threading import Event, Thread

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

from bluecon.ReceiverSupervisor import stop_receiver, supervise_receiver

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
        self._installationFid : str | None = None
        self._stopEvent : Event = Event()
        self._pushCredentials : dict | None = None
        self._initialPersistentIds : list[str] = []
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

    def _getInstallationId(self) -> str:
        """Build a Firebase-installation-ID-like identifier (22 url-safe base64 chars).

        The official app sends its real Firebase Installation ID in the `id` field of the
        v2 token registration. The push receiver library does not keep the one it generates,
        so a stable look-alike is derived from the FCM token instead."""

        if self._installationFid:
            return self._installationFid

        raw = bytearray(hashlib.sha256((self.deviceId or "").encode('utf-8')).digest()[:17])
        raw[0] = 0b01110000 + (raw[0] % 0b00010000)
        return base64.urlsafe_b64encode(bytes(raw)).decode('utf-8')[:22]

    async def registerAppToken(self, active: bool) -> bool:
        """Register (or deactivate) this FCM token with Fermax.

        Tries the v2 endpoint with the payload of the current official app first
        and falls back to the legacy v1 endpoint. The status and body of every
        attempt are logged, since a 200 from the legacy endpoint does not prove
        that pushes will actually be delivered."""

        headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()
        attempts = [
            ("v2", f'{FERMAX_BASE_URL}/notification/api/v2/apptoken', {
                "token": self.deviceId,
                "appVersion": "4.3.4",
                "appBuild": "749",
                "locale": "es-ES",
                "os": "ANDROID",
                "osVersion": "14",
                "phoneMobile": "HomeAssistant",
                "id": self._getInstallationId(),
                "active": active,
                "force": True
            }),
            ("v1", f'{FERMAX_BASE_URL}/notification/api/v1/apptoken', {
                "token": self.deviceId,
                "appVersion": "3.3.2",
                "locale": "en",
                "os": "Android",
                "osVersion": "Android 13",
                "active": active
            })
        ]

        async with aiohttp.ClientSession() as session:
            for version, url, payload in attempts:
                async with session.post(url, json = payload, headers = headers) as response:
                    body = (await response.text())[:300]
                    _LOGGER.info("App token registration (%s) -> HTTP %s: %s", version, response.status, body)
                    if 200 <= response.status < 300:
                        return True
        return False
    
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
            try:
                _LOGGER.info(
                    "Received FCM notification: type=%r keys=%s",
                    notification.get('FermaxNotificationType'),
                    sorted(notification.keys())
                )
                _LOGGER.debug(
                    "FCM notification payload: %s",
                    {k: ('<redacted>' if 'token' in k.lower() else v) for k, v in notification.items()}
                )
            except Exception:
                _LOGGER.exception("Could not describe the received FCM notification")
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
            def setReceiver(receiver):
                blueConAPIClient.receiver = receiver

            supervise_receiver(
                create_receiver = lambda persistentIds: PushReceiver(blueConAPIClient._pushCredentials, persistentIds),
                callback = on_notification,
                obj = blueConAPIClient,
                stop_event = blueConAPIClient._stopEvent,
                persistent_ids = blueConAPIClient._initialPersistentIds,
                on_receiver = setReceiver
            )

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

            def registerWithFid():
                """Register with FCM keeping the Firebase Installation ID that the push
                receiver library generates internally but does not return."""
                captured = {}
                originalGenerateFid = AndroidFCM.generate_firebase_fid

                def capturingGenerateFid():
                    captured['fid'] = originalGenerateFid()
                    return captured['fid']

                AndroidFCM.generate_firebase_fid = staticmethod(capturingGenerateFid)
                try:
                    registered = AndroidFCM.register(
                        api_key=blueConAPIClient.__apiKey,
                        project_id=blueConAPIClient.__projectId,
                        gcm_sender_id = blueConAPIClient.__senderId,
                        gms_app_id = blueConAPIClient.__appId,
                        android_package_name=blueConAPIClient.__packageName,
                        android_package_cert=PACKAGE_CERT
                    )
                finally:
                    AndroidFCM.generate_firebase_fid = staticmethod(originalGenerateFid)
                registered['fcm']['fid'] = captured.get('fid')
                return registered

            credentials = await blueConAPIClient.__notificationInfoStorage.retrieveCredentials()
            if credentials is None or not credentials.get('fcm', {}).get('fid'):
                if credentials is None:
                    _LOGGER.info("No cached FCM credentials found, registering with Google/Firebase")
                else:
                    _LOGGER.info("Cached FCM credentials have no Firebase installation id, registering again")
                try:
                    credentials = await asyncio.get_running_loop().run_in_executor(None, registerWithFid)
                except Exception:
                    _LOGGER.exception("FCM registration failed, notifications will not work")
                    return
                await blueConAPIClient.__notificationInfoStorage.storeCredentials(credentials)
            else:
                _LOGGER.info("Using cached FCM credentials")

            blueConAPIClient.deviceId = credentials["fcm"]["token"]
            blueConAPIClient._installationFid = credentials["fcm"].get("fid")
            registered = await blueConAPIClient.registerAppToken(True)
            if not registered:
                _LOGGER.error("Failed to register this device's FCM token with Fermax, notifications will not arrive")
            else:
                _LOGGER.info("Registered FCM token with Fermax successfully")

            received_persistent_ids = await blueConAPIClient.__notificationInfoStorage.retrievePersistentIds()

            blueConAPIClient._pushCredentials = credentials
            blueConAPIClient._initialPersistentIds = list(received_persistent_ids or [])
            blueConAPIClient._stopEvent = Event()

            if hass:
                hass.async_add_executor_job(receiver_listen, blueConAPIClient)
            else:
                receiver_listen(blueConAPIClient)
        await listener_thread(self)
    
    async def stopNotificationListener(self) -> bool:
        """Stop the push receiver and deactivate this device's token with Fermax.

        Setting the stop event and closing the socket makes the receiver loop, which runs in an
        executor job owned by the caller, finish cleanly instead of trying to reconnect."""

        self._stopEvent.set()
        if self.receiver is not None:
            stop_receiver(self.receiver)

        return not await self.registerAppToken(False)

    async def _getCallRegistry(self, session: aiohttp.ClientSession, deviceId: str) -> List[CallLog]:
        """Fetch the call registry of this app registration, restricted to the given device.

        Fermax scopes the registry by `appToken`, which is the FCM token this app registered
        (the same value the official app sends). The intercom's device id is only used as a
        fallback when the push listener has not provided a token yet."""

        appToken = self.deviceId or deviceId
        async with session.get(f'{FERMAX_BASE_URL}/callManager/api/v1/callregistry/participant',
                                params = {
                                    "appToken": appToken,
                                    "callRegistryType": "all"
                                },
                                headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
            if response.status != 200:
                _LOGGER.warning("Call registry request failed with HTTP %s: %s", response.status, (await response.text())[:200])
                return []
            responseJson = await response.json()

        callLogs: List[CallLog] = [callLog for callLog in map(CallLog, responseJson) if callLog.deviceId == deviceId]
        _LOGGER.debug("Call registry returned %s entries for device %s (%s with photo)", len(responseJson), deviceId, sum(1 for c in callLogs if c.photoId is not None))
        return callLogs

    async def getCallPhoto(self, photoId: str) -> bytes | None:
        """Download the photo Fermax stored for a call registry entry"""

        async with aiohttp.ClientSession() as session:
            async with session.get(f'{FERMAX_BASE_URL}/callManager/api/v1/photocall',
                                    params = {
                                        "photoId": photoId
                                    },
                                    headers = (await self.__getOrRefreshOAuthToken()).getBearerAuthHeader()) as response:
                if response.status != 200:
                    _LOGGER.warning("Photo request for %s failed with HTTP %s", photoId, response.status)
                    return None
                return base64.b64decode((await response.json())["image"]["data"])

    async def getLastPicture(self, deviceId: str) -> bytes | None:
        async with aiohttp.ClientSession() as session:
            allCallLogs = await self._getCallRegistry(session, deviceId)
        callLogs: List[CallLog] = [callLog for callLog in allCallLogs if callLog.photoId is not None]
        _LOGGER.info("Call registry for device %s: %s entries, %s with photo", deviceId, len(allCallLogs), len(callLogs))

        if len(callLogs) == 0:
            return None

        latestCallLog : CallLog = max(callLogs, key = lambda x: x.getCallDate())
        return await self.getCallPhoto(latestCallLog.photoId)

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
            callLogs = await self._getCallRegistry(session, deviceId)

        callLogs.sort(key = lambda x: x.getCallDate(), reverse = True)
        return callLogs[:limit]
