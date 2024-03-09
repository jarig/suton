from abc import ABC
from typing import List

from toncommon.models.ElectionParams import ElectionParams, ElectionValidatorParams, StakeParams
from toncommon.models.depool.DePoolSyncStatus import DePoolSyncStatus


class Validator(ABC):
    """
        Represents validator, proxying interactions to/from validator node
    """

    def delete_temp_key(self, key, adnl_key):
        pass

    def delete_key(self, key):
        pass

    def get_sync_time_diff(self) -> int:
        raise NotImplementedError

    def get_sync_status(self) -> DePoolSyncStatus:
        raise NotImplementedError

    def get_new_key(self) -> str:
        raise NotImplementedError

    def prepare_election(self, key, adnl_key, election_start, election_stop) -> str:
        raise NotImplementedError

    def generate_validation_request(self, election_id, adnl_key,
                                    beneficiary_masterchain_adr, max_factor) -> str:
        raise NotImplementedError

    def sign_request(self, sign_key, election_req) -> (str, str):
        raise NotImplementedError

    def generate_validation_signed(self, beneficiary_masterchain_adr, election_id, adnl_key, public_key, signature,
                                   max_factor) -> str:
        raise NotImplementedError

    def get_elector_address(self) -> str:
        raise NotImplementedError

    def get_election_ids(self, elector_addr) -> [str]:
        raise NotImplementedError

    def get_elector_params(self) -> (ElectionParams, None):
        raise NotImplementedError

    def get_current_participant_stakes(self, elector_addr) -> List[int]:
        raise NotImplementedError

    def get_election_validator_params(self) -> (ElectionValidatorParams, None):
        raise NotImplementedError

    def get_stake_params(self) -> StakeParams:
        raise NotImplementedError

    def compute_returned_stakes(self, elector_addr, validator_addr) -> [int]:
        raise NotImplementedError

    def generate_recover_stake_req(self) -> str:
        raise NotImplementedError

