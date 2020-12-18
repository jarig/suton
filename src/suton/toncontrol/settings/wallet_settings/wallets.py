from toncommon.serialization.json import JsonAware


class WalletSettings(JsonAware):
    DESERIALIZE_VIA_CONSTRUCTOR = True

    def __init__(self, addr: str, name: str = ""):
        self.addr = addr
        self.name = name


class WalletAction(JsonAware):
    pass


class WalletBalanceCheckAction(WalletAction):
    DESERIALIZE_VIA_CONSTRUCTOR = True

    def __init__(self, min_balance: int = 0):
        self.min_balance = min_balance


class ActionSpec(JsonAware):
    DESERIALIZE_VIA_CONSTRUCTOR = True

    def __init__(self, wallet: WalletSettings, action: WalletAction, period: int):
        self.wallet = wallet
        self.action = action
        self.period = period
