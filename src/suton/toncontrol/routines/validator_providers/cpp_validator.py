from typing import List

from toncommon.models.depool.DePoolSyncStatus import DePoolSyncStatus
from tonfift.core import FiftCli
from tonliteclient.core import TonLiteClient
from toncommon.models.ElectionParams import ElectionParams, ElectionValidatorParams, StakeParams
from tonvalidator.core import TonValidatorEngineConsole
from routines.validator_providers.core import Validator


class CPPValidator(Validator):

    def __init__(self, vec: TonValidatorEngineConsole, fift_cli: FiftCli,
                 lite_client: TonLiteClient):
        self._vec = vec
        self._fift_cli = fift_cli
        self._lite_client = lite_client

    def delete_temp_key(self, key, adnl_key):
        self._vec.delete_temp_key(key, adnl_key)

    def delete_key(self, key):
        self._vec.delete_key(key)

    def get_sync_time_diff(self) -> int:
        return self._vec.get_sync_time_diff()

    def get_sync_status(self) -> DePoolSyncStatus:
        diff = self.get_sync_time_diff()
        return DePoolSyncStatus(time_diff=diff, sync_status="unknown")

    def get_new_key(self) -> str:
        return self._vec.get_new_key()

    def prepare_election(self, key, adnl_key, election_start, election_stop):
        self._vec.prepare_election(key, adnl_key,
                                   election_start=election_start,
                                   election_stop=election_stop)

    def generate_validation_request(self, election_id, adnl_key,
                                    beneficiary_masterchain_adr, max_factor):
        return self._fift_cli.generate_validation_req(beneficiary_masterchain_adr,
                                                      election_start=election_id,
                                                      key_adnl=adnl_key,
                                                      max_factor=max_factor)

    def sign_request(self, sign_key, election_req) -> (str, str):
        return self._vec.sign_request(sign_key, election_req)

    def generate_validation_signed(self, beneficiary_masterchain_adr, election_id, adnl_key, public_key, signature,
                                   max_factor) -> str:
        return self._fift_cli.generate_validation_signed(beneficiary_masterchain_adr,
                                                         election_id, adnl_key,
                                                         public_key=public_key, signature=signature,
                                                         max_factor=max_factor)

    def get_elector_address(self) -> str:
        return self._lite_client.get_elector_address()

    def get_election_ids(self, elector_addr) -> [str]:
        return self._lite_client.get_election_ids(elector_addr)

    def get_elector_params(self) -> (ElectionParams, None):
        return self._lite_client.get_elector_params()

    def get_current_participant_stakes(self, elector_addr) -> List[int]:
        return self._lite_client.get_current_participant_stakes(elector_addr)

    def get_election_validator_params(self) -> (ElectionValidatorParams, None):
        return self._lite_client.get_election_validator_params()

    def get_stake_params(self) -> StakeParams:
        return self._lite_client.get_stake_params()

    def compute_returned_stakes(self, elector_addr, validator_addr) -> List[int]:
        return self._lite_client.compute_returned_stakes(elector_addr, validator_addr)

    def generate_recover_stake_req(self) -> str:
        return self._fift_cli.generate_recover_stake_req()
