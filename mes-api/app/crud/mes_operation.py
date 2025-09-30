from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from app.models.mes_operation import MESOperation
from app.schemas.mes_operation import MESOperationCreate, MESOperationUpdate
from app.exceptions.mes_exceptions import InvalidQuantityException


def get_operations(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    workplace_name: Optional[str] = None,
) -> List[MESOperation]:
    query = db.query(MESOperation)

    if status:
        query = query.filter(MESOperation.status == status)
    if workplace_name:
        query = query.filter(MESOperation.workplace_name == workplace_name)

    return (
        query.order_by(MESOperation.order_no, MESOperation.operation_no)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_operation(
    db: Session, order_no: str, asset_id: int, operation_no: str
) -> Optional[MESOperation]:
    return (
        db.query(MESOperation)
        .filter(
            MESOperation.order_no == order_no,
            MESOperation.asset_id == asset_id,
            MESOperation.operation_no == operation_no,
        )
        .first()
    )


def create_operation(db: Session, operation: MESOperationCreate) -> MESOperation:
    if operation.qty_processed and operation.qty_desired:
        if operation.qty_processed > operation.qty_desired:
            raise InvalidQuantityException(
                f"qty_processed ({operation.qty_processed}) cannot exceed qty_desired ({operation.qty_desired})"
            )

    try:
        db_operation = MESOperation(**operation.model_dump())
        db.add(db_operation)
        db.commit()
        db.refresh(db_operation)
        return db_operation
    except IntegrityError:
        db.rollback()
        raise


def update_operation(
    db: Session,
    order_no: str,
    asset_id: int,
    operation_no: str,
    operation_update: MESOperationUpdate,
) -> Optional[MESOperation]:
    db_operation = get_operation(db, order_no, asset_id, operation_no)
    if not db_operation:
        return None

    update_data = operation_update.model_dump(exclude_unset=True)

    new_qty_processed = update_data.get("qty_processed", db_operation.qty_processed)
    qty_desired = update_data.get("qty_desired", db_operation.qty_desired)

    if new_qty_processed and qty_desired and new_qty_processed > qty_desired:
        raise InvalidQuantityException(
            f"qty_processed ({new_qty_processed}) cannot exceed qty_desired ({qty_desired})"
        )

    try:
        for field, value in update_data.items():
            setattr(db_operation, field, value)

        db.commit()
        db.refresh(db_operation)
        return db_operation
    except IntegrityError:
        db.rollback()
        raise


def delete_operation(
    db: Session, order_no: str, asset_id: int, operation_no: str
) -> bool:
    db_operation = get_operation(db, order_no, asset_id, operation_no)
    if not db_operation:
        return False

    try:
        db.delete(db_operation)
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        raise
