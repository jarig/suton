import json
import logging
import socket
import threading
from queue import Queue, Empty
from typing import Optional

logger = logging.getLogger('logstash_client')


class LogStashClient(object):
    """
        Logstash client which helps sending data to logstash service via TCP protocol in json format
    """
    _instance = None

    def __init__(self, hostname, port, pre_conf_data: Optional[dict] = None):
        self._hostname = hostname
        self._port = port
        self._queue = Queue()
        self._max_batch = 10
        self._pre_conf_data = pre_conf_data

    def send_data(self, module, data: dict):
        data['module'] = module
        if self._pre_conf_data:
            data.update(self._pre_conf_data)
        self._queue.put(data, block=False)

    def _process_data(self):
        while True:
            try:
                data_to_send = [self._queue.get(block=True, timeout=10)]
                max_batch = self._max_batch
                while max_batch > 0:
                    # check if more data available and batch it
                    try:
                        data_to_send.append(self._queue.get_nowait())
                        max_batch -= 1
                    except Empty:
                        break
                if not self._hostname or not self._port:
                    continue
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                sock.connect((self._hostname, self._port))
                sock.settimeout(5)
                try:
                    logger.info("Sending {} data chunks to logstash".format(len(data_to_send)))
                    for data in data_to_send:
                        sock.send(str(json.dumps(data)).encode('utf-8'))
                finally:
                    sock.close()
            except Empty:
                # waiting again for more data
                continue
            except socket.error as msg:
                logger.error("Failed to send data to logstash: {}".format(msg))
            except Exception as exc:
                logger.exception("Failed to send data to logstash: {}".format(exc))

    @staticmethod
    def configure_client(hostname, port, pre_conf_data=None):
        LogStashClient._instance = LogStashClient(hostname, port, pre_conf_data=pre_conf_data)

    @staticmethod
    def start_client():
        if not LogStashClient._instance:
            raise Exception("LogStashClient should be configured first, call 'configure_client' before.")
        thread = threading.Thread(target=LogStashClient._instance._process_data, daemon=True)
        thread.start()

    @staticmethod
    def get_client():
        """
        :rtype: LogStashClient
        """
        return LogStashClient._instance

