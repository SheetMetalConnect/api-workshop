"""
Enhanced MES Operations Router with HATEOAS, State Machine Integration,
Advanced Pagination, and Service Layer Architecture.

This router demonstrates:
- HATEOAS implementation for manufacturing workflows
- State machine-driven operation transitions
- Service layer for business logic encapsulation
- Enhanced pagination and filtering
- Batch operations for efficiency
- REST Level 3 compliance
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union
import logging
from datetime import datetime
from urllib.parse import urlencode

from app.database import get_db
from app.schemas.mes_operation import (
    MESOperation,
    MESOperationCreate,
    MESOperationUpdate,
)
from app.services.mes_operation_service import MESOperationService
from app.domain.operation_state_machine import OperationStateMachine
from app.exceptions.mes_exceptions import MESOperationException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


# Enhanced Response Models with HATEOAS
class Link(BaseModel):
    """HATEOAS link representation."""
    href: str
    method: str = "GET"
    rel: str
    title: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None


class MESOperationWithLinks(MESOperation):
    """MES Operation with HATEOAS links."""
    _links: Dict[str, Link] = Field(default_factory=dict)


class PaginationInfo(BaseModel):
    """Enhanced pagination information."""
    page: int = Field(ge=1)
    size: int = Field(ge=1, le=500)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    has_next: bool
    has_previous: bool


class PaginatedResponse(BaseModel):
    """Paginated response with HATEOAS navigation."""
    items: List[MESOperationWithLinks]
    pagination: PaginationInfo
    _links: Dict[str, Link] = Field(default_factory=dict)


class OperationFilters(BaseModel):
    """Advanced filtering options for operations."""
    status: Optional[List[str]] = Field(None, description="Filter by operation status")
    workplace_name: Optional[str] = Field(None, description="Filter by workplace")
    workplace_group: Optional[str] = Field(None, description="Filter by workplace group")
    order_priority: Optional[str] = Field(None, description="Filter by order priority")
    planned_start_after: Optional[datetime] = Field(None, description="Operations planned after this date")
    planned_start_before: Optional[datetime] = Field(None, description="Operations planned before this date")
    has_remaining_qty: Optional[bool] = Field(None, description="Operations with remaining quantity")
    is_overdue: Optional[bool] = Field(None, description="Operations past their planned end time")
    activity_code: Optional[str] = Field(None, description="Filter by activity code")


class BatchUpdateRequest(BaseModel):
    """Batch update request for multiple operations."""
    filters: OperationFilters = Field(description="Criteria to select operations")
    updates: MESOperationUpdate = Field(description="Updates to apply")
    dry_run: bool = Field(False, description="Preview changes without applying")


class StateTransitionRequest(BaseModel):
    """Request to transition operation state."""
    new_status: str = Field(description="Target status")
    reason: Optional[str] = Field(None, description="Reason for state change")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


# Dependency to get service layer
def get_operation_service(db: Session = Depends(get_db)) -> MESOperationService:
    """Get MES Operation service instance."""
    return MESOperationService(db)


def get_state_machine() -> OperationStateMachine:
    """Get state machine instance."""
    return OperationStateMachine()


def add_hateoas_links(
    operation: MESOperation,
    request: Request,
    state_machine: OperationStateMachine
) -> MESOperationWithLinks:
    """Add HATEOAS links to an operation based on current state and permissions."""
    base_url = str(request.base_url).rstrip('/')
    operation_path = f"/api/v1/operations/{operation.order_no}/{operation.asset_id}/{operation.operation_no}"

    # Convert to enhanced model
    enhanced_op = MESOperationWithLinks(**operation.__dict__)

    # Self link
    enhanced_op._links["self"] = Link(
        href=f"{base_url}{operation_path}",
        method="GET",
        rel="self",
        title="Get operation details"
    )

    # Update link
    enhanced_op._links["update"] = Link(
        href=f"{base_url}{operation_path}",
        method="PATCH",
        rel="edit",
        title="Update operation",
        schema={
            "type": "object",
            "properties": {
                "qty_processed": {"type": "number"},
                "qty_scrap": {"type": "number"},
                "actual_start_at": {"type": "string", "format": "date-time"},
                "actual_end_at": {"type": "string", "format": "date-time"},
                "notes": {"type": "string"}
            }
        }
    )

    # Delete link (if not in terminal state)
    if not state_machine.is_terminal_state(operation.status):
        enhanced_op._links["delete"] = Link(
            href=f"{base_url}{operation_path}",
            method="DELETE",
            rel="delete",
            title="Delete operation"
        )

    # State transition links
    valid_transitions = state_machine.get_valid_transitions(operation.status)
    for next_state in valid_transitions:
        relation = f"transition-to-{next_state.lower()}"
        enhanced_op._links[relation] = Link(
            href=f"{base_url}{operation_path}/transitions",
            method="POST",
            rel=relation,
            title=f"Transition to {next_state}",
            schema={
                "type": "object",
                "properties": {
                    "new_status": {"type": "string", "enum": [next_state]},
                    "reason": {"type": "string"},
                    "context": {"type": "object"}
                },
                "required": ["new_status"]
            }
        )

    # Related resources
    enhanced_op._links["events"] = Link(
        href=f"{base_url}/api/v1/events?order_no={operation.order_no}&asset_id={operation.asset_id}&operation_no={operation.operation_no}",
        method="GET",
        rel="related",
        title="Get operation events"
    )

    # Manufacturing-specific actions
    if operation.status == "RELEASED":
        enhanced_op._links["start"] = Link(
            href=f"{base_url}{operation_path}/start",
            method="POST",
            rel="action",
            title="Start operation"
        )
    elif operation.status == "IN_PROGRESS":
        enhanced_op._links["finish"] = Link(
            href=f"{base_url}{operation_path}/finish",
            method="POST",
            rel="action",
            title="Finish operation"
        )
        enhanced_op._links["pause"] = Link(
            href=f"{base_url}{operation_path}/pause",
            method="POST",
            rel="action",
            title="Pause operation"
        )

    return enhanced_op


def add_pagination_links(
    request: Request,
    page: int,
    size: int,
    total_items: int,
    filters: Dict[str, Any] = None
) -> Dict[str, Link]:
    """Add pagination navigation links."""
    base_url = str(request.base_url).rstrip('/')
    path = str(request.url.path)

    total_pages = (total_items + size - 1) // size
    links = {}

    # Build query parameters
    query_params = {"page": page, "size": size}
    if filters:
        query_params.update({k: v for k, v in filters.items() if v is not None})

    # Self link
    links["self"] = Link(
        href=f"{base_url}{path}?{urlencode(query_params)}",
        rel="self",
        title="Current page"
    )

    # First page
    if page > 1:
        first_params = {**query_params, "page": 1}
        links["first"] = Link(
            href=f"{base_url}{path}?{urlencode(first_params)}",
            rel="first",
            title="First page"
        )

    # Previous page
    if page > 1:
        prev_params = {**query_params, "page": page - 1}
        links["prev"] = Link(
            href=f"{base_url}{path}?{urlencode(prev_params)}",
            rel="prev",
            title="Previous page"
        )

    # Next page
    if page < total_pages:
        next_params = {**query_params, "page": page + 1}
        links["next"] = Link(
            href=f"{base_url}{path}?{urlencode(next_params)}",
            rel="next",
            title="Next page"
        )

    # Last page
    if page < total_pages:
        last_params = {**query_params, "page": total_pages}
        links["last"] = Link(
            href=f"{base_url}{path}?{urlencode(last_params)}",
            rel="last",
            title="Last page"
        )

    return links


@router.get("/", response_model=PaginatedResponse, status_code=status.HTTP_200_OK)
async def list_operations(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=500, description="Items per page"),
    status_filter: Optional[List[str]] = Query(None, alias="status"),
    workplace_name: Optional[str] = None,
    workplace_group: Optional[str] = None,
    planned_start_after: Optional[datetime] = None,
    planned_start_before: Optional[datetime] = None,
    has_remaining_qty: Optional[bool] = None,
    is_overdue: Optional[bool] = None,
    activity_code: Optional[str] = None,
    service: MESOperationService = Depends(get_operation_service),
    state_machine: OperationStateMachine = Depends(get_state_machine)
):
    """
    List operations with advanced filtering, pagination, and HATEOAS links.

    Supports:
    - Flexible pagination (page-based)
    - Multiple filter criteria
    - HATEOAS navigation
    - Manufacturing-specific filters
    """
    filters = OperationFilters(
        status=status_filter,
        workplace_name=workplace_name,
        workplace_group=workplace_group,
        planned_start_after=planned_start_after,
        planned_start_before=planned_start_before,
        has_remaining_qty=has_remaining_qty,
        is_overdue=is_overdue,
        activity_code=activity_code
    )

    # Get paginated results from service
    operations, total_count = service.get_operations_paginated(
        page=page,
        size=size,
        filters=filters
    )

    # Add HATEOAS links to each operation
    enhanced_operations = [
        add_hateoas_links(op, request, state_machine)
        for op in operations
    ]

    # Build pagination info
    total_pages = (total_count + size - 1) // size
    pagination = PaginationInfo(
        page=page,
        size=size,
        total_items=total_count,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )

    # Add pagination links
    filter_dict = filters.model_dump(exclude_unset=True)
    pagination_links = add_pagination_links(request, page, size, total_count, filter_dict)

    return PaginatedResponse(
        items=enhanced_operations,
        pagination=pagination,
        _links=pagination_links
    )


@router.get("/{order_no}/{asset_id}/{operation_no}", response_model=MESOperationWithLinks)
async def get_operation(
    request: Request,
    order_no: str = Path(...),
    asset_id: int = Path(..., gt=0),
    operation_no: str = Path(...),
    service: MESOperationService = Depends(get_operation_service),
    state_machine: OperationStateMachine = Depends(get_state_machine)
):
    """Get a specific operation with HATEOAS links for available actions."""
    operation = service.get_by_composite_id(order_no, asset_id, operation_no)
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"Operation not found: {order_no}/{asset_id}/{operation_no}",
            },
        )

    return add_hateoas_links(operation, request, state_machine)


@router.post("/", response_model=MESOperationWithLinks, status_code=status.HTTP_201_CREATED)
async def create_operation(
    request: Request,
    operation: MESOperationCreate,
    response: Response,
    service: MESOperationService = Depends(get_operation_service),
    state_machine: OperationStateMachine = Depends(get_state_machine)
):
    """Create a new operation with immediate HATEOAS links for next actions."""
    created = service.create(operation)

    # Set Location header
    location = f"/api/v1/operations/{created.order_no}/{created.asset_id}/{created.operation_no}"
    response.headers["Location"] = location

    return add_hateoas_links(created, request, state_machine)


@router.patch("/{order_no}/{asset_id}/{operation_no}", response_model=MESOperationWithLinks)
async def update_operation(
    request: Request,
    order_no: str = Path(...),
    asset_id: int = Path(..., gt=0),
    operation_no: str = Path(...),
    operation_update: MESOperationUpdate,
    service: MESOperationService = Depends(get_operation_service),
    state_machine: OperationStateMachine = Depends(get_state_machine)
):
    """Update an operation with state validation and HATEOAS response."""
    updated = service.update(order_no, asset_id, operation_no, operation_update)
    return add_hateoas_links(updated, request, state_machine)


@router.delete("/{order_no}/{asset_id}/{operation_no}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_operation(
    order_no: str = Path(...),
    asset_id: int = Path(..., gt=0),
    operation_no: str = Path(...),
    service: MESOperationService = Depends(get_operation_service)
):
    """Delete an operation if allowed by business rules."""
    service.delete(order_no, asset_id, operation_no)
    return None


@router.post("/{order_no}/{asset_id}/{operation_no}/transitions",
             response_model=Dict[str, Any])
async def transition_operation_state(
    order_no: str = Path(...),
    asset_id: int = Path(..., gt=0),
    operation_no: str = Path(...),
    transition_request: StateTransitionRequest,
    service: MESOperationService = Depends(get_operation_service),
    state_machine: OperationStateMachine = Depends(get_state_machine)
):
    """Execute a state transition using the manufacturing state machine."""
    result = service.transition_state(
        order_no=order_no,
        asset_id=asset_id,
        operation_no=operation_no,
        new_status=transition_request.new_status,
        context=transition_request.context,
        reason=transition_request.reason
    )

    return {
        "transition_executed": True,
        "operation": result["operation"],
        "transition_details": result["transition_result"],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/{order_no}/{asset_id}/{operation_no}/start",
             response_model=MESOperationWithLinks)
async def start_operation(
    request: Request,
    order_no: str = Path(...),
    asset_id: int = Path(..., gt=0),
    operation_no: str = Path(...),
    service: MESOperationService = Depends(get_operation_service),
    state_machine: OperationStateMachine = Depends(get_state_machine)
):
    """Convenience endpoint to start an operation (RELEASED -> IN_PROGRESS)."""
    result = service.transition_state(
        order_no=order_no,
        asset_id=asset_id,
        operation_no=operation_no,
        new_status="IN_PROGRESS",
        context={"action": "start", "timestamp": datetime.utcnow().isoformat()}
    )

    return add_hateoas_links(result["operation"], request, state_machine)


@router.post("/{order_no}/{asset_id}/{operation_no}/finish",
             response_model=MESOperationWithLinks)
async def finish_operation(
    request: Request,
    order_no: str = Path(...),
    asset_id: int = Path(..., gt=0),
    operation_no: str = Path(...),
    service: MESOperationService = Depends(get_operation_service),
    state_machine: OperationStateMachine = Depends(get_state_machine)
):
    """Convenience endpoint to finish an operation (IN_PROGRESS -> FINISHED)."""
    result = service.transition_state(
        order_no=order_no,
        asset_id=asset_id,
        operation_no=operation_no,
        new_status="FINISHED",
        context={"action": "finish", "timestamp": datetime.utcnow().isoformat()}
    )

    return add_hateoas_links(result["operation"], request, state_machine)


@router.post("/batch", response_model=Dict[str, Any])
async def batch_update_operations(
    batch_request: BatchUpdateRequest,
    service: MESOperationService = Depends(get_operation_service)
):
    """
    Batch update multiple operations based on filter criteria.

    Supports dry-run mode to preview changes before applying.
    """
    if batch_request.dry_run:
        # Preview mode - show what would be updated
        matching_ops = service.find_operations_by_filters(batch_request.filters)
        return {
            "dry_run": True,
            "matching_operations": len(matching_ops),
            "operations_preview": [
                {
                    "order_no": op.order_no,
                    "asset_id": op.asset_id,
                    "operation_no": op.operation_no,
                    "current_status": op.status,
                    "workplace_name": op.workplace_name
                }
                for op in matching_ops[:10]  # Show first 10
            ],
            "would_update": batch_request.updates.model_dump(exclude_unset=True)
        }
    else:
        # Execute batch update
        result = service.batch_update(batch_request.filters, batch_request.updates)
        return {
            "dry_run": False,
            "operations_updated": result["count"],
            "timestamp": datetime.utcnow().isoformat(),
            "summary": result["summary"]
        }


@router.get("/summary", response_model=Dict[str, Any])
async def get_operations_summary(
    workplace_name: Optional[str] = None,
    date_filter: Optional[str] = Query(None, description="today, this_week, this_month"),
    service: MESOperationService = Depends(get_operation_service)
):
    """Get summary statistics for operations, useful for dashboards."""
    summary = service.get_operations_summary(
        workplace_name=workplace_name,
        date_filter=date_filter
    )

    return {
        "summary": summary,
        "generated_at": datetime.utcnow().isoformat(),
        "filters_applied": {
            "workplace_name": workplace_name,
            "date_filter": date_filter
        }
    }