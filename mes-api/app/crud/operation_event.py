from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from uuid import UUID
from app.models.operation_event import OperationEvent
from app.schemas.operation_event import OperationEventCreate


def get_events(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    order_no: Optional[str] = None,
    action_type: Optional[str] = None,
) -> List[OperationEvent]:
    query = db.query(OperationEvent)

    if order_no:
        query = query.filter(OperationEvent.order_no == order_no)
    if action_type:
        query = query.filter(OperationEvent.action_type == action_type)

    return (
        query.order_by(OperationEvent.created_at.desc()).offset(skip).limit(limit).all()
    )


def get_event(db: Session, event_id: UUID) -> Optional[OperationEvent]:
    return db.query(OperationEvent).filter(OperationEvent.id == event_id).first()


def create_event(db: Session, event: OperationEventCreate) -> OperationEvent:
    try:
        db_event = OperationEvent(**event.model_dump())
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        return db_event
    except IntegrityError:
        db.rollback()
        raise


def get_events_by_workplace(
    db: Session, workplace_name: str, skip: int = 0, limit: int = 100
) -> List[OperationEvent]:
    return (
        db.query(OperationEvent)
        .filter(OperationEvent.workplace_name == workplace_name)
        .order_by(OperationEvent.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
