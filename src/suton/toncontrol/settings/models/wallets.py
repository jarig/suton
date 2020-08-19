from utils.serialization import JsonAware


class WalletSettings(JsonAware):
    def __init__(self, addr: str, name: str = ""):
        self.addr = addr
        self.name = name

    @classmethod
    def create(cls, data: dict):
        return WalletSettings(**data)


class WalletAction(JsonAware):
    pass


class WalletBalanceCheckAction(WalletAction):

    def __init__(self, min_balance: int = 0):
        self.min_balance = min_balance

    @classmethod
    def create(cls, data: dict):
        return WalletBalanceCheckAction(**data)


class ActionSpec(JsonAware):

    def __init__(self, wallet: WalletSettings, action: WalletAction, period: int):
        self.wallet = wallet
        self.action = action
        self.period = period

    @classmethod
    def create(cls, data: dict):
        return ActionSpec(**data)
