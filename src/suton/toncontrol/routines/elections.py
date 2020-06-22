import datetime
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

from logstash.client import LogStashClient

log = logging.getLogger("elections")


class ElectionsRoutine(object):

    class Election(object):
        def __init__(self, election_id, elector_addr, key=None, adnl_key=None, election_stake: int = 0):
            self.election_id = election_id
            self.key = key
            self.adnl_key = adnl_key
            self.elector_addr = elector_addr
            self.election_stake = election_stake
            self.restake = False

        @staticmethod
        def from_json(data):
            election = ElectionsRoutine.Election(election_id=data['id'],
                                                 elector_addr=data['elector_addr'],
                                                 key=data.get('key'),
                                                 adnl_key=data.get('adnl_key'),
                                                 election_stake=data.get('election_stake', 0))
            if data.get('restake'):
                election.restake = True
            return election

        def to_json(self):
            return {
                'id': self.election_id,
                'key': self.key,
                'adnl_key': self.adnl_key,
                'elector_addr': self.elector_addr,
                'election_stake': self.election_stake,
                'restake': self.restake
            }

        def __str__(self):
            return "[{}] {}".format(self.election_id, self.elector_addr)

        def __repr__(self):
            return str(self)

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
        self._check_elections_interval_seconds = 15 * 60

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

    def _compute_stake(self, balance):
        if '%' in self._stake_to_make:
            factor = float(self._stake_to_make.replace('%', '')) / 100
            return int(balance * factor)
        return min(balance, TonCoin.convert_to_nano_tokens(int(self._stake_to_make)))

    def _get_active_election_by_id(self, eid) -> Election:
        for election in self._active_elections:
            if str(election.election_id) == str(eid):
                return election
        return None

    def _cleanup_election(self, election: Election):
        if election.key and election.adnl_key:
            self._vec.delete_temp_key(election.key, election.adnl_key)
        if election.key:
            self._vec.delete_key(election.key)

    def _get_wallet_seed(self):
        return self._secret_manager.get_validator_seed()

    def _get_wallet_address(self):
        return self._secret_manager.get_validator_address()

    def _check_if_synced(self):
        try:
            time_diff = self._vec.get_sync_time_diff()
            log.debug("Time diff: {}".format(time_diff))
            self._send_telemetry('node_status', {'time_diff': time_diff})
            if time_diff <= self._min_sync_time:
                return True
        except TonConnectionException as ex:
            log.error("Failed to connect to TON Validator: {}".format(ex))
        except Exception as ex:
            log.error("Failed to get time-diff stats: {}".format(ex))
        return False

    def _send_telemetry(self, data_type, data: dict):
        data['timestamp'] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        data['data_type'] = data_type
        LogStashClient.get_client().send_data('elections', data)

    def _routine(self):
        self.load_active_elections()
        while True:
            election_status_telemetry_data = {}
            sleep_interval = self._check_elections_interval_seconds
            try:
                is_synced = self._check_if_synced()
                if not is_synced:
                    sleep_interval = self._check_node_sync_interval_seconds
                    log.info("Validator not synced, waiting until it synchronizes. Next check after: {}s".format(sleep_interval))
                    election_status_telemetry_data['error'] = 'out of sync'
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
                        election_status_telemetry_data = {'validator_address': validator_addr,
                                                          'balance': validator_balance,
                                                          'election_ids': election_ids}
                        # cleanup current active elections
                        finished_elections = []
                        for active_election in self._active_elections:
                            telemetry_data = {
                                'election_id': active_election.election_id,
                                'election_stake': active_election.election_stake
                            }
                            if str(active_election.election_id) not in election_ids:
                                finished_elections.append(active_election)
                                self._send_telemetry('finished_elections', telemetry_data)
                            else:
                                self._send_telemetry('active_elections', telemetry_data)
                        if not election_ids:
                            log.info("No elections happening at a moment.")
                        else:
                            log.info("Current active elections: {}".format(election_ids))
                            new_elections = []  # type: list[ElectionsRoutine.Election]
                            for eid in election_ids:
                                active_election = self._get_active_election_by_id(eid)
                                if not active_election:
                                    new_elections.append(ElectionsRoutine.Election(election_id=eid,
                                                                                   elector_addr=elector_addr))
                                elif active_election.restake:
                                    log.info("Will re-stake for {}".format(active_election))
                                    # reset restake flag
                                    active_election.restake = False
                                    new_elections.append(active_election)
                            if not new_elections:
                                log.info("No new elections found, already participating in all of the existing ones.")
                            else:
                                balance_left = validator_balance
                                # there are some elections in which we want to participate
                                log.info("Going to join these elections: {}".format(new_elections))
                                log.info("Getting min stake...")
                                stake_params = self._lite_client.get_stake_params()
                                for new_election in new_elections:
                                    stake_per_election = validator_balance / len(new_elections)
                                    election_stake = self._compute_stake(stake_per_election)
                                    election_telemetry = {
                                        'election_id': new_election.election_id
                                    }
                                    if balance_left < self._min_balance:
                                        election_telemetry['error'] = 'Not enough balance'
                                        log.warning("Skipping participation in {}, as otherwise will go below minimum specified balance ({})".format(new_election.election_id,
                                                                                                                                                     self._min_balance))
                                        continue
                                    log.info("Joining election: {} with stake {}".format(new_election.election_id, election_stake))
                                    if stake_params:
                                        log.info("Got stake params")
                                        election_telemetry['min_stake'] = stake_params.min_stake
                                        election_telemetry['max_stake'] = stake_params.max_stake
                                        if election_stake < stake_params.min_stake:
                                            log.warning("Can't participate in this election as stake is less than minimal: {} < {}".format(election_stake, stake_params.min_stake))
                                            continue
                                        if election_stake > stake_params.max_stake:
                                            log.info("Reducing stake to {}".format(stake_params.max_stake))
                                            # we staked more than allowed, so reduce
                                            election_stake = stake_params.max_stake
                                    election_telemetry['election_id'] = new_election.election_id
                                    election_telemetry['election_stake'] = election_stake
                                    new_election.election_stake += election_stake
                                    need_election_prepare = False
                                    if not new_election.key:
                                        log.info("Generating keys...")
                                        need_election_prepare = True
                                        new_election.key = self._vec.get_new_key()
                                        new_election.adnl_key = self._vec.get_new_key()
                                    else:
                                        log.info("Using existing/provided keys for the election")
                                    log.info("Perm key hash: {}".format(new_election.key))
                                    log.info("ADNL key hash: {}".format(new_election.adnl_key))
                                    try:
                                        log.info("Getting elector params...")
                                        elector_params = self._lite_client.get_elector_params()
                                        election_stop_time = int(new_election.election_id) + 1000 + elector_params.elections_start_before + \
                                                             elector_params.validators_elected_for + \
                                                             elector_params.elections_end_before + \
                                                             elector_params.stake_held_for
                                        if need_election_prepare:
                                            log.info("Preparing election request...")
                                            self._vec.prepare_election(new_election.key, new_election.adnl_key,
                                                                       election_start=new_election.election_id,
                                                                       election_stop=election_stop_time)
                                        log.info("Generating validation request...")
                                        election_req = self._fift_cli.generate_validation_req(validator_addr,
                                                                                              election_start=new_election.election_id,
                                                                                              key_adnl=new_election.adnl_key,
                                                                                              max_factor=self._stake_max_factor)
                                        # sign request
                                        log.info("Signing election request...")
                                        election_req_signature, pub_key = self._vec.sign_request(new_election.key, election_req)
                                        log.info("Generating signed election request...")
                                        election_signed = self._fift_cli.generate_validation_signed(validator_addr,
                                                                                                    new_election.election_id, new_election.adnl_key,
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
                                        if not self._get_active_election_by_id(new_election.election_id):
                                            self._active_elections.append(new_election)
                                        balance_left -= election_stake
                                        log.info("Transaction id: {}, election: {}".format(transaction.tid,
                                                                                           new_election.election_id))
                                        election_telemetry['elected'] = True
                                    except Exception as ex:
                                        election_status_telemetry_data['error'] = str(ex)
                                        election_telemetry['error'] = str(ex)
                                        self._cleanup_election(new_election)
                                        raise
                                    self._send_telemetry('election_join', election_telemetry)
                        if finished_elections:
                            log.info("Finished elections: {}".format(finished_elections))
                            finished_election_map = {}
                            for finished_election in finished_elections:
                                elect_arr = finished_election_map.setdefault(finished_election.elector_addr, [])
                                elect_arr.append(finished_election)
                            for finish_elector_addr in finished_election_map:
                                try:
                                    log.info("Requesting bounty from: {}".format(finish_elector_addr))
                                    # no election happening
                                    recover_amounts = self._lite_client.compute_returned_stakes(finish_elector_addr, validator_addr)
                                    if recover_amounts:
                                        log.info("Recovering: {}".format(recover_amounts))
                                        recover_req = self._fift_cli.generate_recover_stake_req()
                                        transaction = self._tonos_cli.submitTransaction(validator_addr,
                                                                                        TonAddress.set_address_prefix(finish_elector_addr, TonAddress.Type.MASTER_CHAIN),
                                                                                        value=TonCoin.convert_to_nano_tokens(1),
                                                                                        payload=recover_req,
                                                                                        private_key=self._get_wallet_seed(),
                                                                                        bounce=True)
                                        log.info("Submitted transaction for funds recovery: {}".format(transaction))
                                        log.info("Removing unused keys")
                                        for felection in finished_election_map[finish_elector_addr]:
                                            self._cleanup_election(felection)
                                            self._active_elections.remove(felection)
                                        self._send_telemetry('stake_recover', {
                                            'elector_addr': finish_elector_addr,
                                            'recover_amount': sum(int(amount) for amount in recover_amounts)
                                        })
                                    else:
                                        log.info("Nothing to recover: {}".format(recover_amounts))
                                except Exception as ex:
                                    log.exception("Failed to request bounty: {}".format(ex))
                        self.save_active_elections()
            except Exception as ex:
                election_status_telemetry_data['error'] = str(ex)
                log.exception("Error in validator routine: {}".format(ex))
            self._send_telemetry('election_status', election_status_telemetry_data)
            log.info("Sleeping for: {}s, next check after {}".format(sleep_interval,
                                                                     datetime.datetime.now() + datetime.timedelta(seconds=sleep_interval)))
            time.sleep(sleep_interval)

