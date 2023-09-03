from bluecon.model.AccessDoor import AccessDoor


class Pairing:
    def __init__(self, pairingResponseDictionary: dict):
        self.id = pairingResponseDictionary['id']
        self.deviceId = pairingResponseDictionary['deviceId']
        print(pairingResponseDictionary['accessDoorMap'])
        self.accessDoorMap = {k: AccessDoor(v) for k, v in pairingResponseDictionary['accessDoorMap'].items() if v['visible']}
        pass
