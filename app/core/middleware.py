import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.logger import logger, request_id_ctx


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns a unique correlation ID to every incoming HTTP request,
    sets it in the logging context, measures execution latency, sanitizes any unhandled
    server exceptions, and injects standard security and correlation headers into outgoing responses.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract or generate Request ID
        incoming_id = request.headers.get("X-Request-ID")
        if incoming_id and len(incoming_id.strip()) <= 64:
            request_id = incoming_id.strip()
        else:
            request_id = uuid.uuid4().hex[:12]

        # Set request_id in contextvar and request state
        token = request_id_ctx.set(request_id)
        request.state.request_id = request_id

        start_time = time.perf_counter()

        # Log incoming request
        client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
        logger.info(f"Incoming {request.method} {request.url.path} from {client_ip}")

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.exception(f"Unhandled exception during {request.method} {request.url.path} after {duration_ms:.1f}ms: {exc}")
            response = JSONResponse(
                status_code=500,
                content={
                    "detail": "An internal server error occurred while processing the request.",
                    "request_id": request_id,
                },
            )
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000.0

        # Log response status
        logger.info(
            f"Completed {request.method} {request.url.path} with status {response.status_code} in {duration_ms:.1f}ms"
        )

        # Inject correlation and security headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"

        request_id_ctx.reset(token)
        return response
