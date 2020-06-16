import logging
import re

from toncommon.core import TonExec
from tonliteclient.exceptions.base import TonLiteClientException
from tonliteclient.models.ElectionParams import ElectionParams

log = logging.getLogger("tonclient")


class TonLiteClient(TonExec):
    """
    Python wrapper for ton-client CLI
    """
    
    def __init__(self, client_path, server_addr, client_pub_key):
        super().__init__(client_path)
        self._server_addr = server_addr
        self._client_pub_key = client_pub_key

    def _run_command(self, command):
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
        ret, out = self._execute(args)
        if ret != 0:
            raise TonLiteClientException("Failed to run command {}: {}".format(command, out))
        return out

    def set_address_prefix(self, adr, prefix):
        # remove all possible existing prefixes first
        adr = adr.replace("1:", "")
        adr = adr.replace("-1:", "")
        adr = adr.replace("0x", "")
        return f"{prefix}{adr}"

    def get_elector_address(self):
        out = self._run_command("getconfig 1")
        # get address from the output
        pattern = re.compile(r".+elector_addr:x(.+)\)$")
        for line in out.splitlines():
            m = pattern.match(line)
            if m:
                return m.group(1).strip()
        return None

    def get_elector_params(self) -> (ElectionParams, None):
        # ConfigParam(15) = ( validators_elected_for:65536 elections_start_before:32768 elections_end_before:8192 stake_held_for:32768)
        out = self._run_command("getconfig 15")
        pattern = re.compile(r"ConfigParam\(15\)\s+=\s+\((.+)\)")
        for line in out.splitlines():
            m = pattern.match(line)
            if m:
                tokens = re.split(r"\t|\s", m.group(1))
                data = {}
                for token in tokens:
                    if token.strip():
                        name_val = token.split(":")
                        data[name_val[0].strip()] = name_val[1].strip()
                params = ElectionParams(validators_elected_for=int(data.get("validators_elected_for", 0)),
                                        elections_start_before=int(data.get("elections_start_before", 0)),
                                        elections_end_before=int(data.get("elections_end_before", 0)),
                                        stake_held_for=int(data.get("stake_held_for", 0)))
                return params
        return None

    def get_election_ids(self, elector_addr: str) -> [str]:
        elector_addr = self.set_address_prefix(elector_addr, '-1:')
        out = self._run_command("runmethod {} active_election_id".format(elector_addr))
        pattern = re.compile(r"result:\s+\[(.+)\]")
        for line in out.splitlines():
            m = pattern.match(line)
            if m:
                ids = m.group(1).strip().split(",")
                return [eid.strip() for eid in ids if eid.strip() != "0"]
        return []

    def compute_returned_stakes(self, elector_addr, validator_addr) -> [str]:
        elector_addr = self.set_address_prefix(elector_addr, '-1:')
        validator_addr = self.set_address_prefix(validator_addr, '0x')
        out = self._run_command("runmethod {} compute_returned_stake {}".format(elector_addr, validator_addr))
        pattern = re.compile(r"result:\s+\[(.+)\]")
        for line in out.splitlines():
            m = pattern.match(line)
            if m:
                retvals = m.group(1).strip().split(",")
                return [val.strip() for val in retvals if val.strip() != "0"]
        return []
