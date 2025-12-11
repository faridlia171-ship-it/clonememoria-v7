import logging
import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)
logger.info("MIDDLEWARE_MODULE_LOADED", extra={"file": __file__})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests with request ID and timing."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        logger.info("REQUEST_LOGGING_MIDDLEWARE_INITIALIZED")

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.time()

        log_extra = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_host": request.client.host if request.client else None
        }

        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.request_id = request_id
            return record

        logging.setLogRecordFactory(record_factory)

        logger.info("REQUEST_STARTED", extra=log_extra)

        try:
            response: Response = await call_next(request)

            elapsed_time = time.time() - start_time

            log_extra.update({
                "status_code": response.status_code,
                "elapsed_time": f"{elapsed_time:.3f}s"
            })

            logger.info("REQUEST_COMPLETED", extra=log_extra)

            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            elapsed_time = time.time() - start_time

            log_extra.update({
                "elapsed_time": f"{elapsed_time:.3f}s",
                "error": str(e),
                "error_type": type(e).__name__
            })

            logger.error("REQUEST_FAILED", extra=log_extra, exc_info=True)

            raise

        finally:
            logging.setLogRecordFactory(old_factory)
