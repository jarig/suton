

class DePoolLowBalanceEvent(object):

    def __init__(self, balance: str):
        self.balance: int = self._hex_to_int(balance)

    @staticmethod
    def _hex_to_int(val: str) -> int:
        if val and val.startswith("0x"):
            return int(val, 0)
        return int(val, 0)
