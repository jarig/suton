from toncommon.utils import HexUtils


class TonTransaction(object):

    def __init__(self, tid: str):
        self.tid = tid

    @property
    def transaction_id(self) -> int:
        return HexUtils.hex_to_int(self.tid)

    def __str__(self):
        return f"Trans id: {self.tid}"

