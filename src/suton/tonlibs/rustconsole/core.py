import base64
import hashlib
import json
import logging
import os
import re
import socket
from typing import Optional

from toncommon.core import TonExec


log = logging.getLogger("rcontrol")


class RustConsole(TonExec):
    DUMMY_WALLET_ADDR = "0:0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self, cli_path: str, cwd: str, server_addr: str,
                 server_pub_key_path: str, client_private_key_path: str):
        super().__init__(cli_path)
        self._cwd = cwd
        self._server_addr = server_addr
        self._server_pub_key_path = server_pub_key_path
        self._client_private_key_path = client_private_key_path
        self._key_cache = {}

    def _read_key(self, path):
        mtime = os.stat(path).st_mtime
        if path not in self._key_cache or self._key_cache[path][1] != mtime:
            log.info(f"Reading key from {path}")
            with open(path) as f:
                self._key_cache[path] = (f.read().strip(), mtime)
        return self._key_cache[path][0]

    def _get_exec_config(self, wallet_addr: str = DUMMY_WALLET_ADDR, max_factor: float = 2.7):
        server_pub_key = self._read_key(self._server_pub_key_path)
        client_priv_key = self._read_key(self._client_private_key_path)
        config_key = f'{wallet_addr}.{server_pub_key}.{client_priv_key}.{self._server_addr}'
        config_path = os.path.join(self._cwd, f"conf_{hashlib.md5(config_key.encode()).hexdigest()}")
        if not os.path.exists(self._cwd):
            os.makedirs(self._cwd, exist_ok=True)
        if not os.path.exists(config_path) or not os.path.getsize(config_path):
            # creat config file if not exist yet
            with open(config_path, "w") as cf:
                cf.write(json.dumps({
                    "config": {
                        # control not supporting hostnames :\
                        "server_address": f"{socket.gethostbyname(self._server_addr.split(':')[0])}:{':'.join(self._server_addr.split(':')[1:])}",
                        "server_key": {
                            "type_id": 1209251014,
                            "pub_key": server_pub_key
                        },
                        "client_key": {
                            "type_id": 1209251014,
                            "pvt_key": client_priv_key
                        }
                    },
                    "wallet_id": wallet_addr,
                    "max_factor": float(max_factor)
                }, indent=2))
        return config_path

    def _run_command(self, command: str, options: list = None,
                     wallet_addr: Optional[str] = DUMMY_WALLET_ADDR, max_factor: float = 2.7):
        """
        console -C config.json -c "commamd with parameters" -c "another command" -t timeout
        """
        if options is None:
            options = []
        args = ["-C", self._get_exec_config(wallet_addr, max_factor=max_factor), "-c", command] + options
        log.debug("Running: {} {}".format(self._exec_path, args))
        ret, out = self._execute(args, cwd=self._cwd)
        if ret != 0:
            raise Exception("Failed to run command {}: {}".format(command, out))
        return out

    def get_stats(self) -> dict:
        """ Ex
        GIT_BRANCH: master
        {
            "masterchainblocktime": 1613118553,
            "masterchainblocknumber":       299,
            "timediff":     54033,
            "in_current_vset_p34":  false,
            "in_next_vset_p36":     false
        }
        """
        # getstats
        broken_line_regex = re.compile(r'^\s*"(?P<key>.+)":\s+,?$')
        data = self._run_command(command=f"getstats")
        payload = ""
        payload_started = False
        for line in data.splitlines():
            if line.startswith("{"):
                payload_started = True
            if payload_started:
                if broken_line_regex.match(line):
                    m = broken_line_regex.match(line)
                    key = m.group("key")
                    line = f'"{key}": null {"," if line.endswith(",") else ""}'
                payload += line
        return json.loads(payload)

    def get_sync_time_diff(self) -> int:
        data = self.get_stats()
        return data.get("timediff")

    def recover_stake_request(self):
        self._run_command(command=f"recover_stake", wallet_addr=None)
        with open(os.path.join(self._cwd, "recover-query.boc"), "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return data

    def get_signed_election_req(self, beneficiary_masterchain_adr,
                                election_start, election_stop, max_factor: float = 2.7):
        self._run_command(command=f"election-bid {election_start} {election_stop}",
                          wallet_addr=beneficiary_masterchain_adr,
                          max_factor=max_factor)
        with open(os.path.join(self._cwd, "validator-query.boc"), "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return data
