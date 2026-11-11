import json
import logging
import os
from datetime import datetime, timezone

from catalog.tracing import get_trace_id


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": os.getenv("SERVICE_NAME", "catalog-api"),
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", None) or get_trace_id(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)
