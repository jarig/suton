import json
import logging
import threading
import time
import socket
from queue import Queue, Empty
from typing import Optional, Callable
from datetime import datetime
import sys
import os

# Add parent directory to path to import telemetry base
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from telemetry.base_client import BaseTelemetryClient
from appinsights.log_watcher import LogFileWatcher
from appinsights.parsers import TonValidatorLogParser

try:
    from opencensus.ext.azure import metrics_exporter
    from opencensus.ext.azure.log_exporter import AzureLogHandler, AzureEventHandler
    from opencensus.ext.azure.trace_exporter import AzureExporter
    from applicationinsights import TelemetryClient as AITelemetryClient
    from applicationinsights.channel import SynchronousSender, SynchronousQueue, TelemetryChannel
    APPINSIGHTS_AVAILABLE = True
except ImportError:
    APPINSIGHTS_AVAILABLE = False

logger = logging.getLogger('appinsights_client')


class AppInsightsClient(BaseTelemetryClient):
    """
    Azure Application Insights client which helps sending telemetry data.
    Supports custom events, traces, and metrics.
    """
    _instance = None

    def __init__(self, instrumentation_key: str, pre_conf_data: Optional[dict] = None):
        super().__init__(pre_conf_data)
        if not APPINSIGHTS_AVAILABLE:
            logger.warning("Application Insights SDK not available. Install: pip install opencensus-ext-azure applicationinsights")
            self._instrumentation_key = None
            self._client = None
            self._queue = Queue()
            return
            
        self._instrumentation_key = instrumentation_key
        self._log_watchers = []  # Store log watcher instances
        self._tcp_server = None  # TCP server for receiving data
        self._tcp_server_running = False
        self._queue = Queue()
        self._max_batch = 10
        
        # Initialize Application Insights client
        if instrumentation_key:
            # Create custom channel for better control
            sender = SynchronousSender()
            queue = SynchronousQueue(sender)
            channel = TelemetryChannel(None, queue)
            
            self._client = AITelemetryClient(instrumentation_key, telemetry_channel=channel)
            
            # Add common properties if provided
            if self._pre_conf_data:
                for key, value in self._pre_conf_data.items():
                    self._client.context.properties[key] = value
            
            logger.info("Application Insights client initialized successfully")
        else:
            self._client = None
            logger.warning("No instrumentation key provided, telemetry will not be sent")

    def send_data(self, module: str, data: dict):
        """
        Send custom event data to Application Insights.
        
        Args:
            module: The module/component name sending the data
            data: Dictionary containing the telemetry data
        """
        if not self._client:
            logger.debug("No App Insights client configured, skipping telemetry")
            return
            
        # Add module to data
        event_data = data.copy()
        event_data['module'] = module
        
        # Add pre-configured data
        if self._pre_conf_data:
            event_data.update(self._pre_conf_data)
        
        # Queue the data for batch processing
        self._queue.put(event_data, block=False)

    def _process_data(self):
        """
        Background thread that processes queued telemetry data.
        Sends data in batches to Application Insights.
        """
        while True:
            try:
                # Wait for first item
                data_to_send = [self._queue.get(block=True, timeout=10)]
                
                # Try to batch more items
                max_batch = self._max_batch
                while max_batch > 0:
                    try:
                        data_to_send.append(self._queue.get_nowait())
                        max_batch -= 1
                    except Empty:
                        break
                
                if not self._client:
                    continue
                
                # Send all batched data
                logger.info("Sending {} telemetry events to Application Insights".format(len(data_to_send)))
                for data in data_to_send:
                    try:
                        # Separate properties and metrics
                        properties = {}
                        measurements = {}
                        
                        for key, value in data.items():
                            if isinstance(value, (int, float)):
                                measurements[key] = value
                            else:
                                properties[key] = str(value)
                        
                        # Send as custom event
                        event_name = properties.pop('event_name', 'TonControlEvent')
                        self._client.track_event(event_name, properties, measurements)
                        
                    except Exception as e:
                        logger.error("Failed to send individual event: {}".format(e))
                
                # Flush the client to ensure data is sent
                self._client.flush()
                
            except Empty:
                # No data available, continue waiting
                continue
            except Exception as exc:
                logger.exception("Failed to process telemetry data: {}".format(exc))

    @staticmethod
    def configure_client(instrumentation_key: str, pre_conf_data: Optional[dict] = None):
        """
        Configure the singleton Application Insights client instance.
        
        Args:
            instrumentation_key: Azure Application Insights instrumentation key
            pre_conf_data: Optional dictionary with common properties to include in all telemetry
        """
        AppInsightsClient._instance = AppInsightsClient(instrumentation_key, pre_conf_data=pre_conf_data)

    @staticmethod
    def start_client() -> 'AppInsightsClient':
        """
        Start the background processing thread for the Application Insights client.
        Must be called after configure_client().
        """
        if not AppInsightsClient._instance:
            raise Exception("AppInsightsClient should be configured first, call 'configure_client' before.")
        
        if not AppInsightsClient._instance._client:
            logger.warning("AppInsightsClient not properly initialized, background thread will not process data")
        
        thread = threading.Thread(target=AppInsightsClient._instance._process_data, daemon=True)
        thread.start()
        logger.info("AppInsightsClient background thread started")
        return AppInsightsClient._instance

    @staticmethod
    def get_client():
        """
        Get the singleton instance of the Application Insights client.
        
        Returns:
            AppInsightsClient: The configured client instance
        """
        return AppInsightsClient._instance

    def track_trace(self, message: str, severity: str = 'INFO', properties: Optional[dict] = None):
        """
        Send a trace (log) message to Application Insights.
        
        Args:
            message: The log message
            severity: Log severity level (VERBOSE, INFO, WARNING, ERROR, CRITICAL)
            properties: Optional additional properties
        """
        if not self._client:
            return
        
        props = properties or {}
        if self._pre_conf_data:
            props.update(self._pre_conf_data)
        
        # Map severity levels
        severity_map = {
            'DEBUG': 0,
            'VERBOSE': 0,
            'INFO': 1,
            'WARNING': 2,
            'ERROR': 3,
            'CRITICAL': 4
        }
        severity_level = severity_map.get(severity.upper(), 1)
        
        self._client.track_trace(message, properties=props, severity=severity_level)
        self._client.flush()

    def track_metric(self, name: str, value: float, properties: Optional[dict] = None):
        """
        Send a metric to Application Insights.
        
        Args:
            name: Metric name
            value: Metric value
            properties: Optional additional properties
        """
        if not self._client:
            return
        
        props = properties or {}
        if self._pre_conf_data:
            props.update(self._pre_conf_data)
        
        self._client.track_m
    
    def add_ton_validator_log_watcher(self, log_dir: str, 
                                      pattern: str = "*.log", check_interval: int = 5,
                                      message_filters: Optional[list] = None):
        """
        Add a TON Validator log file watcher that automatically parses and sends logs to Application Insights.
        
        Args:
            log_dir: Directory containing TON validator log files
            pattern: File pattern to match (default: "*.log")
            check_interval: Interval in seconds between file checks (default: 5)
        """
        if not self._client:
            logger.warning("Cannot add log watcher - AppInsights client not initialized")
            return
        
        logger.info("Adding TON Validator log watcher for directory: {}".format(log_dir))
        
        def on_validator_log_line(filename, line):
            parsed = TonValidatorLogParser.parse_line(line, message_filters=message_filters)
            if parsed:
                event_data = TonValidatorLogParser.to_telemetry_event(parsed, filename)
                self.track_trace(
                    message=event_data.get('message', ''),
                    severity=event_data.get('level_name', 'INFO'),
                    properties=event_data
                )
        
        watcher = LogFileWatcher(
            log_dir=log_dir,
            pattern=pattern,
            callback=on_validator_log_line,
            check_interval=check_interval
        )
        
        # Start the watcher in a background thread
        watcher_thread = threading.Thread(target=watcher.watch, daemon=True)
        watcher_thread.start()
        
        # Store the watcher instance
        self._log_watchers.append(watcher)
        
        logger.info("TON Validator log watcher started for {}".format(log_dir))
    
    def stop_log_watchers(self):
        """Stop all active log watchers."""
        logger.info("Stopping {} log watchers".format(len(self._log_watchers)))
        for watcher in self._log_watchers:
            watcher.stop()
        self._log_watchers.clear()
    
    def start_tcp_server(self, host: str = "0.0.0.0", port: int = 5959):
        """
        Start a TCP server that listens for incoming telemetry data.
        Data should be sent as JSON in the format:
        {"module": "<module_name>", "data": {<telemetry_data>}}
        
        Args:
            host: Host address to bind to (default: "0.0.0.0")
            port: Port to listen on (default: 5959)
        """
        if not self._client:
            logger.warning("Cannot start TCP server - AppInsights client not initialized")
            return
        
        if self._tcp_server_running:
            logger.warning("TCP server is already running")
            return
        
        logger.info("Starting TCP server on {}:{}".format(host, port))
        
        def tcp_server_loop():
            try:
                server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server_socket.bind((host, port))
                server_socket.listen(5)
                server_socket.settimeout(1.0)  # Timeout for checking if we should stop
                
                self._tcp_server = server_socket
                self._tcp_server_running = True
                
                logger.info("TCP server listening on {}:{}".format(host, port))
                
                while self._tcp_server_running:
                    try:
                        client_socket, address = server_socket.accept()
                        # Handle client in a separate thread
                        client_thread = threading.Thread(
                            target=self._handle_tcp_client,
                            args=(client_socket, address),
                            daemon=True
                        )
                        client_thread.start()
                    except socket.timeout:
                        continue
                    except Exception as e:
                        if self._tcp_server_running:
                            logger.error("Error accepting connection: {}".format(e))
                
            except Exception as e:
                logger.exception("TCP server error: {}".format(e))
            finally:
                if server_socket:
                    server_socket.close()
                self._tcp_server = None
                self._tcp_server_running = False
                logger.info("TCP server stopped")
        
        # Start server in background thread
        server_thread = threading.Thread(target=tcp_server_loop, daemon=True)
        server_thread.start()
        logger.info("TCP server thread started")
    
    def _handle_tcp_client(self, client_socket: socket.socket, address: tuple):
        """
        Handle a single TCP client connection.
        
        Args:
            client_socket: The client socket
            address: The client address tuple (host, port)
        """
        logger.debug("Accepted connection from {}:{}".format(address[0], address[1]))
        
        try:
            client_socket.settimeout(5.0)
            
            # Read data from socket
            data_buffer = b""
            while True:
                try:
                    chunk = client_socket.recv(4096)
                    if not chunk:
                        break
                    data_buffer += chunk
                    
                    # Try to parse complete JSON objects
                    # Split by newlines in case multiple JSON objects are sent
                    data_str = data_buffer.decode('utf-8', errors='ignore')
                    lines = data_str.split('\n')
                    
                    # Process complete lines, keep incomplete last line in buffer
                    for i, line in enumerate(lines[:-1]):
                        if line.strip():
                            self._process_tcp_message(line.strip())
                    
                    # Keep incomplete data in buffer
                    data_buffer = lines[-1].encode('utf-8')
                    
                except socket.timeout:
                    break
                except Exception as e:
                    logger.error("Error reading from client: {}".format(e))
                    break
            
            # Process any remaining data in buffer
            if data_buffer:
                data_str = data_buffer.decode('utf-8', errors='ignore').strip()
                if data_str:
                    self._process_tcp_message(data_str)
                    
        except Exception as e:
            logger.error("Error handling TCP client from {}: {}".format(address, e))
        finally:
            client_socket.close()
            logger.debug("Closed connection from {}:{}".format(address[0], address[1]))
    
    def _process_tcp_message(self, message: str):
        """
        Process a single JSON message received via TCP.
        Expected format: {"module": "<module_name>", "data": {<telemetry_data>}}
        
        Args:
            message: JSON string message
        """
        try:
            data = json.loads(message)
            
            # Validate message format
            if not isinstance(data, dict):
                logger.warning("Received non-dict TCP message: {}".format(type(data)))
                return
            
            module = data.get('module')
            telemetry_data = data.get('data')
            
            if not module:
                logger.warning("TCP message missing 'module' field: {}".format(message[:100]))
                return
            
            if not isinstance(telemetry_data, dict):
                logger.warning("TCP message 'data' field must be a dict: {}".format(type(telemetry_data)))
                return
            
            # Send through the normal send_data pipeline
            self.send_data(module, telemetry_data)
            logger.debug("Processed TCP message from module: {}".format(module))
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse TCP message as JSON: {} - Message: {}".format(e, message[:100]))
        except Exception as e:
            logger.exception("Error processing TCP message: {}".format(e))
    
    def stop_tcp_server(self):
        """Stop the TCP server if running."""
        if self._tcp_server_running:
            logger.info("Stopping TCP server")
            self._tcp_server_running = False
            # Give server thread time to stop gracefully
            time.sleep(2)
