"""
Enhanced MES Operations Router using Service Layer.

This router demonstrates the improved architecture with:
- Service layer integration
- Dependency injection
- Standardized error handling
- Better separation of concerns
"""

from fastapi import APIRouter, Depends, Query, Path, Response, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.database import get_db
from app.schemas.mes_operation import (
    MESOperation,
    MESOperationCreate,
    MESOperationUpdate,
)
from app.services.mes_operation_service import MESOperationService
from app.exceptions.mes_exceptions import OperationNotFoundException

logger = logging.getLogger(__name__)


def get_mes_operation_service(db: Session = Depends(get_db)) -> MESOperationService:
    """Dependency injection for MES Operation Service."""
    return MESOperationService(db)


router = APIRouter()


@router.get("/", response_model=List[MESOperation])
async def list_operations(
    request: Request,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Number of records to return"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by operation status"),
    workplace_name: Optional[str] = Query(None, description="Filter by workplace name"),
    service: MESOperationService = Depends(get_mes_operation_service),
):
    """
    List MES operations with filtering and pagination.

    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return
    - **status**: Filter operations by status (PLANNED, RELEASED, IN_PROGRESS, etc.)
    - **workplace_name**: Filter operations by workplace/machine name
    """
    logger.info(
        f"Listing operations: skip={skip}, limit={limit}, status={status_filter}, workplace={workplace_name}",
        extra={"request_id": getattr(request.state, 'request_id', None)}
    )

    return service.get_operations(
        skip=skip,
        limit=limit,
        status=status_filter,
        workplace_name=workplace_name
    )


@router.get("/{order_no}/{asset_id}/{operation_no}", response_model=MESOperation)
async def get_operation(
    request: Request,
    order_no: str = Path(..., description="Work order number"),
    asset_id: int = Path(..., gt=0, description="Asset/machine ID"),
    operation_no: str = Path(..., description="Operation sequence number"),
    service: MESOperationService = Depends(get_mes_operation_service),
):
    """
    Get a specific MES operation by its composite key.

    The operation is identified by the combination of:
    - **order_no**: Work order number (e.g., '403860-001')
    - **asset_id**: Asset/machine ID (positive integer)
    - **operation_no**: Operation sequence number (e.g., '0010', '0020')
    """
    operation_key = (order_no, asset_id, operation_no)

    logger.info(
        f"Getting operation: {operation_key}",
        extra={"request_id": getattr(request.state, 'request_id', None)}
    )

    operation = service.get_by_id(operation_key)
    if not operation:
        raise OperationNotFoundException(order_no, asset_id, operation_no)

    return operation


@router.post("/", response_model=MESOperation, status_code=201)
async def create_operation(
    request: Request,
    operation: MESOperationCreate,
    response: Response,
    service: MESOperationService = Depends(get_mes_operation_service),
):
    """
    Create a new MES operation.

    The operation will be validated for:
    - Uniqueness (no duplicate operations)
    - Quantity constraints
    - Time constraints
    - Valid initial state
    """
    logger.info(
        f"Creating operation: {operation.order_no}/{operation.asset_id}/{operation.operation_no}",
        extra={"request_id": getattr(request.state, 'request_id', None)}
    )

    created = service.create(operation)

    # Set Location header for the created resource
    response.headers["Location"] = (
        f"/api/v1/operations/{created.order_no}/{created.asset_id}/{created.operation_no}"
    )

    return created


@router.patch("/{order_no}/{asset_id}/{operation_no}", response_model=MESOperation)
async def update_operation(
    request: Request,
    order_no: str = Path(..., description="Work order number"),
    asset_id: int = Path(..., gt=0, description="Asset/machine ID"),
    operation_no: str = Path(..., description="Operation sequence number"),
    operation_update: MESOperationUpdate = ...,
    service: MESOperationService = Depends(get_mes_operation_service),
):
    """
    Update an existing MES operation.

    Supports partial updates. The operation will be validated for:
    - Valid state transitions
    - Quantity constraints
    - Business rule compliance
    """
    operation_key = (order_no, asset_id, operation_no)

    logger.info(
        f"Updating operation: {operation_key}",
        extra={"request_id": getattr(request.state, 'request_id', None)}
    )

    updated = service.update(operation_key, operation_update)
    return updated


