# src/wavewarn/middleware/logging.py
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("wavewarn.api")
logging.basicConfig(level=logging.INFO)

class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        t0 = time.time()
        resp = await call_next(request)
        dt = (time.time() - t0) * 1000.0
        logger.info("%s %s → %s in %.1f ms",
                    request.method, request.url.path, resp.status_code, dt)
        return resp

