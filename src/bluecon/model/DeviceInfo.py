class DeviceInfo:
    def __init__(self, deviceInfoResponse: dict):
        self.deviceId = deviceInfoResponse['deviceId']
        self.connectionState = deviceInfoResponse['connectionState']
        self.family = deviceInfoResponse['family']
        self.type = deviceInfoResponse['type']
        self.subType = deviceInfoResponse['subtype']
        self.photoCaller = deviceInfoResponse['photocaller']
        self.wirelessSignal = deviceInfoResponse['wirelessSignal']