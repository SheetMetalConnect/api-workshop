from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, Literal
from uuid import UUID


class OperationEventBase(BaseModel):
    """Base schema for Operation Event"""

    action_type: Literal["START", "STOP", "COMPLETE", "REPORT_QUANTITY", "FINISH"]
    order_no: str
    operation_no: str
    workplace_name: str
    user_id: Optional[UUID] = None
    user_email: Optional[str] = None
    operation_data: Optional[dict] = None


class OperationEventCreate(OperationEventBase):
    """Schema for creating a new Operation Event"""

    pass


class OperationEvent(OperationEventBase):
    """Schema for reading Operation Event (includes all fields)"""

    id: UUID
    webhook_success: bool = False
    webhook_response: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
