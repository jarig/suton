import logging
from contextlib import contextmanager


class SensitiveFilter(logging.Filter):

    def __init__(self, secrets: list):
        super().__init__("sensitive_filer")
        self._secrets = secrets

    def filter(self, record: logging.LogRecord) -> int:
        if hasattr(record, 'msg'):
            for secret in self._secrets:
                record.msg = record.msg.replace(str(secret), "***")
        if isinstance(record.args, dict):
            for key in record.args:
                for secret in self._secrets:
                    record.args[key] = record.args[key].replace(str(secret), "***")
        else:
            nargs = []
            for i in range(len(record.args)):
                for secret in self._secrets:
                    nargs.append(record.args[i].replace(str(secret), "***"))
            record.args = tuple(nargs)
        return True


@contextmanager
def secret_manager(secrets: list):
    # patcher logger not to print secrets
    filter = SensitiveFilter(secrets)
    for handler in logging.root.handlers:
        handler.addFilter(filter)
    yield
    # remove patchers
    for handler in logging.root.handlers:
        handler.removeFilter(filter)

