from toncommon.models.TonCoin import TonCoin
from toncommon.serialization.json import JsonAware


class AutoReplenishSettings(JsonAware):
    DESERIALIZE_VIA_CONSTRUCTOR = True

    _last_replenishment_time = 0

    def __init__(self, topup_sum: TonCoin, max_period=3600):
        """
        :param topup_sum: How many tokens to send on DePool insufficient of funds event
        :param max_period: Minimum interval of time between replenishments
        """
        self.topup_sum = topup_sum
        self.max_period = max_period

    def get_last_replenishment_time(self):
        return self._last_replenishment_time

    def set_last_replenishment_time(self, time):
        self._last_replenishment_time = time
