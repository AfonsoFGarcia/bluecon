# BlueCon

Library for connecting to Fermax Blue supported doorbells

**This library is still work in progress, do not use it for actual projects**

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
userInfo = blueConAPIClient.getUserInfo()
```

Get pairings for user:

```python
userInfo = blueConAPIClient.getPairings()
```