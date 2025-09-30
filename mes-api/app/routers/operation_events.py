from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from uuid import UUID
import logging
from app.database import get_db
from app.schemas.operation_event import OperationEvent, OperationEventCreate
from app.crud import operation_event

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[OperationEvent])
def list_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    order_no: Optional[str] = None,
    action_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    logger.info(
        f"Listing events: skip={skip}, limit={limit}, order={order_no}, action={action_type}"
    )
    return operation_event.get_events(
        db, skip=skip, limit=limit, order_no=order_no, action_type=action_type
    )


@router.get("/{event_id}", response_model=OperationEvent)
def get_event(event_id: UUID, db: Session = Depends(get_db)):
    logger.info(f"Getting event: {event_id}")
    event = operation_event.get_event(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Event not found: {event_id}"},
        )
    return event


@router.post("/", response_model=OperationEvent, status_code=status.HTTP_201_CREATED)
def create_event(
    event: OperationEventCreate, response: Response, db: Session = Depends(get_db)
):
    logger.info(
        f"Creating event: {event.action_type} for {event.order_no}/{event.operation_no}"
    )
    try:
        created = operation_event.create_event(db, event)
        response.headers["Location"] = f"/api/v1/events/{created.id}"
        logger.info(f"Event created: {created.id}")
        return created
    except IntegrityError as e:
        logger.error(f"Database integrity error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "integrity_error",
                "message": "Database constraint violation",
            },
        )


@router.get("/workplace/{workplace_name}", response_model=List[OperationEvent])
def list_events_by_workplace(
    workplace_name: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    logger.info(f"Listing events for workplace: {workplace_name}")
    return operation_event.get_events_by_workplace(db, workplace_name, skip, limit)
