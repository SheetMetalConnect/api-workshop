"""
Enhanced MES Operation Service - Business logic with advanced features.

This enhanced service includes:
- State machine integration
- Advanced filtering and pagination
- Batch operations
- Analytics and reporting
- Time-series data support
"""

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func, desc
from pydantic import BaseModel

from app.services.base_service import BaseService
from app.models.mes_operation import MESOperation
from app.schemas.mes_operation import MESOperationCreate, MESOperationUpdate
from app.crud import mes_operation
from app.domain.operation_state_machine import OperationStateMachine
from app.exceptions.mes_exceptions import (
    DuplicateOperationException,
    InvalidQuantityException,
    InvalidOperationStateException,
    OperationNotFoundException
)

# Import the filters model from the router
class OperationFilters(BaseModel):
    """Advanced filtering options for operations."""
    status: Optional[List[str]] = None
    workplace_name: Optional[str] = None
    workplace_group: Optional[str] = None
    order_priority: Optional[str] = None
    planned_start_after: Optional[datetime] = None
    planned_start_before: Optional[datetime] = None
    has_remaining_qty: Optional[bool] = None
    is_overdue: Optional[bool] = None
    activity_code: Optional[str] = None


class MESOperationServiceEnhanced(BaseService[MESOperation]):
    """
    Enhanced service class for MES Operation business logic.

    Adds advanced features on top of the base service:
    - State machine integration
    - Enhanced filtering and pagination
    - Batch operations
    - Analytics and reporting
    """

    def __init__(self, db: Session):
        super().__init__(db)
        self.state_machine = OperationStateMachine()

    def get_by_id(self, operation_key: Tuple[str, int, str]) -> Optional[MESOperation]:
        """Get operation by composite key (order_no, asset_id, operation_no)."""
        order_no, asset_id, operation_no = operation_key
        return mes_operation.get_operation(self.db, order_no, asset_id, operation_no)

    def get_by_composite_id(self, order_no: str, asset_id: int, operation_no: str) -> Optional[MESOperation]:
        """Alternative method signature for composite key lookup."""
        return self.get_by_id((order_no, asset_id, operation_no))

    def get_operations_paginated(
        self,
        page: int = 1,
        size: int = 50,
        filters: OperationFilters = None
    ) -> Tuple[List[MESOperation], int]:
        """
        Get operations with advanced filtering and pagination.

        Returns:
            Tuple of (operations_list, total_count)
        """
        query = self.db.query(MESOperation)

        # Apply filters
        if filters:
            query = self._apply_filters(query, filters)

        # Get total count before pagination
        total_count = query.count()

        # Apply pagination
        skip = (page - 1) * size
        operations = (
            query
            .order_by(
                MESOperation.order_no,
                MESOperation.asset_id,
                MESOperation.operation_no
            )
            .offset(skip)
            .limit(size)
            .all()
        )

        self._log_operation(
            "Paginated operations fetched",
            {"page": page, "size": size, "total": total_count, "returned": len(operations)}
        )

        return operations, total_count

    def find_operations_by_filters(self, filters: OperationFilters) -> List[MESOperation]:
        """Find operations matching filter criteria (for batch operations)."""
        query = self.db.query(MESOperation)
        query = self._apply_filters(query, filters)
        return query.all()

    def batch_update(
        self,
        filters: OperationFilters,
        updates: MESOperationUpdate
    ) -> Dict[str, Any]:
        """
        Batch update multiple operations based on filter criteria.

        Returns summary of the batch operation.
        """
        matching_operations = self.find_operations_by_filters(filters)

        if not matching_operations:
            return {"count": 0, "summary": "No operations matched the filter criteria"}

        update_dict = updates.model_dump(exclude_unset=True)
        updated_count = 0
        failed_updates = []

        with self.transaction():
            for operation in matching_operations:
                try:
                    # Validate state transitions if status is being updated
                    if "status" in update_dict:
                        self._validate_state_transition(operation.status, update_dict["status"])

                    # Apply updates
                    for field, value in update_dict.items():
                        if hasattr(operation, field):
                            setattr(operation, field, value)

                    updated_count += 1

                except Exception as e:
                    failed_updates.append({
                        "operation_key": f"{operation.order_no}/{operation.asset_id}/{operation.operation_no}",
                        "error": str(e)
                    })

        summary = f"Updated {updated_count} operations"
        if failed_updates:
            summary += f", {len(failed_updates)} failed"

        return {
            "count": updated_count,
            "failed_count": len(failed_updates),
            "summary": summary,
            "failed_operations": failed_updates[:10]  # Return first 10 failures
        }

    def transition_state(
        self,
        order_no: str,
        asset_id: int,
        operation_no: str,
        new_status: str,
        context: Dict[str, Any] = None,
        reason: str = None,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        Execute state transition using the state machine.

        Returns both the updated operation and transition details.
        """
        operation = self.get_by_composite_id(order_no, asset_id, operation_no)
        if not operation:
            raise OperationNotFoundException(order_no, asset_id, operation_no)

        # Prepare context with operation data
        transition_context = context or {}
        transition_context.update({
            "qty_processed": operation.qty_processed or 0,
            "qty_desired": operation.qty_desired or 1,
            "current_status": operation.status
        })

        # Execute state machine transition
        transition_result = self.state_machine.transition(
            from_state=operation.status,
            to_state=new_status,
            context=transition_context,
            user_id=user_id
        )

        # Update the operation
        update_data = MESOperationUpdate(status=new_status)

        # Add automatic timestamp updates based on state
        if new_status == "IN_PROGRESS" and not operation.actual_start_at:
            update_data.actual_start_at = datetime.utcnow()
        elif new_status == "FINISHED" and not operation.actual_end_at:
            update_data.actual_end_at = datetime.utcnow()

        updated_operation = self.update((order_no, asset_id, operation_no), update_data)

        self._log_operation(
            "State transition executed",
            {
                "operation_key": f"{order_no}/{asset_id}/{operation_no}",
                "from_state": operation.status,
                "to_state": new_status,
                "user_id": user_id,
                "reason": reason
            }
        )

        return {
            "operation": updated_operation,
            "transition_result": transition_result
        }

    def get_operations_summary(
        self,
        workplace_name: Optional[str] = None,
        date_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get summary statistics for operations.

        Useful for dashboards and reporting.
        """
        query = self.db.query(MESOperation)

        # Apply workplace filter
        if workplace_name:
            query = query.filter(MESOperation.workplace_name == workplace_name)

        # Apply date filter
        if date_filter:
            now = datetime.utcnow()
            if date_filter == "today":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                query = query.filter(MESOperation.planned_start_at >= start_date)
            elif date_filter == "this_week":
                start_date = now - timedelta(days=now.weekday())
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                query = query.filter(MESOperation.planned_start_at >= start_date)
            elif date_filter == "this_month":
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                query = query.filter(MESOperation.planned_start_at >= start_date)

        # Calculate summary statistics
        all_operations = query.all()

        summary = {
            "total_operations": len(all_operations),
            "by_status": {},
            "by_workplace": {},
            "efficiency_metrics": {},
            "time_metrics": {}
        }

        # Count by status
        for operation in all_operations:
            status = operation.status
            summary["by_status"][status] = summary["by_status"].get(status, 0) + 1

            # Count by workplace
            workplace = operation.workplace_name or "Unknown"
            summary["by_workplace"][workplace] = summary["by_workplace"].get(workplace, 0) + 1

        # Calculate efficiency metrics
        finished_ops = [op for op in all_operations if op.status == "FINISHED"]
        if finished_ops:
            total_planned = sum(op.t_target_processing_min or 0 for op in finished_ops)
            total_actual = sum(op.t_actual_processing_min or 0 for op in finished_ops)

            if total_actual > 0:
                summary["efficiency_metrics"] = {
                    "average_efficiency": (total_planned / total_actual) * 100,
                    "total_planned_minutes": total_planned,
                    "total_actual_minutes": total_actual,
                    "finished_operations": len(finished_ops)
                }

        # Calculate time metrics
        in_progress_ops = [op for op in all_operations if op.status == "IN_PROGRESS"]
        overdue_ops = [
            op for op in all_operations
            if op.planned_end_at and op.planned_end_at < datetime.utcnow() and op.status != "FINISHED"
        ]

        summary["time_metrics"] = {
            "in_progress_count": len(in_progress_ops),
            "overdue_count": len(overdue_ops),
            "overdue_percentage": (len(overdue_ops) / len(all_operations) * 100) if all_operations else 0
        }

        return summary

    def create(self, operation_data: MESOperationCreate) -> MESOperation:
        """Create new operation with state machine validation."""
        # Validate initial state
        initial_status = getattr(operation_data, 'status', 'PLANNED')
        if initial_status not in ['PLANNED', 'RELEASED']:
            raise InvalidOperationStateException(
                initial_status, "create operation with invalid initial state"
            )

        return super().create(operation_data)

    def update(
        self,
        order_no: str,
        asset_id: int,
        operation_no: str,
        update_data: MESOperationUpdate
    ) -> Optional[MESOperation]:
        """Update operation with enhanced validation."""
        operation_key = (order_no, asset_id, operation_no)
        return super().update(operation_key, update_data)

    def delete(self, order_no: str, asset_id: int, operation_no: str) -> bool:
        """Delete operation with enhanced validation."""
        operation_key = (order_no, asset_id, operation_no)
        return super().delete(operation_key)

    def _apply_filters(self, query, filters: OperationFilters):
        """Apply advanced filters to the query."""
        if filters.status:
            query = query.filter(MESOperation.status.in_(filters.status))

        if filters.workplace_name:
            query = query.filter(MESOperation.workplace_name == filters.workplace_name)

        if filters.workplace_group:
            # Assuming workplace_group is derived from workplace_name pattern
            query = query.filter(MESOperation.workplace_name.like(f"{filters.workplace_group}%"))

        if filters.activity_code:
            query = query.filter(MESOperation.activity_code == filters.activity_code)

        if filters.planned_start_after:
            query = query.filter(MESOperation.planned_start_at >= filters.planned_start_after)

        if filters.planned_start_before:
            query = query.filter(MESOperation.planned_start_at <= filters.planned_start_before)

        if filters.has_remaining_qty is not None:
            if filters.has_remaining_qty:
                query = query.filter(
                    or_(
                        MESOperation.qty_processed < MESOperation.qty_desired,
                        MESOperation.qty_processed.is_(None)
                    )
                )
            else:
                query = query.filter(MESOperation.qty_processed >= MESOperation.qty_desired)

        if filters.is_overdue is not None:
            now = datetime.utcnow()
            if filters.is_overdue:
                query = query.filter(
                    and_(
                        MESOperation.planned_end_at < now,
                        MESOperation.status != "FINISHED"
                    )
                )
            else:
                query = query.filter(
                    or_(
                        MESOperation.planned_end_at >= now,
                        MESOperation.status == "FINISHED"
                    )
                )

        return query

    def _validate_state_transition(self, current_status: str, new_status: str):
        """Enhanced state transition validation using state machine."""
        if not self.state_machine.can_transition(current_status, new_status):
            valid_transitions = self.state_machine.get_valid_transitions(current_status)
            raise InvalidOperationStateException(
                current_status,
                f"transition to {new_status}. Valid transitions: {valid_transitions}"
            )


# Alias for backward compatibility
MESOperationService = MESOperationServiceEnhanced