# BlueCon

Library for connecting to Fermax Blue supported doorbells.

It is used by the [HASS-BlueCon](https://github.com/paquiro/hass-bluecon) Home Assistant integration.

### Tested Devices:

* Fermax Veo XS WiFi (9449)
* Fermax VEO WIFI MONITOR

## Features

* Sign in with a Fermax Blue account and list the paired devices.
* Get information about the user and the devices.
* Open a door.
* Receive ring notifications (`Call`, `CallEnd` and `LoginInNewDevice`) through Firebase Cloud Messaging.
* Read the call registry and download the photo of a call.

## Requirements

* Python 3.10 or newer.
* The Fermax API **client id and secret**. Fermax has no official API, so they are not provided by this library; you have to supply your own.
* To receive ring notifications you also need the Firebase settings of the Fermax Blue app: Google API key, sender id, app id, project id and package name. They are optional if you only want to open doors and read data.

## Installation

The version published on PyPI (`0.4.3`) does not include the push notification fixes. Install this repository instead, preferably pinned to a commit:

```sh
pip install "bluecon @ git+https://github.com/paquiro/bluecon.git@<commit>"
```

## Usage

See the [quickstart](docs/quickstart.md).

## Notes

* Registering the FCM token only with the legacy `/notification/api/v1/apptoken` endpoint answers `200` but did not result in pushes being delivered. This library registers it with `POST /notification/api/v2/apptoken`, using the payload of the official app, and falls back to v1. This happens every time the listener starts.
* The call registry is scoped by the FCM token of the app, so it is only useful once the notification listener has started.
* `startNotificationListener` accepts an optional `hass` argument. When given, the push receiver runs in an executor job and the callbacks run on that Home Assistant event loop.
* Everything is logged through the `bluecon` logger. Debug logging of the `push_receiver` module prints the full push payload, including an access token, so do not enable it unless you need it.

## Acknowledgements

I'd like to thank all contributors of [push_receiver](https://github.com/olijeffers0n/push_receiver) and its many forks for providing a library that can receive push notifications from Firebase. This is the essential part of how Fermax Blue works in terms of receiving the doorbell rings and without it this project would be close to pointless. This library depends on the `rustPlusPushReceiver` package, which provides the `push_receiver` module.
