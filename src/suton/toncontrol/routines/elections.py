import datetime
import json
import logging
import os
import threading
import time
from typing import List, Optional, Tuple

from exceptions.depool import LowDePoolBalanceException
from routines.election_providers.core import ElectionProvider
from routines.models.elections import Election
from routines.validator_providers.core import Validator
from secrets.interfaces.secretmanager import SecretManagerAbstract
from settings.elections import ElectionSettings, ElectionMode
from settings.depool_settings.prudent_elections import PrudentElectionSettings
from toncommon.models.depool.DePoolElectionEvent import DePoolElectionEvent
from toncommon.models.depool.DePoolLowBalanceEvent import DePoolLowBalanceEvent
from toncommon.models.TonAddress import TonAddress
from toncommon.models.TonCoin import TonCoin
from tonoscli.core import TonosCli
from tonvalidator.exceptions.connection import TonConnectionException
from toncommon.models.ElectionParams import StakeParams, ElectionParams

from logstash.client import LogStashClient

log = logging.getLogger("elections")


class ElectionsRoutine(object):

    def __init__(self,
                 work_dir: str,
                 tonos_cli: TonosCli,
                 secret_manager: SecretManagerAbstract,
                 election_provider: ElectionProvider,  # DePool or Direct
                 validator_provider: Validator,  # CPP or Rust Implementation
                 max_sync_diff=50,
                 min_balance: int = 0,
                 election_settings: ElectionSettings = None):
        self._work_dir = work_dir
        self._election_provider = election_provider
        self._validator_provider = validator_provider
        self._tonos_cli = tonos_cli
        self._secret_manager = secret_manager
        self._max_sync_diff = max_sync_diff
        self._min_balance = min_balance
        self._stake_to_make = election_settings.TON_CONTROL_DEFAULT_STAKE
        self._stake_max_factor = election_settings.TON_CONTROL_STAKE_MAX_FACTOR
        self._enabled = True
        self._active_elections: List[Election] = []
        self._active_election_file = os.path.join(self._work_dir, "active_elections.json")
        self._check_node_sync_interval_seconds = 2 * 60
        self._check_elections_interval_seconds = 15 * 60
        self._election_settings = election_settings
        self._election_mode = election_settings.TON_CONTROL_ELECTION_MODE

    def load_active_elections(self):
        if os.path.exists(self._active_election_file):
            with open(self._active_election_file) as f:
                election_data = json.load(f)
            for election in election_data['elections']:
                self._active_elections.append(Election.from_json(election))
        return self._active_elections

    def save_active_elections(self):
        json_data = json.dumps({
            'elections': [election.to_json() for election in self._active_elections]
        }, indent=2)
        with open(self._active_election_file, "w") as f:
            f.write(json_data)

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

    def _get_active_election_by_id(self, eid) -> Optional[Election]:
        for election in self._active_elections:
            if str(election.election_id) == str(eid):
                return election
        return None

    def _cleanup_election(self, election: Election):
        if election.key and election.adnl_key:
            self._validator_provider.delete_temp_key(election.key, election.adnl_key)
        if election.key:
            self._validator_provider.delete_key(election.key)
        if election in self._active_elections:
            self._active_elections.remove(election)

    def _get_wallet_seed(self):
        return self._secret_manager.get_validator_seed()

    def _get_wallet_address(self):
        return self._secret_manager.get_validator_address()

    def _check_if_synced(self):
        try:
            time_diff = self._validator_provider.get_sync_time_diff()
            if time_diff is None:
                log.error("Time diff is not available yet, node still initializing...")
                return False
            log.debug(f"Time diff: {time_diff}, max allowed {self._max_sync_diff}")
            self._send_telemetry('node_status', {'time_diff': time_diff,
                                                 'max_sync_diff': self._max_sync_diff})
            if time_diff <= self._max_sync_diff:
                return True
        except TonConnectionException as ex:
            log.exception("Failed to connect to TON Validator: {}".format(ex))
        except Exception as ex:
            log.exception("Failed to get time-diff stats: {}".format(ex))
        return False

    def _send_telemetry(self, data_type, data: dict):
        data['timestamp'] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        data['data_type'] = data_type
        LogStashClient.get_client().send_data('elections', data)

    def _join_elections_validator_mode(self, validator_addr: str, election: Election,
                                       elector_addr: str, election_stake: int, stake_params: StakeParams,
                                       elector_params: ElectionParams) -> bool:
        """
        Join elections on behalf of validator wallet
        :param election:
        :param election_stake:
        :param stake_params:
        :param elector_params:
        :return:
        """
        election.election_mode = ElectionMode.VALIDATOR
        election_telemetry = {
            'election_id': election.election_id,
            'election_mode': str(ElectionMode.VALIDATOR)
        }
        try:
            log.info("Joining election: {} with stake {}".format(election.election_id,
                                                                 election_stake))
            if stake_params:
                log.info("Got stake params")
                election_telemetry['min_stake'] = stake_params.min_stake
                election_telemetry['max_stake'] = stake_params.max_stake
                if election_stake < stake_params.min_stake:
                    log.warning(
                        "Can't participate in this election as stake is less than minimal: {} < {}".format(
                            election_stake,
                            stake_params.min_stake))
                    return False
                if election_stake > stake_params.max_stake:
                    log.info("Reducing stake to {}".format(stake_params.max_stake))
                    # we staked more than allowed, so reduce
                    election_stake = stake_params.max_stake
            election_telemetry['election_id'] = election.election_id
            election_telemetry['election_stake'] = election_stake
            election.election_stake += election_stake
            try:
                self._sign_and_join_elections(validator_addr, election=election,
                                              elector_params=elector_params,
                                              beneficiary_masterchain_adr=validator_addr,
                                              elector_adr=elector_addr)
                if not self._get_active_election_by_id(election.election_id):
                    self._active_elections.append(election)
                election_telemetry['elected'] = True
                return True
            except Exception as ex:
                election_telemetry['error'] = str(ex)
                self._cleanup_election(election)
                raise
        finally:
            self._send_telemetry('election_join', election_telemetry)

    def _join_elections_depool_mode(self, depool_addr: str, validator_addr: str, proxy_addr: str,
                                    election: Election,
                                    election_stake: int, elector_params: ElectionParams):
        election_telemetry = {
            'election_id': election.election_id,
            'election_mode': str(ElectionMode.DEPOOL),
            'depool_addr': depool_addr,
            'proxy_addr': proxy_addr
        }
        try:
            election.election_mode = ElectionMode.DEPOOL
            election.depool_addr = depool_addr
            election.proxy_addr = proxy_addr
            self._sign_and_join_elections(validator_addr, election=election,
                                          elector_params=elector_params,
                                          beneficiary_masterchain_adr=proxy_addr, elector_adr=depool_addr)
            election_telemetry['elected'] = True
            election.election_stake += election_stake
            if not self._get_active_election_by_id(election.election_id):
                self._active_elections.append(election)
        except Exception as ex:
            election_telemetry['error'] = str(ex)
            self._cleanup_election(election)
            raise
        self._send_telemetry('election_join', election_telemetry)

    def _sign_and_join_elections(self, validator_addr: str, election: Election,
                                 elector_params: ElectionParams, beneficiary_masterchain_adr: str,
                                 elector_adr: str) -> Election:
        """
        :param validator_addr: Beneficiary address of validator
        :param election: Object describing election details
        :param elector_params: Object with elector parameters
        :param beneficiary_masterchain_adr: Address where rewards will land in masterchain (elector will pay here).
            In case of DePool it's proxy, in case of direct participation it's validator wallet.
        :param elector_adr:
            Address of contract that will perform election handling or comms (either DePool or Elector itself)
        :return:
        """
        need_election_prepare = False
        if not election.key:
            log.info("Generating keys...")
            need_election_prepare = True
            election.key = self._validator_provider.get_new_key()
            election.adnl_key = self._validator_provider.get_new_key()
        else:
            log.info("Using existing/provided keys for the election")
        log.info("Perm key hash: {}".format(election.key))
        log.info("ADNL key hash: {}".format(election.adnl_key))
        election_stop_time = int(election.election_id) + \
            1000 + elector_params.elections_start_before + \
            elector_params.validators_elected_for + \
            elector_params.elections_end_before + \
            elector_params.stake_held_for
        if need_election_prepare:
            log.info("Preparing election request...")
            self._validator_provider.prepare_election(election.key, election.adnl_key,
                                                      election_start=election.election_id,
                                                      election_stop=election_stop_time)

        log.info("Generating validation request...")
        election_req = self._validator_provider.generate_validation_request(beneficiary_masterchain_adr=beneficiary_masterchain_adr,
                                                                            election_id=election.election_id,
                                                                            adnl_key=election.adnl_key,
                                                                            max_factor=self._stake_max_factor)
        # sign request
        log.info("Signing election request...")
        election_req_signature, pub_key = self._validator_provider.sign_request(election.key, election_req)
        log.info("Generating signed election request...")
        election_signed = self._validator_provider.generate_validation_signed(beneficiary_masterchain_adr,
                                                                              election.election_id, election.adnl_key,
                                                                              public_key=pub_key,
                                                                              signature=election_req_signature,
                                                                              max_factor=self._stake_max_factor)

        log.info("Submitting election transaction...")
        transaction = self._tonos_cli.submit_transaction(validator_addr,
                                                         dest=elector_adr,
                                                         value=TonCoin.convert_to_nano_tokens(1),
                                                         payload=election_signed,
                                                         private_key=self._secret_manager.get_validator_seed(),
                                                         bounce=True)
        log.info("Election transaction submitted: {}".format(transaction))
        custodian_seeds = self._secret_manager.get_custodian_seeds()
        if custodian_seeds:
            log.info("Confirming transaction by custodians")
            self._tonos_cli.confirm_transaction(validator_addr, transaction.tid, custodian_seeds)
            log.info("Confirmed.")
        log.info("Transaction id: {}, election: {}".format(transaction.tid, election.election_id))
        return election

    def _satisfies_prudent_settings(self, election: Election, prudent_settings: PrudentElectionSettings,
                                    election_stake: int, max_validators: int,
                                    stakes: List[int], telemetry_holder: dict) -> bool:
        if not stakes:
            log.info("No stake information present for prudent settings")
            return True
        log.info(f"Checking prudent elections settings: {prudent_settings}")
        offset = prudent_settings.election_end_join_offset
        e_finish_in = election.get_election_finishes_in()
        lower_than_mine = [s for s in stakes if s < election_stake]
        # 100 - everyone are lower, 0 - everyone are higher than us
        perc_stakes_lower = (len(lower_than_mine) / len(stakes)) * 100
        telemetry_holder["join_threshold"] = perc_stakes_lower
        log.debug(f"Stakes lower than mine {perc_stakes_lower}%, stake {election_stake}, max validators {max_validators}")
        if offset and offset < election.get_election_finishes_in():
            log.warning(f"Not joining, as too early based on prudent settings: offset {offset}s, "
                        f"but until election finish {e_finish_in}s")
            return False
        if max_validators > len(stakes):
            # there are free slots still available
            return True
        if perc_stakes_lower < prudent_settings.join_threshold:
            log.warning(f"Not joining as not satisfying prudent election join threshold: {perc_stakes_lower}. Stake given {election_stake}.")
            return False
        return True

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
                    if self._enabled:
                        log.info("Checking for new elections, mode: {}".format(self._election_mode))
                        validator_addr = self._secret_manager.get_validator_address()
                        validator_account = self._tonos_cli.get_account(validator_addr)
                        validator_balance = validator_account.balance
                        log.info("Validator balance: {}".format(validator_balance))
                        # get address of elector contract
                        elector_addr = self._validator_provider.get_elector_address()
                        election_ids = self._validator_provider.get_election_ids(elector_addr)
                        log.info("Elector address: {}".format(elector_addr))
                        log.info("Election ids: {}".format(election_ids))
                        election_status_telemetry_data = {'validator_address': validator_addr,
                                                          'balance': validator_balance,
                                                          'election_ids': election_ids}
                        # cleanup current active elections
                        finished_elections = []
                        active_election_stakes = 0
                        recovered_stake = 0
                        for active_election in self._active_elections:
                            telemetry_data = {
                                'election_id': active_election.election_id,
                                'election_stake': active_election.election_stake,
                                'election_state': active_election.get_state(),
                                'participating': False
                            }
                            active_election_stakes += active_election.election_stake
                            if str(active_election.election_id) not in election_ids and active_election.can_return():
                                finished_elections.append(active_election)
                                self._send_telemetry('finished_elections', telemetry_data)
                            else:
                                log.info("Participating election: {}".format(active_election))
                                telemetry_data["participating"] = True
                            self._send_telemetry('active_elections', telemetry_data)
                        if finished_elections:
                            log.info("Finished elections: {}".format(finished_elections))
                            finished_validator_elections = []
                            for finished_election in finished_elections:
                                if finished_election.election_mode == ElectionMode.DEPOOL:
                                    log.info(f"Cleaning up election {finished_election}")
                                    self._cleanup_election(finished_election)
                                elif finished_election.election_mode == ElectionMode.VALIDATOR:
                                    finished_validator_elections.append(finished_election)
                            recovered_stake = self._recover_stakes(validator_addr, finished_validator_elections)
                            log.info("Recovered total stake: {}".format(recovered_stake))
                        if not election_ids:
                            log.info(
                                "No elections happening at a moment (mode: {}, ids: {}).".format(self._election_mode,
                                                                                                 election_ids))
                        else:
                            log.info("Getting elector params...")
                            elector_params = self._validator_provider.get_elector_params()
                            log.info("Current active elections: {}".format(election_ids))
                            new_elections = []  # type: List[Election]
                            for eid in election_ids:
                                active_election = self._get_active_election_by_id(eid)
                                if not active_election:
                                    new_elections.append(Election(election_id=eid,
                                                                  elector_addr=elector_addr,
                                                                  election_params=elector_params))
                                elif active_election.restake:
                                    log.info("Will re-stake for {}".format(active_election))
                                    # reset restake flag
                                    active_election.restake = False
                                    new_elections.append(active_election)

                            participant_stakes = self._validator_provider.get_current_participant_stakes(elector_addr)
                            participant_number = len(participant_stakes)
                            lowest_stake = min(participant_stakes) if participant_stakes else 0
                            election_validator_params = self._validator_provider.get_election_validator_params()
                            max_validators = election_validator_params.max_validators
                            valid_stakes = sorted(participant_stakes, reverse=True)[:max_validators]
                            lowest_valid_stake = min(valid_stakes) if valid_stakes else 0
                            election_status_telemetry_data["lowest_valid_stake"] = lowest_valid_stake
                            election_status_telemetry_data["participants"] = participant_number
                            election_status_telemetry_data["lowest_stake"] = lowest_stake
                            election_status_telemetry_data["max_validators"] = election_validator_params.max_validators
                            log.info(f"Participants {participant_number}, lowest stake {lowest_stake}, "
                                     f"lowest valid {lowest_valid_stake}, max validators {election_validator_params.max_validators}.")
                            if not new_elections:
                                log.info("No new elections found, already participating in all of the existing ones.")
                            else:
                                # there are some elections in which we want to participate
                                log.info(f"Going to join these elections: {new_elections}, "
                                         f"participant num: {participant_number}, min stake: {lowest_stake}")
                                #
                                if self._election_mode == ElectionMode.VALIDATOR:
                                    log.info("Joining in validator mode")
                                    log.info("Getting min stake...")
                                    stake_params = self._validator_provider.get_stake_params()
                                    stake_per_election = (validator_balance + recovered_stake + active_election_stakes) / len(new_elections)
                                    balance_left = validator_balance
                                    election_stake = self._compute_stake(stake_per_election)
                                    election_status_telemetry_data["election_stake"] = election_stake
                                    for election in new_elections:
                                        if self._election_settings.PRUDENT_ELECTION_SETTINGS and \
                                                not self._satisfies_prudent_settings(election=election,
                                                                                     prudent_settings=self._election_settings.PRUDENT_ELECTION_SETTINGS,
                                                                                     election_stake=election_stake,
                                                                                     max_validators=max_validators,
                                                                                     stakes=valid_stakes,
                                                                                     telemetry_holder=election_status_telemetry_data):
                                            log.warning("Prudent settings not satisfied, not joining.")
                                            continue
                                        if (balance_left - election_stake) < self._min_balance:
                                            election_status_telemetry_data['error'] = 'Not enough balance'
                                            log.warning(
                                                "Skipping participation in {}, as otherwise will go below minimum specified balance ({}). Consider lowering stake.".format(
                                                    election.election_id,
                                                    self._min_balance))
                                            break
                                        if self._join_elections_validator_mode(validator_addr=validator_addr,
                                                                               election=election,
                                                                               elector_addr=elector_addr,
                                                                               election_stake=election_stake,
                                                                               stake_params=stake_params,
                                                                               elector_params=elector_params):
                                            balance_left -= election_stake
                                elif self._election_mode == ElectionMode.DEPOOL:
                                    log.info("Joining in depool mode")
                                    depool_list = self._election_settings.DEPOOL_LIST
                                    for depool_data in depool_list:
                                        log.info(f"Participation enabled: {depool_data.enable_elections}")
                                        send_tick_tock = False
                                        depool_healthy = True
                                        log.info("DePool: {}".format(depool_data.depool_address))
                                        if not depool_data.proxy_addresses:
                                            log.info("Proxy addresses not specified, trying to fetch them")
                                            depool_info = self._tonos_cli.depool_info(depool_data.depool_address,
                                                                                      depool_data.abi_url)
                                            depool_data.proxy_addresses = depool_info.proxies
                                        proxy_addresses = depool_data.proxy_addresses
                                        depool_addr = depool_data.depool_address
                                        log.info("Proxy addresses: {}, for: {}".format(proxy_addresses, depool_addr))
                                        depool_events = self._tonos_cli.get_depool_events(depool_addr)
                                        # check healtheness of depool
                                        if depool_events:
                                            last_event = depool_events[0]
                                            election_status_telemetry_data['depool_event'] = str(last_event)
                                            # raise error if events signaling that DePool is malfunctioning
                                            if isinstance(last_event, DePoolLowBalanceEvent):
                                                if depool_data.replenish_settings:
                                                    if time.time() - depool_data.replenish_settings.get_last_replenishment_time() >= depool_data.replenish_settings.max_period:
                                                        depool_data.replenish_settings.set_last_replenishment_time(time.time())
                                                        log.info(f"Automatically replenishing depool with {depool_data.replenish_settings.topup_sum}")
                                                        election_status_telemetry_data["depool_replenish"] = depool_data.replenish_settings.topup_sum.as_tokens()
                                                        self._tonos_cli.depool_replenish(depool_addr=depool_addr,
                                                                                         wallet_addr=validator_addr,
                                                                                         value=depool_data.replenish_settings.topup_sum,
                                                                                         private_key=self._secret_manager.get_validator_seed(),
                                                                                         custodian_keys=self._secret_manager.get_custodian_seeds())
                                                        send_tick_tock = True
                                                depool_healthy = False
                                                election_status_telemetry_data['error'] = str(LowDePoolBalanceException("DePool Balance is low to operate",
                                                                                                                        balance=last_event.balance))

                                        if depool_healthy and depool_data.enable_elections:
                                            election_events = [event for event in depool_events if
                                                               isinstance(event, DePoolElectionEvent)]

                                            elections_to_join = []  # type: List[Tuple[DePoolElectionEvent, Election]]
                                            if election_events:
                                                log.debug("Found election events: {}".format(election_events))
                                                # select ongoing elections that matching our events
                                                for election in new_elections:
                                                    for event in election_events:
                                                        if str(election.election_id) == str(event.election_id):
                                                            elections_to_join.append((event, election))
                                                            break
                                            if not elections_to_join:
                                                log.info(
                                                    "No relevant signing events in depool contract at a moment: {}".format(
                                                        depool_data))
                                                send_tick_tock = True
                                            # Join elections
                                            for event, election in elections_to_join:
                                                log.info("Joining via proxy: {}".format(event.proxy))
                                                depool_account = self._tonos_cli.get_account(depool_addr)
                                                stake = depool_account.balance if len(self._active_elections) else depool_account.balance // 2
                                                election_status_telemetry_data["election_stake"] = stake
                                                if depool_data.prudent_election_settings and \
                                                        not self._satisfies_prudent_settings(election=election,
                                                                                             prudent_settings=depool_data.prudent_election_settings,
                                                                                             election_stake=stake,
                                                                                             max_validators=max_validators,
                                                                                             stakes=valid_stakes,
                                                                                             telemetry_holder=election_status_telemetry_data):
                                                    log.warning("Prudent settings not satisfied, not joining.")
                                                    continue
                                                log.info("Joining via proxy: {} to: {}".format(event.proxy,
                                                                                               election))
                                                self._join_elections_depool_mode(depool_addr=depool_addr,
                                                                                 validator_addr=validator_addr,
                                                                                 election=election,
                                                                                 proxy_addr=event.proxy,
                                                                                 election_stake=stake,
                                                                                 elector_params=elector_params)

                                        if send_tick_tock:
                                            # send tick-tock
                                            if time.time() - depool_data.get_last_ticktock() >= depool_data.max_ticktock_period:
                                                log.info("Sending ticktock event")
                                                self._tonos_cli.depool_ticktock(depool_data.depool_address,
                                                                                wallet_address=validator_addr,
                                                                                private_key=self._secret_manager.get_validator_seed(),
                                                                                custodian_keys=self._secret_manager.get_custodian_seeds())
                                                depool_data.set_last_ticktock(time.time())
                                                log.info("Ticktock sent at {}".format(depool_data.get_last_ticktock()))


                                else:
                                    log.info("Skipping validations due to set election mode: {}".format(self._election_mode))
                        self.save_active_elections()
            except Exception as ex:
                election_status_telemetry_data['error'] = str(ex)
                log.exception("Error in validator routine: {}".format(ex))
            self._send_telemetry('election_status', election_status_telemetry_data)
            log.info("Sleeping for: {}s, next check after {}".format(sleep_interval,
                                                                     datetime.datetime.now() + datetime.timedelta(seconds=sleep_interval)))
            time.sleep(sleep_interval)

    def _recover_stakes(self, validator_addr: str, finished_elections: List[Election]) -> int:
        """
        Check if possible to retrieve some stakes back from given list of elections
        :param validator_addr: Validator(node) address
        :param finished_elections: List of finished elections
        :return:
        """
        recovered_stake = 0
        finished_election_map = {}
        for finished_election in finished_elections:
            elect_arr = finished_election_map.setdefault(finished_election.elector_addr, [])
            elect_arr.append(finished_election)
        for finish_elector_addr in finished_election_map:
            try:
                log.info("Requesting bounty from: {}".format(finish_elector_addr))
                # no election happening
                recover_amounts = self._validator_provider.compute_returned_stakes(finish_elector_addr, validator_addr)
                if recover_amounts:
                    log.info("Recovering: {}".format(recover_amounts))
                    recover_req = self._validator_provider.generate_recover_stake_req()
                    transaction = self._tonos_cli.submit_transaction(validator_addr,
                                                                     TonAddress.set_address_prefix(finish_elector_addr,
                                                                                                   TonAddress.Type.MASTER_CHAIN),
                                                                     value=TonCoin.convert_to_nano_tokens(1),
                                                                     payload=recover_req,
                                                                     private_key=self._get_wallet_seed(),
                                                                     bounce=True)
                    log.info("Submitted transaction for funds recovery: {}".format(transaction))
                    log.info("Removing unused keys")
                    for felection in finished_election_map[finish_elector_addr]:
                        self._cleanup_election(felection)
                    recover_sum = sum(int(amount) for amount in recover_amounts)
                    self._send_telemetry('stake_recover', {
                        'elector_addr': finish_elector_addr,
                        'recover_amount': recover_sum
                    })
                    recovered_stake += recover_sum
                else:
                    log.info("Nothing to recover: {}".format(recover_amounts))
            except Exception as ex:
                log.exception("Failed to request bounty: {}".format(ex))
        return recovered_stake
