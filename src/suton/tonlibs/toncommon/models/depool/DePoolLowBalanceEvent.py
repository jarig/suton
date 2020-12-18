import json

from toncommon.models.depool.DePoolEvent import DePoolEvent
from toncommon.utils import HexUtils


class DePoolLowBalanceEvent(DePoolEvent):

    balance = 0

    def _init(self, raw_data: str):
        data = json.loads(raw_data)
        self.balance = str(HexUtils.hex_to_int(data.get("replenishment")))

    def __str__(self):
        return f"LowBalance {self.balance}"
