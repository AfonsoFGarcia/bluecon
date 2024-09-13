# Quickstart

Create the connection to Fermax Blue servers:

```python
from bluecon import BlueConAPI, INotification

def notification_callback(notification: INotification):
    print(notification.getNotificationType())

username = "user@example.com"
password = "1234"

blueConAPIClient = await BlueConAPI.create(username, password, notification_callback)
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

Get device info:

```python
blueConAPIClient.getDeviceInfo(firstDoor.deviceId)
```
