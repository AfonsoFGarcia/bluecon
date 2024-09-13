class User:
    def __init__(self, userResponseDictionary: dict):
        self.email = userResponseDictionary['email']
        self.locale = userResponseDictionary['locale']
