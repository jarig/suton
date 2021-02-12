import logging
import subprocess

log = logging.getLogger("toncommon")


class TonExec(object):

    def __init__(self, exec_path):
        self._exec_path = exec_path

    def _execute(self, args, cwd=None, timeout=None):
        """
        :param args: args to tonos-cli
        :return: return value and stdout of tonos-cli
        """
        str_args = [str(arg) for arg in args]
        params = [self._exec_path] + str_args
        try:
            process = subprocess.run(params, timeout=timeout, cwd=cwd,
                                     capture_output=True,
                                     check=True, text=True,
                                     # without stdin attached TON utilities failing
                                     stdin=subprocess.PIPE)
            out = process.stdout.strip()
            retcode = 0
        except subprocess.CalledProcessError as e:
            retcode = e.returncode
            out = f'Cmd: {params}, {e}\n'
            out += e.output
        except subprocess.TimeoutExpired as e:
            retcode = 2
            out = f'Cmd: {params} (TIMEOUT {timeout})\n'
            out += e.output
        except Exception as e:
            retcode = -1
            out = f'Cmd: {params} (TIMEOUT {timeout})\n'
            out += str(e)
        log.debug(f"Code: {retcode}. Output: {out}")
        return retcode, out

