# Quickstart

All the examples below use `await`, so they must run inside an `async` function.

Create the connection to Fermax Blue servers (without notification setup):

```python
from bluecon import BlueConAPI, INotification

def notification_callback(notification: INotification):
    print(notification.getNotificationType())

username = "user@example.com"
password = "1234"
clientId = "clientId"
clientSecret = "clientSecret"

blueConAPIClient = await BlueConAPI.create(
    username,
    password,
    clientId,
    clientSecret,
    None,
    None,
    None,
    None,
    None,
    notification_callback
)
```

Get user details:

```python
userInfo = await blueConAPIClient.getUserInfo()
```

Get pairings for user:

```python
pairings = await blueConAPIClient.getPairings()
```

Open door:

```python
firstDoor = pairings[0]
openDoorResult = await blueConAPIClient.openDoor(firstDoor.deviceId, firstDoor.accessDoorMap['ZERO'])
```

Get device info:

```python
deviceInfo = await blueConAPIClient.getDeviceInfo(firstDoor.deviceId)
```

## Receiving ringing notifications

Create the connection to Fermax Blue servers and FCM:

```python
from bluecon import BlueConAPI, INotification

def notification_callback(notification: INotification):
    print(notification.getNotificationType())

username = "user@example.com"
password = "1234"
clientId = "clientId"
clientSecret = "clientSecret"
senderId = 0
apiKey = "apiKey"
projectId = "projectId"
appId = "appId"
packageName = "packageName"

blueConAPIClient = await BlueConAPI.create(
    username,
    password,
    clientId,
    clientSecret,
    senderId,
    apiKey,
    projectId,
    appId,
    packageName,
    notification_callback
)
```

Listen to notifications. `startNotificationListener` is a coroutine: it registers the FCM token with Fermax and starts the push receiver.

```python
await blueConAPIClient.startNotificationListener()
```

The callback receives a `CallNotification` when someone rings (with `deviceId` and `accessDoorKey`), and a `CallEndNotification` when the call finishes or is missed.

When using the library from Home Assistant, pass the `hass` object so the receiver runs in an executor job and the callbacks are scheduled on its event loop:

```python
await blueConAPIClient.startNotificationListener(hass)
```

Stop listening to notifications. This deactivates the token with Fermax:

```python
await blueConAPIClient.stopNotificationListener()
```

## Call registry and photos

The call registry is scoped by the FCM token of the app, so these calls only return data after the notification listener has started.

Get the most recent calls of a device, newest first. Each entry has `callDate` and, when Fermax took a photo, a `photoId`:

```python
callLogs = await blueConAPIClient.getCallHistory(firstDoor.deviceId, limit=10)
```

Download the photo of a call:

```python
image = await blueConAPIClient.getCallPhoto(callLogs[0].photoId)
```

Get the last captured picture:

```python
image = await blueConAPIClient.getLastPicture(firstDoor.deviceId)
```

Fermax can take a few seconds to add the photo of a call to its registry, so right after a `CallEndNotification` the new photo may not be there yet. Retry a few times a few seconds apart.
