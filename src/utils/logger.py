import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
import os

class CustomFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: blue + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)

def setup_logger(name: str) -> logging.Logger:
    """Setup logger with both file and console handlers"""
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Create handlers
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(CustomFormatter())
    
    # Add console handler
    logger.addHandler(console_handler)

    # Only add file handlers if not running on Railway
    if not os.getenv('RAILWAY_ENVIRONMENT'):
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # File handlers setup...
        debug_file_handler = RotatingFileHandler(
            log_dir / "debug.log",
            maxBytes=10*1024*1024,
            backupCount=5
        )
        debug_file_handler.setLevel(logging.DEBUG)
        debug_file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )

        error_file_handler = RotatingFileHandler(
            log_dir / "error.log",
            maxBytes=10*1024*1024,
            backupCount=5
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )

        # Add file handlers
        logger.addHandler(debug_file_handler)
        logger.addHandler(error_file_handler)

    return logger

def log_async_error(logger: logging.Logger, error: Exception, context: str = None):
    """Helper function to log async errors with context"""
    error_msg = f"Async Error: {str(error)}"
    if context:
        error_msg = f"{context} - {error_msg}"
    logger.error(error_msg, exc_info=True) 