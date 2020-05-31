import logging

from mqueue.interfaces.tonqueue import TonControllQueueAbstract
import threading
import time
from tonvalidator.core import TonValidatorEngineConsole


log = logging.getLogger("qcontroller")


class QueueRoutine(object):

    def __init__(self, validation_engine_console: TonValidatorEngineConsole,
                 queue_provider: TonControllQueueAbstract):
        self._queue_provider = queue_provider
        self._validation_engine_console = validation_engine_console

    def start(self):
        thread = threading.Thread(target=self._routine, daemon=True)
        thread.start()
    
    def _routine(self):
        while True:
            time.sleep(60)
