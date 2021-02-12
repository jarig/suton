import json
import logging
import re
from typing import List, Dict, Optional

from toncommon.core import TonExec
from toncommon.models.TonAddress import TonAddress
from tonliteclient.exceptions.base import TonLiteClientException
from toncommon.models.ElectionParams import ElectionParams, StakeParams, ElectionValidatorParams

log = logging.getLogger("tonclient")


class TonLiteClient(TonExec):
    """
    Python wrapper for ton-client CLI
    """
    
    def __init__(self, client_path, server_addr, client_pub_key):
        super().__init__(client_path)
        self._server_addr = server_addr
        self._client_pub_key = client_pub_key

    def _run_command(self, command, timeout=60):
        """Ex:
        ./lite-client \
        -p "${KEYS_DIR}/liteserver.pub" \
        -a 127.0.0.1:3031 \
        -rc "getconfig 1" -rc "quit"
        """
        args = ['-a', self._server_addr,
                '-p', self._client_pub_key,
                '-rc', command, '-rc', 'quit', '-v0']
        log.debug("Running: {} {}".format(self._exec_path, args))
        ret, out = self._execute(args, timeout=timeout)
        if ret != 0:
            raise TonLiteClientException("Failed to run command {}: {}".format(command, out))
        return out

    def _parse_config_tokens(self, data: str) -> Dict[str, str]:
        tokens = re.split(r"\t|\s", data)
        data = {}
        for token in tokens:
            if token.strip():
                name_val = token.split(":")
                data[name_val[0].strip()] = name_val[1].strip()
        return data

    def get_elector_address(self) -> Optional[str]:
        out = self._run_command("getconfig 1", timeout=10)
        # get address from the output
        pattern = re.compile(r".+elector_addr:x(.+)\)$")
        for line in out.splitlines():
            m = pattern.match(line)
            if m:
                return TonAddress.set_address_prefix(m.group(1).strip(), TonAddress.Type.MASTER_CHAIN)
        return None

    def get_election_validator_params(self) -> (ElectionValidatorParams, None):
        # ConfigParam(16) = ( max_validators:1000 max_main_validators:100 min_validators:13)
        out = self._run_command("getconfig 16", timeout=10)
        pattern = re.compile(r"ConfigParam\(16\)\s+=\s+\((.+)\)")
        for line in out.splitlines():
            m = pattern.match(line)
            if m:
                data = self._parse_config_tokens(m.group(1))
                params = ElectionValidatorParams(max_validators=int(data.get("max_validators", 0)),
                                                 max_main_validators=int(data.get("max_main_validators", 0)),
                                                 min_validators=int(data.get("min_validators", 0)))
                return params
        return None

    def get_elector_params(self) -> (ElectionParams, None):
        # ConfigParam(15) = ( validators_elected_for:65536 elections_start_before:32768 elections_end_before:8192 stake_held_for:32768)
        out = self._run_command("getconfig 15", timeout=10)
        pattern = re.compile(r"ConfigParam\(15\)\s+=\s+\((.+)\)")
        for line in out.splitlines():
            m = pattern.match(line)
            if m:
                data = self._parse_config_tokens(m.group(1))
                params = ElectionParams(validators_elected_for=int(data.get("validators_elected_for", 0)),
                                        elections_start_before=int(data.get("elections_start_before", 0)),
                                        elections_end_before=int(data.get("elections_end_before", 0)),
                                        stake_held_for=int(data.get("stake_held_for", 0)))
                return params
        return None

    def get_stake_params(self):
        """
        ConfigParam(17) = (
        min_stake:(nanograms
            amount:(var_uint len:6 value:10000000000000))
        max_stake:(nanograms
            amount:(var_uint len:7 value:10000000000000000))
        min_total_stake:(nanograms
            amount:(var_uint len:6 value:100000000000000)) max_stake_factor:196608)
        """
        out = self._run_command("getconfig 17")
        pattern = re.compile(".+min_stake.+?value:(\d+).+max_stake:.+?value:(\d+).+min_total_stake:.+value:(\d+)",
                             flags=re.DOTALL)
        m = pattern.match(out)
        if m:
            return StakeParams(min_stake=int(m.group(1)), max_stake=int(m.group(2)))
        return None

    def get_election_ids(self, elector_addr: str) -> [str]:
        elector_addr = TonAddress.set_address_prefix(elector_addr, TonAddress.Type.MASTER_CHAIN)
        out = self._run_command("runmethod {} active_election_id".format(elector_addr))
        pattern = re.compile(r"result:\s+\[(.+)\]")
        for line in out.splitlines():
            m = pattern.match(line)
            if m:
                ids = m.group(1).strip().split(",")
                return [eid.strip() for eid in ids if eid.strip() != "0"]
        return []

    def get_current_participant_stakes(self, elector_addr: str) -> List[int]:
        elector_addr = TonAddress.set_address_prefix(elector_addr, TonAddress.Type.MASTER_CHAIN)
        out = self._run_command("runmethodfull {} participant_list".format(elector_addr))
        pattern = re.compile(r"result:\s+\[\s*\((.+)\)\s*\]")
        for line in out.splitlines():
            m = pattern.match(line)
            if m:
                participant_info = json.loads(f"[{m.group(1).replace(' ', ',')}]")
                return [p_info[1] for p_info in participant_info]
        return []

    def compute_returned_stakes(self, elector_addr, validator_addr) -> [int]:
        elector_addr = TonAddress.set_address_prefix(elector_addr, TonAddress.Type.MASTER_CHAIN)
        validator_addr = TonAddress.set_address_prefix(validator_addr, TonAddress.Type.HEX)
        out = self._run_command("runmethod {} compute_returned_stake {}".format(elector_addr, validator_addr))
        pattern = re.compile(r"result:\s+\[(.+)\]")
        for line in out.splitlines():
            m = pattern.match(line)
            if m:
                retvals = m.group(1).strip().split(",")
                return [int(val.strip()) for val in retvals if val.strip() != "0"]
        return []
