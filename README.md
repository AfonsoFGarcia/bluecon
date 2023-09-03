# BlueCon

Library for connecting to Fermax Blue supported doorbells.

**This library is still work in progress, do not use it for actual projects**

Tested Devices:

* Fermax Veo XS WiFi (9449)

## Installation

```sh
pip install bluecon
```

## Get started

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

## Acknowledgements

I'd like to thank all contributors of [push_receiver](https://github.com/louisliv/push_receiver) and its many forks for provinding a library that can receive push notifications from Firebase. This is the essencial part of how Fermax Blue works in terms of receiving the doorbell rings and without it this project would be close to pointless. This library is included with some minor changes in this repo.
