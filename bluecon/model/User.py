from json import JSONEncoder, dumps, loads


class User:
    def __init__(self, userResponseDictionary: dict):
        self.email = userResponseDictionary['email']
        self.locale = userResponseDictionary['locale']
    
    def toJson(self) -> str:
        return dumps(self, cls = UserJSONEncoder)
    
    @classmethod
    def fromJson(csl, json: str):
        return User(loads(json))
    
class UserJSONEncoder(JSONEncoder):
    def default(self, o: User):
        return {
            "email": o.email,
            "locale": o.locale
        }