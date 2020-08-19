from typing import List

from settings.base import BaseTonControlSettings
from settings.models.wallets import WalletSettings, ActionSpec, WalletBalanceCheckAction


class WalletManagementSettings(BaseTonControlSettings):
    Wallet = WalletSettings
    ActionSpec = ActionSpec
    WalletBalanceCheckAction = WalletBalanceCheckAction

    ACTION_SPECS: List[ActionSpec] = []

    @classmethod
    def get_class_code_name(cls):
        return WalletManagementSettings.__qualname__

