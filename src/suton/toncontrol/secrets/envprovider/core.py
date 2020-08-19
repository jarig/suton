import base64
import json
import os

import rsa
from rsa import PrivateKey

from secrets.interfaces.secretmanager import SecretManagerAbstract


class EnvSecretProvider(SecretManagerAbstract):

    def __init__(self, connection_string, keys_folder):
        super().__init__(connection_string, keys_folder)
        self._data = json.loads(connection_string)
        self._private_key = None
        if self._data.get("encryption_key_name"):
            if not os.path.exists(os.path.join(keys_folder, self._data.get("encryption_key_name"))):
                raise Exception("Couldn't initialize environment-based secret-manager, as encryption name with name {} do not exist.".format(
                    self._data.get("encryption_key_name")))
            with open(os.path.join(keys_folder, self._data.get("encryption_key_name")), "rb") as f:
                # PEM key
                self._private_key = PrivateKey.load_pkcs1(f.read())

    def _decrypt(self, data: str) -> str:
        return rsa.decrypt(base64.decodebytes(data.encode()), self._private_key).decode().strip()

    def get_validator_address(self):
        return self._data.get("validator_address")

    def get_secret_by_name(self, name: str) -> str:
        seed = self._data.get("secrets").get(name)
        if self._private_key:
            seed = self._decrypt(seed)
        return seed

    def get_validator_seed(self):
        if self._private_key:
            return self._decrypt(self._data.get("validator_seed"))
        return self._data.get("validator_seed").strip()

    def get_custodian_seeds(self):
        if self._private_key:
            decr = []
            for seed in self._data.get("custodian_seeds", []):
                decr.append(self._decrypt(seed))
            return decr
        return self._data.get("custodian_seeds", [])


class SecretManager(EnvSecretProvider):
    pass
