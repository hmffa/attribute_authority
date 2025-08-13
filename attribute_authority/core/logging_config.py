import logging
import logging.config
from typing import Any, Dict
from pydantic import BaseModel

from ..core.config import settings

class LogConfig(BaseModel):
    """Logging configuration"""
    LOGGER_NAME: str = "attribute_authority_api"
    LOG_FORMAT: str = "%(levelname)s | %(asctime)s | %(message)s"
    LOG_LEVEL: str = getattr(settings, "LOG_LEVEL", "INFO")

    # Configure logging settings
    version: int = 1
    disable_existing_loggers: bool = False
    formatters: Dict[str, Dict[str, str]] = {
        "default": {
            "format": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }
    handlers: Dict[str, Dict[str, Any]] = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    }
    loggers: Dict[str, Dict[str, Any]] = {
        "attribute_authority_api": {"handlers": ["default"], "level": LOG_LEVEL},
    }

# Configure logging
logging.config.dictConfig(LogConfig().model_dump())
logger = logging.getLogger("attribute_authority_api")

# TODO: For production, log to a file and rotate logs
# TODO: To catch logs from all libraries (not just your own), add a root logger
