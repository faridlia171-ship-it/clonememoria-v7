import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with safe extra fields."""

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)

        # Standardized base fields
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger_name'] = record.name
        log_record['file'] = record.pathname
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno

        # SAFE custom ID (never a reserved key)
        if hasattr(record, 'cm_request_id'):
            log_record['cm_request_id'] = record.cm_request_id


class DebugFormatter(logging.Formatter):
    """Human-readable formatter for local debugging."""

    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, '')
        timestamp = datetime.utcnow().strftime('%H:%M:%S')

        message = f"{timestamp} {color}[{record.levelname:8}]{self.RESET} {record.name:35} | {record.getMessage()}"

        # Extra safe fields
        extras = {
            k: v for k, v in record.__dict__.items()
            if k not in [
                'name', 'msg', 'args', 'created', 'filename', 'funcName', 'levelname',
                'levelno', 'lineno', 'module', 'msecs', 'message', 'pathname',
                'process', 'processName', 'relativeCreated', 'thread', 'threadName',
                'exc_info', 'exc_text', 'stack_info'
            ]
        }

        if extras:
            extra_str = " | ".join([f"{k}={v}" for k, v in extras.items()])
            message += f" | {extra_str}"

        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"

        return message


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configure logging for application."""

    level = getattr(logging, log_level.upper(), logging.INFO)

    if log_format == "json":
        formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(logger_name)s %(message)s')

    elif log_format == "debug":
        formatter = DebugFormatter()

    else:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Forward uvicorn logs to our formatter
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = True

    root_logger.info(
        "LOGGING_CONFIGURED",
        extra={"log_level": log_level, "log_format": log_format}
    )
