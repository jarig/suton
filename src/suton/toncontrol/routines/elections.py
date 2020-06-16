import logging
import threading
import time

from secrets.interfaces.secretmanager import SecretManagerAbstract
from toncommon.models.TonCoin import TonCoin
from tonfift.core import FiftCli
from tonliteclient.core import TonLiteClient
from tonoscli.core import TonosCli
from tonvalidator.core import TonValidatorEngineConsole
from tonvalidator.exceptions.connection import TonConnectionException

log = logging.getLogger("elections")


class ElectionsRoutine(object):

    class Election(object):
        def __init__(self, election_id, key, adnl_key, elector_addr):
            self.election_id = election_id
            self.key = key
            self.adnl_key = adnl_key
            self.elector_addr = elector_addr

        def __str__(self):
            return "[{}] {}".format(self.election_id, self.elector_addr)
    
    def __init__(self, validation_engine_console: TonValidatorEngineConsole,
                 lite_client: TonLiteClient,
                 tonos_cli: TonosCli,
                 fift_cli: FiftCli,
                 secret_manager: SecretManagerAbstract,
                 stake_to_make="25%",  # either % or absolute value
                 min_sync_time=50,
                 join_elections=True):
        self._vec = validation_engine_console
        self._lite_client = lite_client
        self._tonos_cli = tonos_cli
        self._fift_cli = fift_cli
        self._secret_manager = secret_manager
        self._min_sync_time = min_sync_time
        self._stake_to_make = stake_to_make
        self._join_elections = join_elections
        self._active_elections: list[ElectionsRoutine.Election] = []
        self._check_node_sync_interval_seconds = 2 * 60
        self._check_elections_interval_seconds = 30 * 60

    def start(self):
        thread = threading.Thread(target=self._routine, daemon=True)
        thread.start()

    def _compute_stake(self, value):
        if '%' in self._stake_to_make:
            factor = float(self._stake_to_make.replace('%', '')) / 100
            return int(value * factor)
        return int(self._stake_to_make)

    def _get_active_election_by_id(self, eid):
        for election in self._active_elections:
            if str(election.election_id) == str(eid):
                return election
        return None
    
    def _get_wallet_seed(self):
        return self._secret_manager.get_validator_seed()

    def _get_wallet_address(self):
        return self._secret_manager.get_validator_address()

    def _check_if_synced(self):
        try:
            time_diff = self._vec.get_sync_time_diff()
            log.debug("Time diff: {}".format(time_diff))
            if time_diff <= self._min_sync_time:
                return True
        except TonConnectionException as ex:
            log.error("Failed to connect to TON Validator: {}".format(ex))
        except Exception as ex:
            log.error("Failed to get time-diff stats: {}".format(ex))
        return False

    def _routine(self):
        while True:
            sleep_interval = self._check_elections_interval_seconds
            try:
                is_synced = self._check_if_synced()
                if not is_synced:
                    sleep_interval = self._check_node_sync_interval_seconds
                    log.info("Validator not synced, waiting until it synchronizes. Next check after: {}s".format(sleep_interval))
                else:
                    log.info("Validator is in synced state.")
                    if self._join_elections:
                        log.info("Checking for new elections")
                        validator_addr = self._secret_manager.get_validator_address()
                        validator_account = self._tonos_cli.get_account(validator_addr)
                        validator_balance = validator_account.balance
                        log.info("Validator balance: {}".format(validator_balance))
                        # get address of elector contract
                        elector_addr = self._lite_client.get_elector_address()
                        election_ids = self._lite_client.get_election_ids(elector_addr)
                        log.info("Elector address: {}".format(elector_addr))
                        # cleanup current active elections
                        finished_elections = []
                        for active_election in self._active_elections[:]:
                            if str(active_election.election_id) not in election_ids:
                                finished_elections.append(active_election)
                                self._active_elections.remove(active_election)
                        if not election_ids:
                            log.info("No elections happening at a moment.")
                        else:
                            log.info("Current active elections: {}".format(election_ids))
                            new_election_ids = [eid for eid in election_ids if not self._get_active_election_by_id(eid)]
                            if not new_election_ids:
                                log.info("No new elections found, already participating in all of the existing ones.")
                            else:
                                stake_per_election = validator_balance / len(new_election_ids)
                                election_stake = self._compute_stake(stake_per_election)
                                # there are some elections in which we want to participate
                                log.info("Going to join these elections: {}".format(new_election_ids))
                                for election_id in new_election_ids:
                                    log.info("Joining election: {}".format(election_id))
                                    election_key = self._vec.get_new_key()
                                    election_adnl_key = self._vec.get_new_key()
                                    elector_params = self._lite_client.get_elector_params()
                                    election_stop_time = int(election_id) + 1000 + elector_params.elections_start_before + \
                                                         elector_params.validators_elected_for + \
                                                         elector_params.elections_end_before + \
                                                         elector_params.stake_held_for
                                    self._vec.prepare_election(election_key, election_adnl_key,
                                                               election_start=election_id, election_stop=election_stop_time)
                                    election_req = self._fift_cli.generate_validation_req(validator_addr,
                                                                                          election_start=int(election_id),
                                                                                          key_adnl=election_adnl_key)
                                    # sign request
                                    election_req_signature = self._vec.sign_request(election_key, election_req)
                                    election_signed = self._fift_cli.generate_validation_signed(validator_addr,
                                                                                                int(election_id), election_adnl_key,
                                                                                                election_key, election_req_signature)

                                    transaction = self._tonos_cli.submitTransaction(validator_addr, elector_addr,
                                                                                    TonCoin(election_stake), election_signed,
                                                                                    private_key=self._secret_manager.get_validator_seed(), bounce=True)
                                    log.info("Election transaction submitted: {}".format(transaction))
                                    log.info("Confirming transaction by custodians")
                                    for custodian_seed in self._secret_manager.get_custodian_seeds():
                                        self._tonos_cli.confirmTransaction(validator_addr, transaction.tid, custodian_seed)
                                    log.info("Confirmed.")
                                    # record that we participated in the election
                                    election_data = ElectionsRoutine.Election(election_id, election_key,
                                                                              election_adnl_key, elector_addr)
                                    self._active_elections.append(election_data)
                        if finished_elections:
                            log.info("Finished elections: {}".format(finished_elections))
                            for finished_election in finished_elections:
                                try:
                                    log.info("Requesting bounty from: {}".format(finished_election))
                                    # no election happening
                                    recover_amount = self._lite_client.compute_returned_stakes(finished_election.elector_addr, validator_addr)
                                    if recover_amount:
                                        recover_req = self._fift_cli.generate_recover_stake_req()
                                        transaction = self._tonos_cli.submitTransaction(validator_addr, finished_election.elector_addr,
                                                                                        value=TonCoin(1),
                                                                                        payload=recover_req,
                                                                                        private_key=self._get_wallet_seed(),
                                                                                        bounce=True)
                                        log.info("Submitted transaction for funds recovery: {}".format(transaction))
                                    # TODO: remove keys from keyring
                                except Exception as ex:
                                    log.exception("Failed to request bounty: {}".format(ex))
                                    self._active_elections.append(finished_election)
                            pass
                    pass
            except Exception as ex:
                log.exception("Error in validator routine: {}".format(ex))
            log.info("Sleeping for: {}s".format(sleep_interval))
            time.sleep(sleep_interval)

