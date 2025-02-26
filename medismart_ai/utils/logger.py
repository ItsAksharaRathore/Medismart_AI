"""
Logger utility for consistent logging throughout the application.
"""
import logging
import logging.handlers
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional

class Logger:
    """
    Logger utility that provides consistent, configurable logging across the application.
    """
    
    # Log levels mapped to logging module constants
    LEVELS = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }
    
    def __init__(self, 
                 log_dir: str = "logs",
                 app_name: str = "healthcare_app",
                 log_level: str = "info",
                 log_to_console: bool = True,
                 log_to_file: bool = True,
                 max_file_size_mb: int = 10,
                 backup_count: int = 5,
                 json_format: bool = False):
        """
        Initialize the logger.
        
        Args:
            log_dir: Directory to store log files
            app_name: Name of the application
            log_level: Minimum log level to capture
            log_to_console: Whether to log to console
            log_to_file: Whether to log to file
            max_file_size_mb: Maximum size of log file in MB before rotation
            backup_count: Number of backup log files to keep
            json_format: Whether to format logs as JSON
        """
        self.log_dir = log_dir
        self.app_name = app_name
        self.log_to_console = log_to_console
        self.log_to_file = log_to_file
        self.json_format = json_format
        
        # Create log directory if it doesn't exist
        if self.log_to_file and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Set log level
        self.log_level = self.LEVELS.get(log_level.lower(), logging.INFO)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # Remove any existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Create formatters
        if json_format:
            self.formatter = self._create_json_formatter()
        else:
            self.formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # Add console handler if enabled
        if log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(self.formatter)
            root_logger.addHandler(console_handler)
        
        # Add file handler if enabled
        if log_to_file:
            log_file = os.path.join(log_dir, f"{app_name}.log")
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size_mb * 1024 * 1024,
                backupCount=backup_count
            )
            file_handler.setFormatter(self.formatter)
            root_logger.addHandler(file_handler)
        
        # Create app logger
        self.logger = logging.getLogger(app_name)
        self.logger.setLevel(self.log_level)
    
    def _create_json_formatter(self):
        """Create a JSON formatter for structured logging."""
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "line": record.lineno
                }
                
                # Add exception info if available
                if record.exc_info:
                    log_data["exception"] = {
                        "type": record.exc_info[0].__name__,
                        "message": str(record.exc_info[1])
                    }
                
                # Add extra fields
                for key, value in record.__dict__.items():
                    if key.startswith("_") or key in ['args', 'exc_info', 'exc_text', 
                                                     'levelname', 'levelno', 'lineno', 
                                                     'module', 'msecs', 'message', 'msg', 
                                                     'name', 'pathname', 'process', 
                                                     'processName', 'relativeCreated', 
                                                     'stack_info', 'thread', 'threadName']:
                        continue
                    log_data[key] = value
                
                return json.dumps(log_data)
        
        return JsonFormatter()
    
    def get_logger(self, name: str = None) -> logging.Logger:
        """
        Get a named logger.
        
        Args:
            name: Name of the logger
            
        Returns:
            Logger instance
        """
        if name:
            return logging.getLogger(f"{self.app_name}.{name}")
        return self.logger
    
    def log(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None):
        """
        Log a message with the specified level.
        
        Args:
            level: Log level
            message: Log message
            extra: Additional fields to include in the log
        """
        log_method = getattr(self.logger, level.lower(), None)
        if log_method:
            log_method(message, extra=extra)
    
    def set_level(self, level: str):
        """
        Set the log level.
        
        Args:
            level: New log level
        """
        if level.lower() in self.LEVELS:
            self.logger.setLevel(self.LEVELS[level.lower()])
    
    def create_audit_logger(self, name: str = "audit") -> logging.Logger:
        """
        Create a specialized audit logger for compliance purposes.
        
        Args:
            name: Name of the audit logger
            
        Returns:
            Audit logger instance
        """
        audit_logger = logging.getLogger(f"{self.app_name}.{name}")
        audit_logger.setLevel(logging.INFO)
        
        if self.log_to_file:
            audit_log_file = os.path.join(self.log_dir, f"{self.app_name}_{name}.log")
            handler = logging.handlers.RotatingFileHandler(
                audit_log_file,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=10
            )
            handler.setFormatter(self.formatter)
            audit_logger.addHandler(handler)
        
        return audit_logger