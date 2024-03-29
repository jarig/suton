from typing import List, Optional


class SecretManagerAbstract(object):

    def __init__(self, connection_string, keys_folder):
        self._connection_string = connection_string
        self._keys_folder = keys_folder

    def get_validator_address(self):
        # not really a secret, but more convenient to store nxt to seed
        raise NotImplementedError("Implement this method")

    def get_secret_by_name(self, name: str) -> str:
        raise NotImplementedError("Implement this method")

    def get_validator_seed(self):
        raise NotImplementedError("Implement this method")

    def get_custodian_seeds(self) -> List[str]:
        """
        Keys of custodians whose confirmations should be automated
        :return:
        """
        return []

    def get_project_secret(self) -> Optional[str]:
        return None
