"""Contract-shaped error envelope and a FastAPI exception handler.

All backend JSON errors follow:
    {"error": {"code", "message", "retryable", "request_id"}}
"""
from __future__ import annotations

import uuid

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        retryable: bool = False,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)


def _envelope(code: str, message: str, retryable: bool, request_id: str) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "request_id": request_id,
        }
    }


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope(exc.code, exc.message, exc.retryable, request_id),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    return JSONResponse(
        status_code=500,
        content=_envelope(
            "internal_error",
            "An unexpected error occurred.",
            True,
            request_id,
        ),
    )


# Convenience constructors matching contract status meanings.
def not_found(message: str = "Unknown area or resource.") -> ApiError:
    return ApiError(404, "not_found", message)


def conflict(message: str, code: str = "conflict") -> ApiError:
    return ApiError(409, code, message)


def too_large(message: str = "Upload exceeds the allowed size.") -> ApiError:
    return ApiError(413, "payload_too_large", message)


def validation_error(message: str = "Request could not be processed.") -> ApiError:
    return ApiError(422, "validation_error", message)


def unavailable(message: str, code: str = "service_unavailable") -> ApiError:
    return ApiError(503, code, message, retryable=True)
