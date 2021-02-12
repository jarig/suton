from typing import List

from settings.base import BaseTonControlSettings
from settings.elections import ElectionSettings
from settings.wallet_management import WalletManagementSettings
from toncommon.serialization.json import JsonAware


class TonSettings(BaseTonControlSettings):
    CONFIGS_DIR = None

    # Rust node
    RUST_TON_NODE_GITHUB_REPO = "https://github.com/tonlabs/ton-labs-node.git"
    RUST_TON_NODE_GITHUB_COMMIT_ID = "master"
    RUST_TONOS_CLI_GITHUB_COMMIT_ID = "master"
    RUST_TON_NODE_TOOLS_GITHUB_COMMIT_ID = "master"

    # Intended to be overriden and values set to appropriate values
    # Note: do not commit sensitive data, and instead use Python to derive them in run-time from secure places
    NODE_NAME = 'ton-validator-0'

    # DOCKER_HOST parameter, ex: ssh://root@1.1.1.1
    DOCKER_HOST = None
    TON_WORK_DIR = None
    TON_ENV = "main.ton.dev"
    TON_ENDPOINTS = None
    TON_CONTROL_WORK_DIR = '/var/ton-control'
    TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING = None  # never commit your raw seeds, encrypt them or use connection-strings to vaults
    TON_CONTROL_QUEUE_NAME = 'ton-validator-0'
    TONOS_CLI_CONFIG_URL = None
    VALIDATOR_MAX_SYNC_DIFF = 30

    TON_VALIDATOR_CONFIG_URL = "https://raw.githubusercontent.com/tonlabs/main.ton.dev/master/configs/ton-global.config.json"

    TON_CONTROL_VALIDATOR_NETWORK_ADDR = 'tonvalidator:3031'
    TON_CONTROL_VALIDATOR_LITE_CLIENT_ADDR = 'tonvalidator:3031'

    TON_CONTROL_SECRET_MANAGER_PROVIDER = 'secrets.envprovider.core'
    TON_CONTROL_QUEUE_PROVIDER = 'mqueue.azureservicebus.core'

    TON_VALIDATOR_TYPE = "rust"
    ELECTOR_ABI_URL = None  # required for Rust node

    ELECTIONS_SETTINGS: ElectionSettings = ElectionSettings()
    WALLET_MANAGEMENT_SETTINGS: WalletManagementSettings = WalletManagementSettings()

    def init(self):
        if not self.TONOS_CLI_CONFIG_URL:
            self.TONOS_CLI_CONFIG_URL = f"https://{self.TON_ENV}"

    def get_queue_name(self):
        if self.TON_CONTROL_QUEUE_NAME:
            queue_name = self.TON_CONTROL_QUEUE_NAME
        elif self.NODE_NAME:
            queue_name = "node-{}".format(self.NODE_NAME)
        else:
            import socket
            queue_name = "node-{}".format(socket.gethostname())
        return queue_name

    def validate(self):
        if self.TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING is None:
            raise Exception("You need to set secret-manager connection string value")

    @classmethod
    def get_class_code_name(cls):
        return TonSettings.__qualname__

    @staticmethod
    def from_json(data: dict, classes: List['JsonAware'] = None) -> 'TonSettings':
        return BaseTonControlSettings.from_json(data, classes=classes)
