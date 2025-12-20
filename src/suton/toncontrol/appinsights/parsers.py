import re
import logging
from typing import Optional, Dict

logger = logging.getLogger('log_parser')


class TonValidatorLogParser:
    """
    Parser for TON Validator log format.
    Supports multiple formats:
    1. Old format: [level][thread_id][timestamp][module][function]message
    2. New format: timestamp LEVEL [module] thread_id: message
    """
    
    # Pattern 1: Old format - [level][t thread_id][timestamp][module][function]message
    # Example: [ 1][t 1][1639900800.123][validator.impl][process_block]Processing block...
    OLD_LOG_PATTERN = re.compile(
        r'\[\s*(?P<level>\d+)\]'  # [level]
        r'\[t\s*(?P<thread_id>\d+)\]'  # [t thread_id]
        r'\[(?P<time_epoch>[\d.]+)\]'  # [timestamp]
        r'\[(?P<module>\w+)(?P<module_ext>[^\]]*)\]'  # [module.extension]
        r'\[(?P<func>[^\]]*)\]'  # [function]
        r'(?P<message>.*)$'  # message
    )
    
    # Pattern 2: New format - timestamp LEVEL [module] thread_id: message
    # Example: 2025-09-21 18:07:47.682767982 ERROR [remp] 140513612269312: Cannot deserialize message from RMQ 18*e
    NEW_LOG_PATTERN = re.compile(
        r'^(?P<timestamp>[\d\-:\s.]+?)\s+'  # timestamp
        r'(?P<level_name>TRACE|DEBUG|INFO|WARNING|ERROR|FATAL|CRITICAL)\s+'  # level name
        r'\[(?P<module>[^\]]+)\]\s+'  # [module]
        r'(?P<thread_id>\d+):\s+'  # thread_id:
        r'(?P<message>.*)$'  # message
    )

    # Log level mapping (for old format)
    LEVEL_MAP = {
        '0': 'FATAL',
        '1': 'ERROR',
        '2': 'WARNING',
        '3': 'INFO',
        '4': 'DEBUG',
        '5': 'TRACE'
    }
    
    @staticmethod
    def parse_line(line: str, message_filters: Optional[list] = None) -> Optional[Dict[str, str]]:
        """
        Parse a TON validator log line.
        Tries multiple patterns to match different log formats.
        
        Args:
            line: Raw log line string
            
        Returns:
            Dictionary with parsed fields or None if parsing failed
        """
        parsed = None
        
        # Try new format first (more common)
        match = TonValidatorLogParser.NEW_LOG_PATTERN.match(line)
        if match:
            parsed = match.groupdict()
            parsed['format'] = 'new'
            # For new format, level_name is already captured
            parsed['module_full'] = parsed.get('module', '')
            parsed['func'] = None  # New format doesn't have function field
        else:
            # Try old format
            match = TonValidatorLogParser.OLD_LOG_PATTERN.match(line)
            if match:
                parsed = match.groupdict()
                parsed['format'] = 'old'
                
                # Map numeric level to string for old format
                level_num = parsed.get('level', '3')
                parsed['level_name'] = TonValidatorLogParser.LEVEL_MAP.get(level_num, 'INFO')
                
                # Combine module and extension
                module = parsed.get('module', '')
                module_ext = parsed.get('module_ext', '')
                parsed['module_full'] = module + module_ext
        
        if not parsed:
            return None
        
        # Clean up message
        message = parsed.get('message', '').strip()
        parsed['message'] = message
        
        # Check for SLOW messages and extract additional data
        if not message or (message_filters and not any(tag in message for tag in message_filters)):
            return None
        
        return parsed
    
    @staticmethod
    def to_telemetry_event(parsed_data: Dict[str, str], filename: str) -> Dict[str, any]:
        """
        Convert parsed log data to telemetry event format.
        
        Args:
            parsed_data: Dictionary from parse_line()
            filename: Name of the log file
            
        Returns:
            Dictionary formatted for telemetry ingestion
        """
        event = {
            'event_name': 'TonValidatorLog',
            'filename': filename,
            'level': parsed_data.get('level'),
            'level_name': parsed_data.get('level_name'),
            'thread_id': parsed_data.get('thread_id'),
            'timestamp': parsed_data.get('timestamp') or parsed_data.get('time_epoch'),
            'module': parsed_data.get('module_full'),
            'function': parsed_data.get('func'),
            'message': parsed_data.get('message'),
            'log_source': 'ton_validator',
            'log_format': parsed_data.get('format', 'unknown')
        }
        
        # Add SLOW message metadata if present
        if parsed_data.get('is_slow'):
            event['is_slow'] = True
            event['slow_module'] = parsed_data.get('slow_module')
            event['slow_duration_ms'] = parsed_data.get('slow_duration_ms')
            # Change event name for better tracking
            event['event_name'] = 'TonValidatorSlowOperation'
        
        return event
