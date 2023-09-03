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
from bluecon import BlueConAPI

username = "user@example.com"
password = "1234"

blueConAPIClient = await BlueConAPI.create(username, password)
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