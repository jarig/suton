

class DePoolElectionEvent(object):

    def __init__(self, election_id: str, proxy: str):
        self.election_id: str = str(self._hex_to_int(election_id))
        self.proxy = proxy

    @staticmethod
    def _hex_to_int(val: str) -> int:
        if val and val.startswith("0x"):
            return int(val, 0)
        return int(val, 0)
