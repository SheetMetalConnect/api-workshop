from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
import logging
from app.database import get_db
from app.schemas.mes_operation import (
    MESOperation,
    MESOperationCreate,
    MESOperationUpdate,
)
from app.crud import mes_operation
from app.exceptions.mes_exceptions import (
    DuplicateOperationException,
    InvalidQuantityException,
    InvalidOperationStateException,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[MESOperation], status_code=status.HTTP_200_OK)
def list_operations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status_filter: Optional[str] = Query(None, alias="status"),
    workplace_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    logger.info(
        f"Listing operations: skip={skip}, limit={limit}, status={status_filter}, workplace={workplace_name}"
    )
    return mes_operation.get_operations(
        db, skip=skip, limit=limit, status=status_filter, workplace_name=workplace_name
    )


@router.get("/{order_no}/{asset_id}/{operation_no}", response_model=MESOperation)
def get_operation(
    order_no: str = Path(...),
    asset_id: int = Path(..., gt=0),
    operation_no: str = Path(...),
    db: Session = Depends(get_db),
):
    logger.info(f"Getting operation: {order_no}/{asset_id}/{operation_no}")
    operation = mes_operation.get_operation(db, order_no, asset_id, operation_no)
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"Operation not found: {order_no}/{asset_id}/{operation_no}",
            },
        )
    return operation


@router.post("/", response_model=MESOperation, status_code=status.HTTP_201_CREATED)
def create_operation(
    operation: MESOperationCreate, response: Response, db: Session = Depends(get_db)
):
    logger.info(
        f"Creating operation: {operation.order_no}/{operation.asset_id}/{operation.operation_no}"
    )

    existing = mes_operation.get_operation(
        db, operation.order_no, operation.asset_id, operation.operation_no
    )
    if existing:
        raise DuplicateOperationException(
            operation.order_no, operation.asset_id, operation.operation_no
        )

    try:
        created = mes_operation.create_operation(db, operation)
        response.headers["Location"] = (
            f"/api/v1/operations/{created.order_no}/{created.asset_id}/{created.operation_no}"
        )
        logger.info(
            f"Operation created successfully: {created.order_no}/{created.operation_no}"
        )
        return created
    except InvalidQuantityException as e:
        logger.warning(f"Invalid quantity: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": e.error_type, "message": e.message},
        )
    except IntegrityError as e:
        logger.error(f"Database integrity error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "integrity_error",
                "message": "Database constraint violation",
            },
        )


@router.patch("/{order_no}/{asset_id}/{operation_no}", response_model=MESOperation)
def update_operation(
    order_no: str = Path(...),
    asset_id: int = Path(..., gt=0),
    operation_no: str = Path(...),
    operation_update: MESOperationUpdate = ...,
    db: Session = Depends(get_db),
):
    logger.info(f"Updating operation: {order_no}/{asset_id}/{operation_no}")

    existing = mes_operation.get_operation(db, order_no, asset_id, operation_no)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"Operation not found: {order_no}/{asset_id}/{operation_no}",
            },
        )

    update_data = operation_update.model_dump(exclude_unset=True)

    if "status" in update_data:
        if existing.status == "FINISHED" and update_data["status"] == "IN_PROGRESS":
            raise InvalidOperationStateException(
                existing.status, "change to IN_PROGRESS"
            )

    try:
        updated = mes_operation.update_operation(
            db, order_no, asset_id, operation_no, operation_update
        )
        logger.info(f"Operation updated successfully: {order_no}/{operation_no}")
        return updated
    except InvalidQuantityException as e:
        logger.warning(f"Invalid quantity during update: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": e.error_type, "message": e.message},
        )
    except IntegrityError as e:
        logger.error(f"Database integrity error during update: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "integrity_error",
                "message": "Database constraint violation",
            },
        )


@router.delete(
    "/{order_no}/{asset_id}/{operation_no}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_operation(
    order_no: str = Path(...),
    asset_id: int = Path(..., gt=0),
    operation_no: str = Path(...),
    db: Session = Depends(get_db),
):
    logger.info(f"Deleting operation: {order_no}/{asset_id}/{operation_no}")
    deleted = mes_operation.delete_operation(db, order_no, asset_id, operation_no)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"Operation not found: {order_no}/{asset_id}/{operation_no}",
            },
        )
    logger.info(f"Operation deleted: {order_no}/{operation_no}")
    return None
