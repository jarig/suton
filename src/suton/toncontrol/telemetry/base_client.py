from abc import ABC, abstractmethod
from typing import Optional


class BaseTelemetryClient(ABC):
    """
    Base interface for telemetry clients that send monitoring data.
    All telemetry client implementations should inherit from this class.
    """
    _instance = None

    def __init__(self, pre_conf_data: Optional[dict] = None):
        """
        Initialize base telemetry client.
        
        Args:
            pre_conf_data: Optional dictionary with pre-configured data to include in all telemetry
        """
        self._pre_conf_data = pre_conf_data

    @abstractmethod
    def send_data(self, module: str, data: dict):
        """
        Send telemetry data.
        
        Args:
            module: The module/component name sending the data
            data: Dictionary containing the telemetry data to send
        """
        pass

    @staticmethod
    @abstractmethod
    def configure_client(*args, **kwargs):
        """
        Static method to configure the singleton instance.
        Each implementation should override this with specific parameters.
        """
        pass

    @staticmethod
    @abstractmethod
    def start_client() -> 'BaseTelemetryClient':
        """
        Static method to start the client's background processing.
        """
        pass

    @staticmethod
    def get_client():
        """
        Get the singleton instance of the telemetry client.
        
        Returns:
            The configured telemetry client instance
        """
        raise NotImplementedError("Subclass must implement get_client()")


class DummyTelemetryClient(BaseTelemetryClient):
    """
    Dummy telemetry client that does nothing.
    Useful for testing or when telemetry is disabled.
    """

    def send_data(self, module: str, data: dict):
        # Do nothing
        pass

    @staticmethod
    def configure_client(*args, **kwargs):
        DummyTelemetryClient._instance = DummyTelemetryClient()

    @staticmethod
    def start_client() -> 'DummyTelemetryClient':
        return DummyTelemetryClient._instance

    @staticmethod
    def get_client():
        return DummyTelemetryClient._instance


class ActiveTelemetryClient:
    _client: BaseTelemetryClient = DummyTelemetryClient()

    def set_client(client: BaseTelemetryClient):
        ActiveTelemetryClient._client = client
    
    def get_client() -> BaseTelemetryClient:
        return ActiveTelemetryClient._client