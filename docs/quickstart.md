# Quickstart

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
userInfo = await blueConAPIClient.getPairings()
```