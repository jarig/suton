import logging
import subprocess

log = logging.getLogger("")


class TonExec(object):

    def __init__(self, exec_path):
        self._exec_path = exec_path

    def _execute(self, args, cwd=None, timeout=None):
        """
        :param args: args to tonos-cli
        :return: return value and stdout of tonos-cli
        """
        params = [self._exec_path] + args
        try:
            out = subprocess.check_output(params, timeout=timeout, cwd=cwd,
                                          # without stdin attached TON utilities failing
                                          stdin=subprocess.PIPE).decode("utf-8")
            # TODO: remove
            log.debug("Output: {}".format(out))
            retcode = 0
        except subprocess.CalledProcessError as e:
            retcode = e.returncode
            out = 'Cmd: {}\n'.format(params)
            out += e.output.decode("utf-8")
        except subprocess.TimeoutExpired as e:
            retcode = 2
            out = 'Cmd: {} (TIMEOUT {}})\n'.format(params, timeout)
            out += e.output.decode("utf-8")
        except Exception as e:
            retcode = -1
            out = 'Cmd: {} (TIMEOUT {})\n'.format(params, timeout)
            out += str(e)
        return retcode, out

