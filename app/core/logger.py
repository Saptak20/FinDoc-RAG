import contextvars
import logging
import sys
from typing import Optional

# Thread-safe/async-safe request ID context variable
request_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    """Logging filter that injects the active request ID into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        req_id = request_id_ctx.get()
        record.request_id = f"[{req_id}] " if req_id else ""
        return True


# Setup custom root logger handler with request_id filter
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Clear existing handlers to avoid duplicate logs
root_logger.handlers.clear()

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(request_id)s%(name)s: %(message)s")
handler.setFormatter(formatter)
handler.addFilter(RequestIdFilter())
root_logger.addHandler(handler)

logger = logging.getLogger("findoc_rag")
logger.setLevel(logging.INFO)

