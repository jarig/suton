import hashlib
import json
import logging
import os
from typing import List, Optional

from pip._vendor import requests
from toncommon.contextmanager import secret_manager
from toncommon.core import TonExec
from toncommon.models.TonCoin import TonCoin
from toncommon.models.depool.DePoolElectionEvent import DePoolElectionEvent
from toncommon.models.depool.DePoolEvent import DePoolEvent
from toncommon.models.depool.DePoolLowBalanceEvent import DePoolLowBalanceEvent
from toncommon.models.TonAccount import TonAccount
from toncommon.models.TonTransaction import TonTransaction

log = logging.getLogger("tonoscli")


class TonosCli(TonExec):
    """
    Python wrapper for tonos CLI
    """
    CONFIG_NAME = "tonos-cli.conf.json"

    def __init__(self, cli_path, cwd, config_url, abi_path=None, tvc_path=None):
        super().__init__(cli_path)
        with open(cli_path, "rb") as f:
            h = hashlib.md5(f.read())
            h.update(config_url.encode())
        self._cwd = os.path.join(cwd, h.hexdigest())
        self._config_url = config_url
        self._abi_path = abi_path
        self._tvc_path = tvc_path

    def _run_command(self, command: str, options: list = None, retries=5):
        """
        ./tonos-cli <command> <options>
        """
        if not os.path.exists(os.path.join(self._cwd, TonosCli.CONFIG_NAME)):
            os.makedirs(self._cwd, exist_ok=True)
            for i in range(retries):
                ret, out = self._execute(["config", "--url", self._config_url],
                                         cwd=self._cwd)
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

    def call_command(self, address: str, command: str, payload: dict,
                     abi_url: str, private_key: str = None) -> Optional[dict]:
        cmd = [address, command, str(json.dumps(payload)), "--abi", self._materialize_abi(abi_url)]
        with secret_manager(secrets=[private_key]):
            if private_key:
                cmd.extend(['--sign', str(private_key)])
            out = self._run_command('call', cmd)
            data = self._parse_result(out)
            log.debug("Tonoscli call: {}".format(out))
        return data

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
                                    "--abi", self._abi_path, "--sign", str(private_key)])
            data = self._parse_result(out)
            log.debug("Tonoscli: {}".format(out))
        return TonTransaction(tid=data.get("transId"))

    def confirm_transaction(self, address: str, transaction_id: str, private_keys: List[str]) -> TonTransaction:
        with secret_manager(secrets=private_keys):
            for key in private_keys:
                transaction_payload = json.dumps({"transactionId": transaction_id})
                out = self._run_command('call', [address, "confirmTransaction", transaction_payload,
                                        "--abi", self._abi_path, "--sign", key])
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

    def terminate_depool(self, address, private_key: str):
        with secret_manager(secrets=[private_key]):
            transaction_payload = json.dumps({})
            out = self._run_command('call', [address, "terminator", transaction_payload,
                                    "--abi", self._abi_path, "--sign", str(private_key)])
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

