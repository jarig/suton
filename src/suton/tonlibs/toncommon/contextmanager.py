import logging
from contextlib import contextmanager


class SensitiveFilter(logging.Filter):

    def __init__(self, secrets: list):
        super().__init__("sensitive_filer")
        self._secrets = secrets

    def filter(self, record: logging.LogRecord) -> int:
        for secret in self._secrets:
            record.message = record.message.replace(secret, "***")
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

