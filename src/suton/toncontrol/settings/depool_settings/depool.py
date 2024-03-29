from typing import List

from settings.depool_settings.auto_replenish import AutoReplenishSettings
from settings.depool_settings.prudent_elections import PrudentElectionSettings
from toncommon.models.TonAddress import TonAddress
from toncommon.serialization.json import JsonAware


class DePoolSettings(JsonAware):
    DESERIALIZE_VIA_CONSTRUCTOR = True

    def __init__(self, depool_address: str, proxy_addresses: List[str] = None, max_ticktock_period=3600,
                 prudent_election_settings: PrudentElectionSettings = None,
                 replenish_settings: AutoReplenishSettings = None, abi_url: str = None, enable_elections=True):
        assert proxy_addresses or abi_url, "Either proxy addresses or abi url need to be specified for depool settings"
        self.depool_address = depool_address
        self.proxy_addresses = proxy_addresses if proxy_addresses else []
        self.max_ticktock_period = max_ticktock_period
        self.prudent_election_settings = prudent_election_settings
        self.replenish_settings = replenish_settings
        self.abi_url = abi_url
        self.enable_elections = enable_elections
        self._last_ticktock = 0

    def get_last_ticktock(self):
        return self._last_ticktock

    def set_last_ticktock(self, timestamp):
        self._last_ticktock = timestamp

    def __str__(self):
        return "DePool: {} {}".format(TonAddress.get_short_address(self.depool_address),
                                      [TonAddress.get_short_address(prox_adr) for prox_adr in self.proxy_addresses])
