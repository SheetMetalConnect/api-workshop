"""
Custom exceptions for MES API operations.
These exceptions map to specific HTTP status codes for clear API responses.
"""


class MESOperationException(Exception):
    """Base exception for all MES operation errors"""

    def __init__(self, message: str, error_type: str = "general_error"):
        self.message = message
        self.error_type = error_type
        super().__init__(self.message)


class OperationNotFoundException(MESOperationException):
    """Raised when an operation cannot be found (404)"""

    def __init__(self, order_no: str, asset_id: int, operation_no: str):
        message = f"Operation not found: {order_no}/{asset_id}/{operation_no}"
        super().__init__(message, "not_found")


class DuplicateOperationException(MESOperationException):
    """Raised when trying to create an operation that already exists (409)"""

    def __init__(self, order_no: str, asset_id: int, operation_no: str):
        message = f"Operation already exists: {order_no}/{asset_id}/{operation_no}"
        super().__init__(message, "duplicate_operation")


class InvalidOperationStateException(MESOperationException):
    """Raised when operation state transition is invalid (422)"""

    def __init__(self, current_status: str, attempted_action: str):
        message = f"Cannot {attempted_action} operation with status '{current_status}'"
        super().__init__(message, "invalid_state_transition")


class InvalidQuantityException(MESOperationException):
    """Raised when quantities don't make sense (422)"""

    def __init__(self, message: str):
        super().__init__(message, "invalid_quantity")
