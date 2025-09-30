"""
Global exception handlers for the MES API.

This module provides centralized error handling, logging, and response formatting
for all exceptions across the application.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, TimeoutError as SQLTimeoutError
from pydantic import ValidationError
import logging
from typing import Dict, Any
import traceback

from app.exceptions.mes_exceptions import MESOperationException

logger = logging.getLogger(__name__)


class ErrorResponse:
    """Standardized error response format."""

    def __init__(
        self,
        error_type: str,
        message: str,
        details: Dict[str, Any] = None,
        request_id: str = None
    ):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        self.request_id = request_id

    def to_dict(self) -> Dict[str, Any]:
        response = {
            "error": {
                "type": self.error_type,
                "message": self.message,
                "timestamp": self._get_timestamp()
            }
        }

        if self.details:
            response["error"]["details"] = self.details

        if self.request_id:
            response["error"]["request_id"] = self.request_id

        return response

    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"


def create_error_response(
    error_type: str,
    message: str,
    status_code: int,
    details: Dict[str, Any] = None,
    request: Request = None
) -> JSONResponse:
    """Create standardized error response."""
    request_id = getattr(request.state, 'request_id', None) if request else None

    error_response = ErrorResponse(
        error_type=error_type,
        message=message,
        details=details,
        request_id=request_id
    )

    return JSONResponse(
        status_code=status_code,
        content=error_response.to_dict()
    )


async def mes_operation_exception_handler(request: Request, exc: MESOperationException):
    """Handle all MES operation-specific exceptions."""
    logger.warning(f"MES operation error: {exc.error_type} - {exc.message}")

    # Map error types to HTTP status codes
    status_code_map = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "duplicate_operation": status.HTTP_409_CONFLICT,
        "invalid_state_transition": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "invalid_quantity": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "integrity_violation": status.HTTP_400_BAD_REQUEST,
        "general_error": status.HTTP_500_INTERNAL_SERVER_ERROR
    }

    status_code = status_code_map.get(exc.error_type, status.HTTP_500_INTERNAL_SERVER_ERROR)

    return create_error_response(
        error_type=exc.error_type,
        message=exc.message,
        status_code=status_code,
        request=request
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database integrity constraint violations."""
    logger.error(f"Database integrity error: {str(exc)}")

    # Extract more specific error information from the database error
    error_details = {
        "database_error": str(exc.orig) if hasattr(exc, 'orig') else str(exc)
    }

    return create_error_response(
        error_type="database_constraint_violation",
        message="The operation violates database constraints",
        status_code=status.HTTP_400_BAD_REQUEST,
        details=error_details,
        request=request
    )


async def database_timeout_handler(request: Request, exc: SQLTimeoutError):
    """Handle database timeout errors."""
    logger.error(f"Database timeout: {str(exc)}")

    return create_error_response(
        error_type="database_timeout",
        message="Database operation timed out. Please try again.",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        request=request
    )


async def database_operational_error_handler(request: Request, exc: OperationalError):
    """Handle database operational errors."""
    logger.error(f"Database operational error: {str(exc)}")

    return create_error_response(
        error_type="database_error",
        message="Database service temporarily unavailable",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        request=request
    )


async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    logger.warning(f"Validation error: {str(exc)}")

    # Format validation errors for better user experience
    validation_details = []
    for error in exc.errors():
        validation_details.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    return create_error_response(
        error_type="validation_error",
        message="Request validation failed",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details={"validation_errors": validation_details},
        request=request
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

    # In production, don't expose internal error details
    import os
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"

    details = {}
    if debug_mode:
        details = {
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc()
        }

    return create_error_response(
        error_type="internal_server_error",
        message="An unexpected error occurred. Please contact support if the problem persists.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details=details if debug_mode else None,
        request=request
    )


# Exception handler registry for easy registration
EXCEPTION_HANDLERS = {
    MESOperationException: mes_operation_exception_handler,
    IntegrityError: integrity_error_handler,
    SQLTimeoutError: database_timeout_handler,
    OperationalError: database_operational_error_handler,
    ValidationError: validation_error_handler,
    Exception: general_exception_handler,  # Catch-all handler
}