import logging
import re

from toncommon.core import TonExec
from tonvalidator.exceptions.connection import TonConnectionException
import sys

log = logging.getLogger("tonvalidator")


class TonValidatorEngineConsole(TonExec):
    
    def __init__(self, exec_path, client_key, server_pub_key, server_addr):
        self._exec_path = exec_path
        self._client_key = client_key
        self._server_pub_key = server_pub_key
        self._server_addr = server_addr

    def _run_command(self, commands: list, timeout=10):
        """
        ./validator-engine-console" \
        -a 127.0.0.1:3030 \
        -k "${KEYS_DIR}/client" \
        -p "${KEYS_DIR}/server.pub" \
        -c "getstats" -c "quit"
        """
        args = ['-a', self._server_addr,
                '-k', self._client_key,
                '-p', self._server_pub_key,
                '-t', str(timeout)]
        for comm in commands:
            args += ['-c', comm]
        args += ['-c', 'quit']
        log.debug("Running: {} {}".format(self._exec_path, args))
        ret, out = self._execute(args)
        return ret, out

    def get_stats(self):
        ret, out = self._run_command(['getstats'])
        stats = {}
        if ret != 0:
            raise TonConnectionException("Failed to retrieve stats: {}".format(out))
        output_started = False
        for line in out.splitlines():
            if not output_started and 'conn ready' in line:
                output_started = True
                continue
            if output_started:
                tokens = line.split('\t', maxsplit=1)
                if len(tokens) > 1:
                    stats[tokens[0].strip()] = tokens[1].strip()
        return stats

    def get_sync_time_diff(self):
        stats = self.get_stats()
        if stats:
            return int(stats['unixtime']) - int(stats['masterchainblocktime'])
        return sys.maxsize

    def get_new_key(self):
        ret, out = self._run_command(['newkey'])
        new_key_pattern = re.compile(r"created new key(.+)")
        for line in out.splitlines():
            m = new_key_pattern.match(line)
            if m:
                return m.group(1).strip()
        return None

    def delete_temp_key(self, key, temp_key):
        ret, out = self._run_command(['deltempkey {} {}'.format(key, temp_key)])

    def delete_key(self, key):
        ret, out = self._run_command(['delpermkey {}'.format(key)])

    def prepare_election(self, election_key, key_adnl, election_start, election_stop) -> str:
        commands = ['addpermkey {key} {election_start} {election_stop}',
                    'addtempkey {key} {key} {election_stop}',
                    'addadnl {key_adnl} 0',
                    'addvalidatoraddr {key} {key_adnl} {election_stop}']
        interpolated_cmds = []
        for cmd in commands:
            interpolated_cmds.append(cmd.format(
                key=election_key,
                key_adnl=key_adnl,
                election_start=election_start,
                election_stop=election_stop
            ))
        ret, out = self._run_command(interpolated_cmds)
        if ret != 0:
            raise Exception("Failed to prepare elections: {}".format(out))
        return out

    def sign_request(self, election_key, request) -> (str, str):
        ret, out = self._run_command(['exportpub {}'.format(election_key),
                                      'sign {} {}'.format(election_key, request)])
        if ret != 0:
            raise Exception("Failed to generate signature: {}".format(out))
        signature_pattern = re.compile(r"got signature(.+)")
        public_key_pattern = re.compile(r"got public key:(.+)")
        signature = None
        pub_key = None
        for line in out.splitlines():
            m = signature_pattern.match(line)
            if m:
                signature = m.group(1).strip()
                continue
            m = public_key_pattern.match(line)
            if m:
                pub_key = m.group(1).strip()
        return signature, pub_key
