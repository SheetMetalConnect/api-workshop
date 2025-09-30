"""
Base service class providing common functionality for all services.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging
from contextlib import contextmanager
from app.exceptions.mes_exceptions import MESOperationException

T = TypeVar('T')
logger = logging.getLogger(__name__)


class BaseService(ABC, Generic[T]):
    """
    Abstract base service providing common patterns for business logic.

    This class provides:
    - Transaction management
    - Error handling patterns
    - Logging standardization
    - Common CRUD operations interface
    """

    def __init__(self, db: Session):
        self.db = db
        self._logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")

    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions with automatic rollback on failure.

        Usage:
            with service.transaction():
                # Multiple database operations
                service.some_operation()
                service.another_operation()
                # Automatically commits if no exceptions
        """
        try:
            yield
            self.db.commit()
            self._logger.debug("Transaction committed successfully")
        except Exception as e:
            self.db.rollback()
            self._logger.error(f"Transaction rolled back due to error: {str(e)}")
            raise

    def _log_operation(self, operation: str, details: Dict[str, Any] = None):
        """Standard logging for service operations."""
        if details:
            self._logger.info(f"{operation}: {details}")
        else:
            self._logger.info(operation)

    def _handle_integrity_error(self, error: IntegrityError, context: str = "database operation"):
        """Standard handling for database integrity violations."""
        self._logger.error(f"Integrity error in {context}: {str(error)}")
        raise MESOperationException(
            f"Database constraint violation during {context}",
            error_type="integrity_violation"
        )

    @abstractmethod
    def get_by_id(self, entity_id: Any) -> Optional[T]:
        """Get entity by ID - must be implemented by subclasses."""
        pass

    @abstractmethod
    def create(self, entity_data: Any) -> T:
        """Create new entity - must be implemented by subclasses."""
        pass

    @abstractmethod
    def update(self, entity_id: Any, update_data: Any) -> Optional[T]:
        """Update entity - must be implemented by subclasses."""
        pass

    @abstractmethod
    def delete(self, entity_id: Any) -> bool:
        """Delete entity - must be implemented by subclasses."""
        pass