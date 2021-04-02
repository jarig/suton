from typing import List

from rustconsole.core import RustConsole
from tonliteclient.models.ElectionParams import ElectionParams, ElectionValidatorParams, StakeParams
from tonoscli.core import TonosCli
from routines.validator_providers.core import Validator


class RustValidator(Validator):

    def __init__(self, console: RustConsole, tonos_cli: TonosCli, elector_abi_url: str):
        self._console = console
        self._tonos_cli = tonos_cli
        self._elector_abi_url = elector_abi_url
        self._election_data = {}

    def delete_temp_key(self, key, adnl_key):
        pass

    def delete_key(self, key):
        pass

    def get_sync_time_diff(self) -> int:
        return self._console.get_sync_time_diff()

    def get_new_key(self) -> str:
        return ""

    def prepare_election_payload(self):
        pass

    def prepare_election(self, key, adnl_key, election_start, election_stop) -> str:
        self._election_data = {
            "election_start": election_start,
            "election_stop": election_stop
        }
        return ""

    def generate_validation_request(self, election_id, adnl_key,
                                    beneficiary_masterchain_adr, max_factor):
        return ""

    def sign_request(self, sign_key, election_req) -> (str, str):
        return "", ""

    def generate_validation_signed(self, beneficiary_masterchain_adr, election_id, adnl_key, public_key, signature,
                                   max_factor) -> str:
        return self._console.get_signed_election_req(beneficiary_masterchain_adr,
                                                     self._election_data["election_start"],
                                                     self._election_data["election_end"], max_factor=max_factor)

    def get_elector_address(self) -> str:
        # get config 1
        return self._tonos_cli.get_elector_address()

    def get_election_ids(self, elector_addr) -> [str]:
        return self._tonos_cli.get_active_election_ids(elector_addr, elector_abi_url=self._elector_abi_url)

    def get_elector_params(self) -> (ElectionParams, None):
        # get config 15
        return self._tonos_cli.get_elector_params()

    def get_current_participant_stakes(self, elector_addr) -> List[int]:
        # TODO: implement when Rust supports this
        return []

    def get_election_validator_params(self) -> (ElectionValidatorParams, None):
        # get config 16
        return self._tonos_cli.get_election_validator_params()

    def get_stake_params(self) -> StakeParams:
        # get config 17
        return self._tonos_cli.get_stake_params()

    def compute_returned_stakes(self, elector_addr, validator_addr) -> [int]:
        return self._tonos_cli.compute_returned_stake(elector_addr, validator_addr,
                                                      elector_abi_url=self._elector_abi_url)

    def generate_recover_stake_req(self) -> str:
        # console -c "recover_stake"
        return self._console.recover_stake_request()

