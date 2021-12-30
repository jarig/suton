import hashlib
import json
import logging
import os
from typing import List, Optional, Union, Dict

from pip._vendor import requests
from toncommon.contextmanager import secret_manager
from toncommon.core import TonExec
from toncommon.models.ElectionData import ElectionData, ElectionMember
from toncommon.models.TonAddress import TonAddress
from toncommon.models.TonCoin import TonCoin
from toncommon.models.depool.DePoolElectionEvent import DePoolElectionEvent
from toncommon.models.depool.DePoolEvent import DePoolEvent
from toncommon.models.depool.DePoolInfo import DePoolInfo
from toncommon.models.depool.DePoolLowBalanceEvent import DePoolLowBalanceEvent
from toncommon.models.TonAccount import TonAccount
from toncommon.models.TonTransaction import TonTransaction
from toncommon.utils import HexUtils
from toncommon.models.ElectionParams import ElectionValidatorParams, StakeParams, ElectionParams

log = logging.getLogger("tonoscli")


class TonosCli(TonExec):
    """
    Python wrapper for tonos CLI
    """
    CONFIG_NAME = "tonos-cli.conf.json"

    def __init__(self, cli_path, cwd, config_url, wallet_abi_url=None, wallet_tvc_url=None,
                 ton_endpoints=None):
        super().__init__(cli_path)
        with open(cli_path, "rb") as f:
            h = hashlib.md5(f.read())
            h.update(f"{config_url}.{ton_endpoints}".encode())
        self._cwd = os.path.join(cwd, h.hexdigest())
        self._config_url = config_url
        self._tvc_wallet_url = wallet_tvc_url
        self._wallet_abi_url = wallet_abi_url
        self._ton_endpoints = ton_endpoints

    def _run_command(self, command: str, options: list = None, retries=5):
        """
        ./tonos-cli <command> <options>
        """
        if not os.path.exists(os.path.join(self._cwd, TonosCli.CONFIG_NAME)):
            os.makedirs(self._cwd, exist_ok=True)
            for i in range(retries):
                ret, out = self._execute(["config", "--url", self._config_url],
                                         cwd=self._cwd)
                if self._ton_endpoints:
                    log.info(f"Configuring endpoints: {self._ton_endpoints}")
                    ret2, out2 = self._execute(["config", "endpoint", "add", self._config_url, self._ton_endpoints],
                                               cwd=self._cwd)
                    out = f"{out} {out2}"
                    ret = ret2 + ret
                if ret != 0:
                    if out and "timeout" in out.lower():
                        log.info("Retrying tonos command due to timeout")
                        continue
                    if not os.path.exists(os.path.join(self._cwd, TonosCli.CONFIG_NAME)):
                        raise Exception("Failed to initialize tonos-cli: {}".format(out))
                break
        if options is None:
            options = []
        args = [command] + options
        log.debug("Running: {} {}".format(self._exec_path, args))
        ret, out = self._execute(args, cwd=self._cwd)
        if ret != 0:
            raise Exception("Failed to run command {}: {}".format(command, out))
        return out

    def _materialize_abi(self, abi_url):
        log.info("Materialising ABI url: {}".format(abi_url))
        cached_path = "{}.json".format(os.path.join(self._cwd, hashlib.md5(abi_url.encode()).hexdigest()))
        if not os.path.exists(cached_path):
            log.info("Downloading ABI from: {}".format(abi_url))
            resp = requests.get(abi_url, allow_redirects=True)
            open(cached_path, 'wb').write(resp.content)
        return cached_path

    def _parse_result(self, output: str) -> (dict, None):
        if "Result" in output:
            result_keyword = 'Result: '
            substr = output[output.find(result_keyword) + len(result_keyword):]
            obj = json.loads(substr)
            return obj
        return None

    def get_config(self, index: int) -> (str, Optional[dict]):
        """ ex:
            Config p17: {
              "max_stake": "10000000000000000",
              "max_stake_factor": 196608,
              "min_stake": "10000000000000",
              "min_total_stake": "100000000000000"
            }
        """
        out = self._run_command('getconfig', [str(index)])
        config_pattern = f"Config p{index}:"
        payload = ""
        payload_started = False
        for line in out.splitlines():
            if line.startswith(config_pattern):
                payload_started = True
                line = line.replace(config_pattern, "").strip()
            if payload_started:
                payload += line
        if payload:
            return json.loads(payload)
        return None

    def get_stake_params(self) -> StakeParams:
        data = self.get_config(17)
        return StakeParams(data["min_stake"], data["max_stake"])

    def get_election_validator_params(self) -> (ElectionValidatorParams, None):
        data = self.get_config(16)
        if data and "max_validators" in data:
            return ElectionValidatorParams(max_validators=data["max_validators"],
                                           max_main_validators=data["max_main_validators"],
                                           min_validators=data["min_validators"])
        return None

    def get_elector_params(self) -> (ElectionParams, None):
        data = self.get_config(15)
        if data:
            return ElectionParams(validators_elected_for=data["validators_elected_for"],
                                  elections_start_before=data["elections_start_before"],
                                  elections_end_before=data["elections_end_before"],
                                  stake_held_for=data["stake_held_for"])
        return None

    def get_elector_address(self) -> Optional[str]:
        data = self.get_config(1)
        if data:
            return TonAddress.set_address_prefix(data.strip(), TonAddress.Type.MASTER_CHAIN)
        return None

    def compute_returned_stake(self, elector_addr: str, validator_wallet_addr: str, elector_abi_url: str):
        # run ${ELECTOR_ADDR} compute_returned_stake "{\"wallet_addr\":\"${MSIG_ADDR_HEX}\"}" --abi ${CONFIGS_DIR}/Elector.abi.json
        data = self.exec_command('run', elector_addr, 'compute_returned_stake',
                                 {"wallet_addr": validator_wallet_addr},
                                 abi_url=elector_abi_url)
        if data:
            return [HexUtils.hex_to_int(data.get("value0"))]
        return []

    def compute_returned_stake_fift(self, elector_addr: str, validator_wallet_addr: str):
        # runget ${ELECTOR_ADDR} compute_returned_stake "${MSIG_ADDR_HEX}" 2>&1
        data = self.exec_command_fift('runget', elector_addr, 'compute_returned_stake', validator_wallet_addr)
        if data:
            return [HexUtils.hex_to_int(data[0])]
        return []

    def get_active_election_ids(self, elector_addr: str, elector_abi_url: str) -> List[str]:
        # $(${UTILS_DIR}/tonos-cli run ${ELECTOR_ADDR} active_election_id {} --abi ${CONFIGS_DIR}/Elector.abi.json
        data = self.exec_command('run', elector_addr, 'active_election_id',
                                 {}, abi_url=elector_abi_url)
        if data:
            value = HexUtils.hex_to_int(data.get("value0"))
            if value:  # non-zero, non-empty value
                return [str(value)]
        return []

    def get_active_election_ids_fift(self, elector_addr: str) -> List[str]:
        # using fift
        data = self.exec_command_fift('runget', elector_addr, 'active_election_id')
        if data:
            value = HexUtils.hex_to_int(data[0])
            if value:  # non-zero, non-empty value
                return [str(value)]
        return []

    def get_election_data(self, elector_addr: str, elector_abi_url: str) -> Optional[ElectionData]:
        data = self.exec_command('run', elector_addr, 'get',
                                 {}, abi_url=elector_abi_url)
        if data:
            return ElectionData(election_open=data.get("election_open", False),
                                members=[ElectionMember(addr=m_data.get("addr"),
                                                        stake=m_data.get("stake", 0),
                                                        max_factor=m_data.get("max_factor", 3),
                                                        timestamp=m_data.get("time"))
                                         for m_hash, m_data in data.get("cur_elect", {}).get("members", {}).items()
                                         ])
        return None

    def get_participant_list_fift(self, elector_addr: str) -> Optional[ElectionData]:
        # tonos-cli runget -1:3333333333333333333333333333333333333333333333333333333333333333 participant_list
        data = self.exec_command_fift("runget", elector_addr, "participant_list")
        if data:
            # a bit weird output that 'runget' returns with nested arrays
            def collect(p, res):
                if p and p[0]:
                    res.append(p[0])
                    if len(p) > 1:
                        collect(p[1], res)
            stakes = []
            collect(data[0], stakes)
            return ElectionData(election_open=True,
                                members=[ElectionMember(addr=stake_data[0],
                                                        stake=int(stake_data[1]),
                                                        max_factor=3,
                                                        timestamp=0)
                                         for stake_data in stakes
                                         ])
        return None

    def get_account(self, address) -> TonAccount:
        out = self._run_command('account', [address])
        data = {}
        output_started = False
        for line in out.splitlines():
            if not output_started and "Succeeded." in line:
                output_started = True
                continue
            if output_started:
                if "Account not found" in line:
                    raise Exception("Account not found: {}".format(address))
                tokens = line.split(":")
                data[tokens[0].strip()] = tokens[1].strip()
        return TonAccount(acc_type=data["acc_type"], balance=int(data.get("balance", 0).replace("nanoton", "").strip()),
                          last_paid=int(data.get("last_paid")), data=data.get("data(boc)"))

    def _run_command_and_parse_result(self, command: str,
                                      options: List[str] = None, private_key: str = None) -> Optional[dict]:
        cmd_args = options.copy() if options else []
        with secret_manager(secrets=[private_key]):
            if private_key:
                cmd_args.extend(['--sign', str(private_key)])
            out = self._run_command(command, cmd_args)
            data = self._parse_result(out)
            log.debug("Tonoscli call: {}".format(out))
        return data

    def exec_command(self, command: str, address: str, method: str, payload: dict,
                     abi_url: str, private_key: str = None) -> Optional[dict]:
        cmd = [address, method, str(json.dumps(payload)), "--abi", self._materialize_abi(abi_url)]
        return self._run_command_and_parse_result(command, cmd, private_key=private_key)

    def exec_command_fift(self, command: str, address: str, method: str, payload: str = None,
                          private_key: str = None) -> Union[Optional[Dict], Optional[List]]:
        cmd = [address, method]
        if payload:
            cmd.append(str(payload))
        return self._run_command_and_parse_result(command, cmd, private_key=private_key)

    def generate_key_pair_file(self, file_location, phrase):
        with secret_manager(secrets=[phrase]):
            return self._run_command("getkeypair", [file_location, phrase])

    def submit_transaction(self, address, dest, value: int, payload, private_key, bounce=False, allBalance=False) -> TonTransaction:
        with secret_manager(secrets=[private_key]):
            transaction_payload = json.dumps({"dest": str(dest),
                                              "value": str(value),
                                              "bounce": bounce,
                                              "allBalance": allBalance,
                                              "payload": str(payload)})
            out = self._run_command('call', [address, "submitTransaction", str(transaction_payload),
                                    "--abi", self._materialize_abi(self._wallet_abi_url), "--sign", str(private_key)])
            data = self._parse_result(out)
            log.debug("Tonoscli: {}".format(out))
        return TonTransaction(tid=data.get("transId"))

    def confirm_transaction(self, address: str, transaction_id: str, private_keys: List[str]) -> TonTransaction:
        with secret_manager(secrets=private_keys):
            for key in private_keys:
                transaction_payload = json.dumps({"transactionId": transaction_id})
                out = self._run_command('call', [address, "confirmTransaction", transaction_payload,
                                        "--abi", self._materialize_abi(self._wallet_abi_url), "--sign", key])
                log.debug("Tonoscli: {}".format(out))
        return TonTransaction(tid=transaction_id)

    def depool_replenish(self, depool_addr: str, wallet_addr: str, value: TonCoin,
                         private_key: str, custodian_keys: List[str] = None) -> TonTransaction:
        with secret_manager(secrets=[private_key]):
            out = self._run_command('depool', ["--addr", depool_addr, "replenish", "--value", value.as_tokens(),
                                    "--wallet", wallet_addr, "--sign", str(private_key)])
            log.debug("Tonoscli: {}".format(out))
            data = self._parse_result(out)
            if data and custodian_keys:
                self.confirm_transaction(wallet_addr, transaction_id=data.get("transId"), private_keys=custodian_keys)
        return TonTransaction(tid=data.get("transId"))

    def get_depool_events(self, depool_addr,
                          max: int = 100) -> List[DePoolEvent]:
        out = self._run_command("depool", ["--addr", depool_addr, "events"])
        log.debug("Tonoscli: {}".format(out))
        events = []
        current_event_id = None
        current_event = None
        for line in out.splitlines():
            if not line or not line.strip():
                # empty line indicates that next event is coming
                current_event_id = None
                current_event = None
                continue
            if line.startswith("event "):
                current_event_id = line.split(" ")[1]
                continue

            if current_event_id and not current_event:
                # new event started, but we don't know yet which one
                event_name = line.split(" ")[0]
                event_cls = DePoolEvent
                if event_name == "TooLowDePoolBalance":
                    event_cls = DePoolLowBalanceEvent
                elif event_name == "StakeSigningRequested":
                    event_cls = DePoolElectionEvent
                current_event = event_cls(current_event_id, event_name)
                continue

            if current_event and line.startswith("{"):
                current_event.set_data(line)
                events.append(current_event)

            if len(events) >= max:
                break

        return events

    def terminate_depool(self, address, private_key: str, abi_url: str):
        with secret_manager(secrets=[private_key]):
            transaction_payload = json.dumps({})
            out = self._run_command('call', [address, "terminator", transaction_payload,
                                    "--abi", self._materialize_abi(abi_url), "--sign", str(private_key)])
            log.debug("Tonoscli: {}".format(out))

    def depool_ticktock(self, depool_address: str, wallet_address: str, private_key: str,
                        custodian_keys: List[str] = None):
        with secret_manager(secrets=[private_key]):
            out = self._run_command("depool", ["--addr", depool_address, "ticktock",
                                               "-w", wallet_address, "--sign", str(private_key)])
            log.debug("Tonoscli: {}".format(out))
            data = self._parse_result(out)
            if custodian_keys:
                self.confirm_transaction(wallet_address, transaction_id=data.get("transId"), private_keys=custodian_keys)

    def depool_info(self, depool_address: str, abi_url: str) -> DePoolInfo:
        # tonos-cli run 0:5e76094228c2cbc38b16e69507cfe7e0592b5ef67b1f3e3c11a0d3317f9532fa getDePoolInfo {} --abi pool_01.02.21/DePool.abi.json
        data = self.exec_command('run', depool_address, 'getDePoolInfo', {}, abi_url=abi_url)
        return DePoolInfo(pool_closed=data["poolClosed"],
                          proxies=data["proxies"],
                          validator_wallet=data["validatorWallet"],
                          participant_reward_fraction=data["participantRewardFraction"])

