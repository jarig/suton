import hashlib
import json
import logging
import os

from toncommon.contextmanager import secret_manager
from toncommon.core import TonExec
from toncommon.models.TonAccount import TonAccount
from toncommon.models.TonCoin import TonCoin
from toncommon.models.TonTransaction import TonTransaction

log = logging.getLogger("tonoscli")


class TonosCli(TonExec):
    """
    Python wrapper for tonos CLI
    """
    CONFIG_NAME = "tonlabs-cli.conf.json"

    def __init__(self, cli_path, cwd, config_url, abi_path=None, tvc_path=None):
        super().__init__(cli_path)
        self._cwd = os.path.join(cwd, hashlib.md5(config_url.encode()).hexdigest())
        self._config_url = config_url
        self._abi_path = abi_path
        self._tvc_path = tvc_path

    def _run_command(self, command: str, options: list = None):
        """
        ./tonos-cli <command> <options>
        """
        if not os.path.exists(os.path.join(self._cwd, TonosCli.CONFIG_NAME)):
            os.makedirs(self._cwd, exist_ok=True)
            ret, out = self._execute(["config", "--url", self._config_url],
                                     cwd=self._cwd)
            if ret != 0 or not os.path.exists(os.path.join(self._cwd, TonosCli.CONFIG_NAME)):
                raise Exception("Failed to initialize tonos-cli: {}".format(out))
        if options is None:
            options = []
        args = [command] + options
        log.debug("Running: {} {}".format(self._exec_path, args))
        ret, out = self._execute(args, cwd=self._cwd)
        if ret != 0:
            raise Exception("Failed to run command {}: {}".format(command, out))
        return out

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
        return TonAccount(acc_type=data["acc_type"], balance=int(data.get("balance", 0)),
                          last_paid=int(data.get("last_paid")), data=data.get("data(boc)"))

    def generate_key_pair_file(self, file_location, phrase):
        with secret_manager(secrets=[phrase]):
            return self._run_command("getkeypair", [file_location, phrase])

    def submitTransaction(self, address, dest, value: TonCoin, payload, private_key, bounce=False, allBalance=False) -> TonTransaction:
        with secret_manager(secrets=[private_key]):
            transaction_payload = json.dumps({"dest": dest,
                                              "value": value.as_nano_tokens(),
                                              "bounce": bounce,
                                              "allBalance": allBalance,
                                              "payload": payload})
            out = self._run_command('call', [address, "submitTransaction", transaction_payload,
                                    "--abi", self._abi_path, "--sign", private_key])
            data = self._parse_result(out)
            log.debug("Tonoscli: {}".format(out))
            return TonTransaction(tid=data.get("transId"))

    def confirmTransaction(self, address, transaction_id, private_key) -> TonTransaction:
        with secret_manager(secrets=[private_key]):
            transaction_payload = json.dumps({"transactionId": transaction_id})
            out = self._run_command('call', [address, "confirmTransaction", transaction_payload,
                                    "--abi", self._abi_path, "--sign", private_key])
            log.debug("Tonoscli: {}".format(out))
            return TonTransaction(out)
