class AccessDoor:
    def __init__(self, accessDoorMap: dict):
        self.title = accessDoorMap['title']
        self.block = accessDoorMap['accessId']['block']
        self.subBlock = accessDoorMap['accessId']['subblock']
        self.number = accessDoorMap['accessId']['number']

    def getDirectOpenDoorParamsRequest(self):
        return {
            'block': self.block,
            'number': self.number,
            'subblock': self.subBlock
        }
