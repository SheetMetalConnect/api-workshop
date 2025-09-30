"""
Centralized logging configuration for the MES API.

Provides structured logging with proper formatting, levels,
and integration with monitoring systems.
"""

import logging
import logging.config
import os
import sys
from datetime import datetime
from typing import Dict, Any
import json


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add extra fields if present
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id

        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id

        if hasattr(record, 'operation_key'):
            log_data['operation_key'] = record.operation_key

        # Add exception information if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }

        return json.dumps(log_data)


def setup_logging(
    log_level: str = None,
    json_format: bool = None,
    log_file: str = None
) -> None:
    """
    Setup application logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to use JSON formatting
        log_file: Path to log file (optional)
    """
    # Get configuration from environment
    log_level = log_level or os.getenv("LOG_LEVEL", "INFO").upper()
    json_format = json_format if json_format is not None else os.getenv("LOG_JSON", "false").lower() == "true"
    log_file = log_file or os.getenv("LOG_FILE")

    # Create formatters
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    # Setup handlers
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    # File handler (if specified)
    if log_file:
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        handlers=handlers,
        force=True  # Override any existing configuration
    )

    # Set specific logger levels
    logger_levels = {
        "uvicorn": "INFO",
        "uvicorn.access": "WARNING",
        "sqlalchemy.engine": "WARNING",
        "sqlalchemy.pool": "WARNING",
        "app": log_level
    }

    for logger_name, level in logger_levels.items():
        logging.getLogger(logger_name).setLevel(getattr(logging, level))

    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={log_level}, json={json_format}, file={log_file}")


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance with proper configuration."""
    return logging.getLogger(name or __name__)


class RequestContextFilter(logging.Filter):
    """Filter to add request context to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to the log record."""
        # This would typically get context from a context variable
        # For now, we'll add placeholder logic
        if not hasattr(record, 'request_id'):
            record.request_id = None

        if not hasattr(record, 'user_id'):
            record.user_id = None

        return True


# Logging configuration for different environments
LOGGING_CONFIGS = {
    "development": {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s"
            },
            "simple": {
                "format": "%(levelname)s - %(name)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "stream": "ext://sys.stdout"
            }
        },
        "loggers": {
            "app": {
                "level": "DEBUG",
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            }
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"]
        }
    },

    "production": {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "app.core.logging_config.JSONFormatter"
            }
        },
        "filters": {
            "request_context": {
                "()": "app.core.logging_config.RequestContextFilter"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "json",
                "filters": ["request_context"],
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filters": ["request_context"],
                "filename": "/var/log/mes-api/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            }
        },
        "loggers": {
            "app": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False
            }
        },
        "root": {
            "level": "WARNING",
            "handlers": ["console"]
        }
    }
}


def configure_logging_from_dict(environment: str = "development") -> None:
    """Configure logging using dictionary configuration."""
    config = LOGGING_CONFIGS.get(environment, LOGGING_CONFIGS["development"])
    logging.config.dictConfig(config)