@router.delete("/{order_no}/{asset_id}/{operation_no}", status_code=204)
async def delete_operation(
    request: Request,
    order_no: str = Path(..., description="Work order number"),
    asset_id: int = Path(..., gt=0, description="Asset/machine ID"),
    operation_no: str = Path(..., description="Operation sequence number"),
    service: MESOperationService = Depends(get_mes_operation_service),
):
    """
    Delete an MES operation.

    Note: Finished operations cannot be deleted as per business rules.
    """
    operation_key = (order_no, asset_id, operation_no)

    logger.info(
        f"Deleting operation: {operation_key}",
        extra={"request_id": getattr(request.state, 'request_id', None)}
    )

    service.delete(operation_key)
    return None


# Manufacturing workflow endpoints
@router.post("/{order_no}/{asset_id}/{operation_no}/start", response_model=MESOperation)
async def start_operation(
    request: Request,
    order_no: str = Path(..., description="Work order number"),
    asset_id: int = Path(..., gt=0, description="Asset/machine ID"),
    operation_no: str = Path(..., description="Operation sequence number"),
    service: MESOperationService = Depends(get_mes_operation_service),
):
    """
    Start an operation (business workflow action).

    This will:
    - Change status to IN_PROGRESS
    - Set actual_start_at timestamp
    - Validate state transition rules
    """
    operation_key = (order_no, asset_id, operation_no)

    logger.info(
        f"Starting operation: {operation_key}",
        extra={"request_id": getattr(request.state, 'request_id', None)}
    )

    return service.start_operation(operation_key)


@router.post("/{order_no}/{asset_id}/{operation_no}/finish", response_model=MESOperation)
async def finish_operation(
    request: Request,
    order_no: str = Path(..., description="Work order number"),
    asset_id: int = Path(..., gt=0, description="Asset/machine ID"),
    operation_no: str = Path(..., description="Operation sequence number"),
    final_quantity: Optional[int] = Query(None, ge=0, description="Final processed quantity"),
    service: MESOperationService = Depends(get_mes_operation_service),
):
    """
    Finish an operation (business workflow action).

    This will:
    - Change status to FINISHED
    - Set actual_end_at timestamp
    - Optionally update final quantity
    - Validate state transition rules
    """
    operation_key = (order_no, asset_id, operation_no)

    logger.info(
        f"Finishing operation: {operation_key} with final_quantity: {final_quantity}",
        extra={"request_id": getattr(request.state, 'request_id', None)}
    )

    return service.finish_operation(operation_key, final_quantity)


@router.get("/{order_no}/{asset_id}/{operation_no}/efficiency")
async def get_operation_efficiency(
    request: Request,
    order_no: str = Path(..., description="Work order number"),
    asset_id: int = Path(..., gt=0, description="Asset/machine ID"),
    operation_no: str = Path(..., description="Operation sequence number"),
    service: MESOperationService = Depends(get_mes_operation_service),
):
    """
    Calculate operation efficiency based on actual vs target times.

    Returns efficiency ratio (target_time / actual_time).
    Values > 1.0 indicate better than planned performance.
    """
    operation_key = (order_no, asset_id, operation_no)

    operation = service.get_by_id(operation_key)
    if not operation:
        raise OperationNotFoundException(order_no, asset_id, operation_no)

    efficiency = service.calculate_efficiency(operation)

    return {
        "operation_key": {
            "order_no": order_no,
            "asset_id": asset_id,
            "operation_no": operation_no
        },
        "efficiency": efficiency,
        "target_processing_min": float(operation.t_target_processing_min) if operation.t_target_processing_min else None,
        "actual_processing_min": float(operation.t_actual_processing_min) if operation.t_actual_processing_min else None,
        "status": operation.status
    }