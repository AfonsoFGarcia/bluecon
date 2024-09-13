# Quickstart

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
blueConAPIClient.getDeviceInfo(firstDoor.deviceId)
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

Listen to notifications:

```python
blueConAPIClient.startNotificationListener()
```

Stop listening to notifications:

```python
blueConAPIClient.stopNotificationListener()
```

Get last captured picture:

```python
blueConAPIClient.getLastPicture(firstDoor.deviceId)
```
