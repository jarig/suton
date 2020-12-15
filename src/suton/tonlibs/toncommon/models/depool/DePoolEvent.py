

class DePoolEvent(object):

    def __init__(self, eid: str, name: str):
        self.eid = eid
        self.name = name
        self.data = None

    def set_data(self, data: str):
        self.data = data
        self._init(data)

    def _init(self, data: str):
        # for custom implementations
        pass

    @staticmethod
    def _hex_to_int(val: str) -> int:
        if val and val.startswith("0x"):
            return int(val, 0)
        return int(val, 0)

    def __str__(self):
        return f"Event {self.name}"

    def __repr__(self):
        return f"Event: {self.name}: {self.data}"
