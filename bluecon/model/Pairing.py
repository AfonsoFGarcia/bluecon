from json import JSONEncoder, dumps, loads


class Pairing:
    def __init__(self, pairingResponseDictionary: dict):
        pass
    
    def toJson(self) -> str:
        return dumps(self, cls = PairingJSONEncoder)
    
    @classmethod
    def fromJson(csl, json: str):
        return Pairing(loads(json))
    
class PairingJSONEncoder(JSONEncoder):
    def default(self, o: Pairing):
        return {
        }