import os

from secrets.interfaces.secretmanager import SecretManagerAbstract


class KeyVault(SecretManagerAbstract):

    def __init__(self, connection_string, keys_folder):
        super().__init__(connection_string, keys_folder)

    def get_validator_seed(self):
        return None


class SecretManager(KeyVault):
    def __init__(self, connection_string, keys_folder):
        super().__init__(connection_string, keys_folder)
