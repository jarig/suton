import json
import logging
import os
import threading
import time

from secrets.interfaces.secretmanager import SecretManagerAbstract
from toncommon.models.TonAddress import TonAddress
from toncommon.models.TonCoin import TonCoin
from tonfift.core import FiftCli
from tonliteclient.core import TonLiteClient
from tonoscli.core import TonosCli
from tonvalidator.core import TonValidatorEngineConsole
from tonvalidator.exceptions.connection import TonConnectionException

log = logging.getLogger("elections")


class ElectionsRoutine(object):

    class Election(object):
        def __init__(self, election_id, key, adnl_key, elector_addr, election_stake):
            self.election_id = election_id
            self.key = key
            self.adnl_key = adnl_key
            self.elector_addr = elector_addr
            self.election_stake = election_stake
            self.re_elect = False

        @staticmethod
        def from_json(data):
            election = ElectionsRoutine.Election(election_id=data['id'],
                                             key=data['key'],
                                             adnl_key=data['adnl_key'],
                                             elector_addr=data['elector_addr'],
                                             election_stake=data.get('election_stake'))
            if data.get('re_elect'):
                election.re_elect = True
            return election

        def to_json(self):
            return {
                'id': self.election_id,
                'key': self.key,
                'adnl_key': self.adnl_key,
                'elector_addr': self.elector_addr,
                'election_stake': self.election_stake,
                're_elect': self.re_elect
            }

        def __str__(self):
            return "[{}] {}".format(self.election_id, self.elector_addr)
    
    def __init__(self,
                 work_dir: str,
                 validation_engine_console: TonValidatorEngineConsole,
                 lite_client: TonLiteClient,
                 tonos_cli: TonosCli,
                 fift_cli: FiftCli,
                 secret_manager: SecretManagerAbstract,
                 stake_to_make="30%",  # either % or absolute value
                 min_sync_time=50,
                 min_balance: int = 0,
                 stake_max_factor: str = '3',
                 join_elections=True):
        self._work_dir = work_dir
        self._vec = validation_engine_console
        self._lite_client = lite_client
        self._tonos_cli = tonos_cli
        self._fift_cli = fift_cli
        self._secret_manager = secret_manager
        self._min_sync_time = min_sync_time
        self._min_balance = min_balance
        self._stake_to_make = stake_to_make
        self._stake_max_factor = stake_max_factor
        self._join_elections = join_elections
        self._active_elections: list[ElectionsRoutine.Election] = []
        self._active_election_file = os.path.join(self._work_dir, "active_elections.json")
        self._check_node_sync_interval_seconds = 2 * 60
        self._check_elections_interval_seconds = 30 * 60


    def load_active_elections(self):
        if os.path.exists(self._active_election_file):
            with open(self._active_election_file) as f:
                election_data = json.load(f)
            for election in election_data['elections']:
                self._active_elections.append(ElectionsRoutine.Election.from_json(election))
        return self._active_elections

    def save_active_elections(self):
        with open(self._active_election_file, "w") as f:
            f.write(json.dumps({
                'elections': [election.to_json() for election in self._active_elections]
            }))

    def start(self):
        if not os.path.exists(self._work_dir):
            os.makedirs(self._work_dir)
        thread = threading.Thread(target=self._routine, daemon=True)
        thread.start()

    def _compute_stake(self, value):
        if '%' in self._stake_to_make:
            factor = float(self._stake_to_make.replace('%', '')) / 100
            return int(value * factor)
        return int(self._stake_to_make)

    def _get_active_election_by_id(self, eid) -> Election:
        for election in self._active_elections:
            if str(election.election_id) == str(eid):
                return election
        return None

    def _cleanup_election(self, election: Election):
        self._vec.delete_temp_key(election.key, election.adnl_key)
        self._vec.delete_key(election.key)
    
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
        self.load_active_elections()
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
                        log.info("Election ids: {}".format(election_ids))
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
                            new_election_ids = []
                            for eid in election_ids:
                                active_election = self._get_active_election_by_id(eid)
                                if not active_election:
                                    new_election_ids.append(eid)
                                elif active_election.re_elect:
                                    log.info("Cleaning up election keys, preparing for re-election")
                                    self._cleanup_election(active_election)
                                    self._active_elections.remove(active_election)
                                    new_election_ids.append(eid)
                            if not new_election_ids:
                                log.info("No new elections found, already participating in all of the existing ones.")
                            else:
                                balance_left = validator_balance
                                stake_per_election = validator_balance / len(new_election_ids)
                                election_stake = self._compute_stake(stake_per_election)
                                # there are some elections in which we want to participate
                                log.info("Going to join these elections: {}".format(new_election_ids))
                                for election_id in new_election_ids:
                                    if balance_left < self._min_balance:
                                        log.warning("Skipping participation in {}, as otherwise will go below minimum specified balance ({})".format(election_id,
                                                                                                                                                     self._min_balance))
                                        continue
                                    log.info("Joining election: {} with stake {}".format(election_id, election_stake))
                                    log.info("Getting min stake...")
                                    stake_params = self._lite_client.get_stake_params()
                                    if stake_params:
                                        log.info("Got stake params")
                                        if election_stake < stake_params.min_stake:
                                            log.warning("Can't participate in this election as stake is less than minimal: {} < {}".format(election_stake, stake_params.min_stake))
                                        if election_stake > stake_params.max_stake:
                                            log.info("Reducing stake to {}".format(stake_params.max_stake))
                                            # we staked more than allowed, so reduce
                                            election_stake = stake_params.max_stake
                                    log.info("Generating keys...")
                                    election_key = self._vec.get_new_key()
                                    election_adnl_key = self._vec.get_new_key()
                                    # create election record
                                    election_data = ElectionsRoutine.Election(election_id, election_key,
                                                                              election_adnl_key, elector_addr,
                                                                              election_stake)
                                    try:
                                        log.info("Getting elector params...")
                                        elector_params = self._lite_client.get_elector_params()
                                        election_stop_time = int(election_id) + 1000 + elector_params.elections_start_before + \
                                                             elector_params.validators_elected_for + \
                                                             elector_params.elections_end_before + \
                                                             elector_params.stake_held_for
                                        log.info("Preparing election request...")
                                        self._vec.prepare_election(election_key, election_adnl_key,
                                                                   election_start=election_id, election_stop=election_stop_time)
                                        log.info("Generating validation request...")
                                        election_req = self._fift_cli.generate_validation_req(validator_addr,
                                                                                              election_start=election_id,
                                                                                              key_adnl=election_adnl_key,
                                                                                              max_factor=self._stake_max_factor)
                                        # sign request
                                        log.info("Signing election request...")
                                        election_req_signature, pub_key = self._vec.sign_request(election_key, election_req)
                                        log.info("Generating signed election request...")
                                        election_signed = self._fift_cli.generate_validation_signed(validator_addr,
                                                                                                    election_id, election_adnl_key,
                                                                                                    public_key=pub_key,
                                                                                                    signature=election_req_signature,
                                                                                                    max_factor=self._stake_max_factor)

                                        log.info("Submitting election transaction...")
                                        transaction = self._tonos_cli.submitTransaction(validator_addr,
                                                                                        elector_addr,
                                                                                        election_stake, election_signed,
                                                                                        private_key=self._secret_manager.get_validator_seed(), bounce=True)
                                        log.info("Election transaction submitted: {}".format(transaction))
                                        custodian_seeds = self._secret_manager.get_custodian_seeds()
                                        if custodian_seeds:
                                            log.info("Confirming transaction by custodians")
                                            for custodian_seed in self._secret_manager.get_custodian_seeds():
                                                self._tonos_cli.confirmTransaction(validator_addr, transaction.tid, custodian_seed)
                                            log.info("Confirmed.")
                                        log.info("Transaction id: {}".format(transaction.tid))
                                    except:
                                        self._cleanup_election(election_data)
                                        raise
                                    self._active_elections.append(election_data)
                                    balance_left -= election_stake
                        if finished_elections:
                            log.info("Finished elections: {}".format(finished_elections))
                            for finished_election in finished_elections:
                                try:
                                    log.info("Requesting bounty from: {}".format(finished_election))
                                    # no election happening
                                    recover_amounts = self._lite_client.compute_returned_stakes(finished_election.elector_addr, validator_addr)
                                    if recover_amounts:
                                        log.info("Recovering: {}".format(recover_amounts))
                                        recover_req = self._fift_cli.generate_recover_stake_req()
                                        transaction = self._tonos_cli.submitTransaction(validator_addr,
                                                                                        TonAddress.set_address_prefix(finished_election.elector_addr, TonAddress.Type.MASTER_CHAIN),
                                                                                        value=TonCoin.convert_to_nano_tokens(1),
                                                                                        payload=recover_req,
                                                                                        private_key=self._get_wallet_seed(),
                                                                                        bounce=True)
                                        log.info("Submitted transaction for funds recovery: {}".format(transaction))
                                    else:
                                        log.info("Nothing to recover: {}".format(recover_amounts))
                                    log.info("Removing unused keys")
                                    self._cleanup_election(finished_election)
                                except Exception as ex:
                                    log.exception("Failed to request bounty: {}".format(ex))
                                    self._active_elections.append(finished_election)
                            pass
                        self.save_active_elections()
                    pass
            except Exception as ex:
                log.exception("Error in validator routine: {}".format(ex))
            log.info("Sleeping for: {}s".format(sleep_interval))
            time.sleep(sleep_interval)

