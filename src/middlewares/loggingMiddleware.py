import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


log = logging.getLogger('ЛогерМиделвеир')


class LoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        log.info(f"{request_id} | Request")
        time_start = time.time()

        response = await call_next(request)

        log.info(f"{request_id} | Response time = {time.time() - time_start}")

        return response