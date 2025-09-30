"""
MES Operation Service - Business logic for manufacturing operations.

This service encapsulates all business rules and workflows related to
manufacturing operations, including state transitions, quantity validation,
and time calculations.
"""

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.services.base_service import BaseService
from app.models.mes_operation import MESOperation
from app.schemas.mes_operation import MESOperationCreate, MESOperationUpdate
from app.crud import mes_operation
from app.exceptions.mes_exceptions import (
    DuplicateOperationException,
    InvalidQuantityException,
    InvalidOperationStateException,
    OperationNotFoundException
)


class MESOperationService(BaseService[MESOperation]):
    """
    Service class for MES Operation business logic.

    Handles:
    - Operation lifecycle management
    - State transition validation
    - Quantity and time validations
    - Manufacturing business rules
    - Performance calculations
    """

    # Valid state transitions for manufacturing operations
    VALID_STATE_TRANSITIONS = {
        "PLANNED": ["RELEASED", "CANCELLED"],
        "RELEASED": ["IN_PROGRESS", "CANCELLED", "ON_HOLD"],
        "IN_PROGRESS": ["FINISHED", "ON_HOLD", "CANCELLED"],
        "ON_HOLD": ["IN_PROGRESS", "CANCELLED"],
        "FINISHED": [],  # Terminal state
        "CANCELLED": []  # Terminal state
    }

    def __init__(self, db: Session):
        super().__init__(db)

    def get_by_id(self, operation_key: Tuple[str, int, str]) -> Optional[MESOperation]:
        """Get operation by composite key (order_no, asset_id, operation_no)."""
        order_no, asset_id, operation_no = operation_key
        return mes_operation.get_operation(self.db, order_no, asset_id, operation_no)

    def get_operations(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        workplace_name: Optional[str] = None
    ) -> List[MESOperation]:
        """Get operations with filtering and pagination."""
        self._log_operation(
            "Fetching operations",
            {"skip": skip, "limit": limit, "status": status, "workplace": workplace_name}
        )
        return mes_operation.get_operations(
            self.db, skip=skip, limit=limit, status=status, workplace_name=workplace_name
        )

    def create(self, operation_data: MESOperationCreate) -> MESOperation:
        """
        Create new operation with business rule validation.

        Validates:
        - No duplicate operations
        - Quantity constraints
        - Time constraints
        - Initial state validity
        """
        operation_key = (operation_data.order_no, operation_data.asset_id, operation_data.operation_no)

        self._log_operation("Creating operation", {"key": operation_key})

        # Check for duplicates
        existing = self.get_by_id(operation_key)
        if existing:
            raise DuplicateOperationException(
                operation_data.order_no, operation_data.asset_id, operation_data.operation_no
            )

        # Validate business rules
        self._validate_operation_data(operation_data)

        try:
            with self.transaction():
                created = mes_operation.create_operation(self.db, operation_data)
                self._log_operation("Operation created", {"key": operation_key, "status": created.status})
                return created
        except IntegrityError as e:
            self._handle_integrity_error(e, "operation creation")

    def update(
        self,
        operation_key: Tuple[str, int, str],
        update_data: MESOperationUpdate
    ) -> Optional[MESOperation]:
        """
        Update operation with state transition and business rule validation.
        """
        order_no, asset_id, operation_no = operation_key

        self._log_operation("Updating operation", {"key": operation_key})

        existing = self.get_by_id(operation_key)
        if not existing:
            raise OperationNotFoundException(order_no, asset_id, operation_no)

        # Validate state transitions
        update_dict = update_data.model_dump(exclude_unset=True)
        if "status" in update_dict:
            self._validate_state_transition(existing.status, update_dict["status"])

        # Validate quantities
        self._validate_quantities_update(existing, update_dict)

        try:
            with self.transaction():
                updated = mes_operation.update_operation(
                    self.db, order_no, asset_id, operation_no, update_data
                )
                self._log_operation(
                    "Operation updated",
                    {"key": operation_key, "fields": list(update_dict.keys())}
                )
                return updated
        except IntegrityError as e:
            self._handle_integrity_error(e, "operation update")

    def delete(self, operation_key: Tuple[str, int, str]) -> bool:
        """Delete operation with validation."""
        order_no, asset_id, operation_no = operation_key

        self._log_operation("Deleting operation", {"key": operation_key})

        existing = self.get_by_id(operation_key)
        if not existing:
            return False

        # Business rule: Can't delete finished operations
        if existing.status == "FINISHED":
            raise InvalidOperationStateException(
                existing.status, "delete finished operation"
            )

        try:
            with self.transaction():
                deleted = mes_operation.delete_operation(self.db, order_no, asset_id, operation_no)
                if deleted:
                    self._log_operation("Operation deleted", {"key": operation_key})
                return deleted
        except IntegrityError as e:
            self._handle_integrity_error(e, "operation deletion")

    def start_operation(self, operation_key: Tuple[str, int, str]) -> MESOperation:
        """Start an operation (business workflow method)."""
        order_no, asset_id, operation_no = operation_key

        operation = self.get_by_id(operation_key)
        if not operation:
            raise OperationNotFoundException(order_no, asset_id, operation_no)

        if operation.status not in ["RELEASED", "ON_HOLD"]:
            raise InvalidOperationStateException(operation.status, "start operation")

        update_data = MESOperationUpdate(
            status="IN_PROGRESS",
            actual_start_at=datetime.utcnow(),
            timestamp_ms=datetime.utcnow(),
            change_type="UPDATE"
        )

        return self.update(operation_key, update_data)

    def finish_operation(
        self,
        operation_key: Tuple[str, int, str],
        final_quantity: Optional[int] = None
    ) -> MESOperation:
        """Finish an operation (business workflow method)."""
        order_no, asset_id, operation_no = operation_key

        operation = self.get_by_id(operation_key)
        if not operation:
            raise OperationNotFoundException(order_no, asset_id, operation_no)

        if operation.status != "IN_PROGRESS":
            raise InvalidOperationStateException(operation.status, "finish operation")

        update_dict = {
            "status": "FINISHED",
            "actual_end_at": datetime.utcnow(),
            "timestamp_ms": datetime.utcnow(),
            "change_type": "UPDATE"
        }

        if final_quantity is not None:
            update_dict["qty_processed"] = final_quantity

        update_data = MESOperationUpdate(**update_dict)
        return self.update(operation_key, update_data)

    def calculate_efficiency(self, operation: MESOperation) -> Optional[float]:
        """Calculate operation efficiency based on actual vs target times."""
        if not operation.t_actual_processing_min or not operation.t_target_processing_min:
            return None

        if operation.t_target_processing_min == 0:
            return None

        efficiency = float(operation.t_target_processing_min) / float(operation.t_actual_processing_min)
        return min(efficiency, 2.0)  # Cap at 200% efficiency

    def _validate_operation_data(self, operation_data: MESOperationCreate):
        """Validate business rules for operation creation."""
        # Quantity validation
        if operation_data.qty_processed and operation_data.qty_desired:
            if operation_data.qty_processed > operation_data.qty_desired:
                raise InvalidQuantityException(
                    f"Processed quantity ({operation_data.qty_processed}) cannot exceed desired quantity ({operation_data.qty_desired})"
                )

        # Time validation
        if operation_data.planned_start_at and operation_data.planned_end_at:
            if operation_data.planned_start_at >= operation_data.planned_end_at:
                raise InvalidOperationStateException(
                    "time_validation", "Planned start time must be before end time"
                )

    def _validate_state_transition(self, current_status: str, new_status: str):
        """Validate if state transition is allowed."""
        if current_status == new_status:
            return  # No change

        valid_next_states = self.VALID_STATE_TRANSITIONS.get(current_status, [])
        if new_status not in valid_next_states:
            raise InvalidOperationStateException(
                current_status, f"transition to {new_status}"
            )

    def _validate_quantities_update(self, existing: MESOperation, update_dict: Dict[str, Any]):
        """Validate quantity constraints during updates."""
        new_qty_processed = update_dict.get("qty_processed", existing.qty_processed)
        new_qty_desired = update_dict.get("qty_desired", existing.qty_desired)
        new_qty_scrap = update_dict.get("qty_scrap", existing.qty_scrap)

        if new_qty_processed and new_qty_desired and new_qty_processed > new_qty_desired:
            raise InvalidQuantityException(
                f"Processed quantity ({new_qty_processed}) cannot exceed desired quantity ({new_qty_desired})"
            )

        if new_qty_scrap and new_qty_processed and new_qty_scrap > new_qty_processed:
            raise InvalidQuantityException(
                f"Scrap quantity ({new_qty_scrap}) cannot exceed processed quantity ({new_qty_processed})"
            )