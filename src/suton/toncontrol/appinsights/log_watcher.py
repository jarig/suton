import os
import time
import logging
from typing import Optional, Callable
from pathlib import Path

logger = logging.getLogger('log_watcher')


class LogFileWatcher:
    """
    Watches log files for changes and processes new lines.
    Implements periodic reading with position tracking.
    """
    
    def __init__(self, log_dir: str, pattern: str = "*.log", 
                 callback: Optional[Callable[[str, str], None]] = None,
                 check_interval: int = 5):
        """
        Initialize log file watcher.
        
        Args:
            log_dir: Directory containing log files to watch
            pattern: File pattern to match (e.g., "*.log")
            callback: Function to call for each new line. Receives (filename, line)
            check_interval: Interval in seconds between checks
        """
        self.log_dir = Path(log_dir)
        self.pattern = pattern
        self.callback = callback
        self.check_interval = check_interval
        self._file_positions = {}  # Track read position for each file
        self._running = False
        
        if not self.log_dir.exists():
            logger.warning("Log directory does not exist: {}".format(log_dir))
    
    def _get_log_files(self):
        """Get list of log files matching the pattern."""
        if not self.log_dir.exists():
            return []
        return list(self.log_dir.glob(self.pattern))
    
    def _read_new_lines(self, file_path: Path):
        """
        Read new lines from a file since last position.
        
        Args:
            file_path: Path to the log file
            
        Returns:
            List of new lines
        """
        try:
            file_str = str(file_path)
            
            # Get current file size
            current_size = file_path.stat().st_size
            
            # Get last known position
            last_position = self._file_positions.get(file_str, 0)
            
            # Check if file was truncated or rotated
            if current_size < last_position:
                logger.info("File {} appears to be rotated or truncated, resetting position".format(file_path.name))
                last_position = 0
            
            # Read new content
            new_lines = []
            if current_size > last_position:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(last_position)
                    new_lines = f.readlines()
                    self._file_positions[file_str] = f.tell()
            
            return new_lines
            
        except Exception as e:
            logger.error("Failed to read file {}: {}".format(file_path, e))
            return []
    
    def _process_file(self, file_path: Path):
        """Process a single log file for new lines."""
        new_lines = self._read_new_lines(file_path)
        
        if new_lines and self.callback:
            for line in new_lines:
                line = line.rstrip('\n\r')
                if line:  # Skip empty lines
                    try:
                        self.callback(file_path.name, line)
                    except Exception as e:
                        logger.error("Error processing line from {}: {}".format(file_path.name, e))
    
    def watch(self):
        """
        Start watching log files. This is a blocking call.
        Should be run in a separate thread.
        """
        self._running = True
        logger.info("Starting log file watcher for {} with pattern {}".format(self.log_dir, self.pattern))
        
        while self._running:
            try:
                # Get all matching log files
                log_files = self._get_log_files()
                
                # Process each file
                for log_file in log_files:
                    self._process_file(log_file)
                
                # Wait before next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.exception("Error in log watcher loop: {}".format(e))
                time.sleep(self.check_interval)
    
    def stop(self):
        """Stop watching log files."""
        logger.info("Stopping log file watcher")
        self._running = False
