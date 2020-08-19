from typing import List

from toncommon.models.TonAddress import TonAddress
from utils.serialization import JsonAware


class DePoolSettings(JsonAware):

    def __init__(self, depool_address: str, proxy_addresses: List[str],
                 helper_address: str, helper_seed_name: str, helper_abi_url: str,
                 helper_ticktock_cmd_name="sendTicktock", max_ticktock_period=3600):
        self.depool_address = depool_address
        self.helper_address = helper_address
        self.helper_seed_name = helper_seed_name
        self.proxy_addresses = proxy_addresses
        self.helper_abi_url = helper_abi_url
        self.helper_ticktock_cmd_name = helper_ticktock_cmd_name
        self.max_ticktock_period = max_ticktock_period
        self._last_ticktock = 0

    def get_last_ticktock(self):
        return self._last_ticktock

    def set_last_ticktock(self, timestamp):
        self._last_ticktock = timestamp

    @classmethod
    def create(cls, data: dict):
        return DePoolSettings(**data)

    @classmethod
    def get_class_code_name(cls) -> str:
        return cls.__qualname__

    def __str__(self):
        return "DePool: {} {} {}".format(TonAddress.get_short_address(self.depool_address),
                                         [TonAddress.get_short_address(prox_adr) for prox_adr in self.proxy_addresses],
                                         TonAddress.get_short_address(self.helper_address))
