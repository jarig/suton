import datetime
import logging
import threading
import time
from typing import List

from logstash.client import LogStashClient
from settings.wallet_settings.wallets import ActionSpec
from tonoscli.core import TonosCli
from tonvalidator.core import TonValidatorEngineConsole


log = logging.getLogger("wallet_management")


class WalletManagementRoutine(object):

    def __init__(self,
                 tonos_cli: TonosCli,
                 validation_engine_console: TonValidatorEngineConsole,
                 specs: List[ActionSpec]):
        self._tonos_cli = tonos_cli
        self._validation_engine_console = validation_engine_console
        self._action_specs = specs

    def start(self):
        thread = threading.Thread(target=self._routine, daemon=True)
        thread.start()

    def _routine(self):
        while True:
            try:
                for spec in self._action_specs:
                    telemetry_data = {
                        "wallet_addr": spec.wallet.addr,
                        "wallet_name": spec.wallet.name
                    }
                    account = self._tonos_cli.get_account(spec.wallet.addr)
                    telemetry_data["wallet_balance"] = account.balance
                    self._send_telemetry("wallet_status", telemetry_data)
                    # if account.balance <= spec.action.
            except Exception:
                log.exception("Failure in wallet management")
            time.sleep(600)

    def _send_telemetry(self, data_type, data: dict):
        data['timestamp'] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        data['data_type'] = data_type
        LogStashClient.get_client().send_data('wallets', data)

