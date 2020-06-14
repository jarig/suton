import base64
import hashlib
import logging
import os
import tempfile

from toncommon.core import TonExec

log = logging.getLogger("fiftcli")


class FiftCli(TonExec):
    """
    Python wrapper for Fift CLI
    """

    def __init__(self, cli_path, includes=None):
        super().__init__(cli_path)
        self._includes = includes

    def _run_command(self, options: list):
        """
        ./tonos-cli <command> <options>
        """
        args = []
        if self._includes:
            args += ['-I', self._includes]
        args = args + options
        log.debug("Running: {} {}".format(self._exec_path, args))
        ret, out = self._execute(args)
        if ret != 0:
            raise Exception("Failed to run fift: {}".format(out))
        return out

    def generate_boc(self, fif_filename, args: list = None) -> (str, str):
        temp_path = os.path.join(tempfile.mkdtemp(), 'query.boc')
        cmds = ['-s', fif_filename]
        if args:
            cmds += args
        out = self._run_command(cmds + [temp_path])
        if not os.path.exists(temp_path):
            raise Exception("Failed to generate boc file: {}".format(out))
        with open(temp_path) as f:
            return base64.b64encode(f.read()), out

    def generate_recover_stake_req(self):
        boc64, _ = self.generate_boc('recover-stake.fif')
        return boc64

    def generate_validation_req(self, wallet_addr, election_start, key_adnl) -> str:
        _, out = self.generate_boc('validator-elect-req.fif',
                                   args=[wallet_addr, election_start, '2', key_adnl])
        return out

    def generate_validation_signed(self, wallet_addr, election_start, key_adnl, election_key,
                                   signature) -> str:
        boc64, _ = self.generate_boc('validator-elect-signed.fif',
                                     args=[wallet_addr, election_start, '2', key_adnl,
                                           election_key, signature])
        return boc64
