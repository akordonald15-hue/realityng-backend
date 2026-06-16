"""Request correlation ID middleware and logging helpers."""

from __future__ import annotations

import contextvars
import logging
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

REQUEST_ID_HEADER = "HTTP_X_REQUEST_ID"
RESPONSE_REQUEST_ID_HEADER = "X-Request-ID"

request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestCorrelationIdMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.META.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = request_id_context.set(request_id)
        request.request_id = request_id

        try:
            response = self.get_response(request)
            response[RESPONSE_REQUEST_ID_HEADER] = request_id
            return response
        finally:
            request_id_context.reset(token)


class RequestIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        return True

