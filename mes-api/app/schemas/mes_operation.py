from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal


class MESOperationBase(BaseModel):
    """Base schema for MES Operation"""

    order_no: str = Field(
        ..., min_length=1, description="Work order number (e.g., '403860-001')"
    )
    asset_id: int = Field(..., gt=0, description="Asset/machine ID")
    operation_no: str = Field(
        ...,
        min_length=1,
        description="Operation sequence number (e.g., '0010', '0020')",
    )
    reference_url: Optional[str] = Field(
        None, description="External reference URL (drawings, docs)"
    )
    status: Optional[str] = Field(None, description="Current operation status")
    activity_code: Optional[str] = Field(
        None, description="Activity type code (e.g., 'LASER', 'TROMMELEN')"
    )
    activity_description: Optional[str] = Field(
        None, description="Human-readable activity description"
    )
    workplace_name: Optional[str] = Field(None, description="Workstation/machine name")
    workplace_group: Optional[str] = Field(
        None, description="Workstation group/department"
    )
    qty_desired: Optional[int] = Field(
        None, ge=0, description="Target quantity to produce"
    )
    qty_processed: Optional[int] = Field(
        None, ge=0, description="Quantity completed so far"
    )
    qty_scrap: Optional[int] = Field(
        None, ge=0, description="Quantity scrapped/rejected"
    )
    planned_start_at: Optional[datetime] = Field(None, description="Planned start time")
    planned_end_at: Optional[datetime] = Field(
        None, description="Planned completion time"
    )
    actual_start_at: Optional[datetime] = Field(None, description="Actual start time")
    actual_end_at: Optional[datetime] = Field(
        None, description="Actual completion time"
    )
    t_target_processing_min: Optional[Decimal] = Field(
        None, ge=0, description="Target processing time (minutes)"
    )
    t_target_setup_min: Optional[Decimal] = Field(
        None, ge=0, description="Target setup time (minutes)"
    )
    t_target_lead_min: Optional[Decimal] = Field(
        None, ge=0, description="Target lead time (minutes)"
    )
    t_actual_processing_min: Optional[Decimal] = Field(
        None, ge=0, description="Actual processing time (minutes)"
    )
    t_actual_setup_min: Optional[Decimal] = Field(
        None, ge=0, description="Actual setup time (minutes)"
    )
    t_actual_lead_min: Optional[Decimal] = Field(
        None, ge=0, description="Actual lead time (minutes)"
    )

    @field_validator("qty_processed", "qty_scrap")
    @classmethod
    def validate_quantities(cls, v, info):
        """Ensure quantities are non-negative"""
        if v is not None and v < 0:
            raise ValueError(f"{info.field_name} cannot be negative")
        return v


class MESOperationCreate(MESOperationBase):
    """Schema for creating a new MES Operation

    Example:
    {
        "order_no": "403860-001",
        "asset_id": 1,
        "operation_no": "0030",
        "workplace_name": "TruLaser 5060 (L76)",
        "activity_code": "LASER",
        "status": "RELEASED",
        "qty_desired": 100,
        "qty_processed": 0,
        "qty_scrap": 0,
        "timestamp_ms": "2025-09-30T10:00:00Z",
        "change_type": "INSERT"
    }
    """

    timestamp_ms: datetime = Field(..., description="Timestamp of this change/event")
    change_type: Literal["INSERT", "UPDATE", "DELETE"] = Field(
        ..., description="Type of change"
    )


class MESOperationUpdate(BaseModel):
    """Schema for updating an existing MES Operation (partial updates allowed)

    Example - Update quantity processed:
    {
        "qty_processed": 50,
        "timestamp_ms": "2025-09-30T11:00:00Z",
        "change_type": "UPDATE"
    }

    Example - Mark as finished:
    {
        "status": "FINISHED",
        "qty_processed": 100,
        "actual_end_at": "2025-09-30T15:30:00Z",
        "timestamp_ms": "2025-09-30T15:30:00Z",
        "change_type": "UPDATE"
    }
    """

    reference_url: Optional[str] = None
    status: Optional[str] = None
    activity_code: Optional[str] = None
    activity_description: Optional[str] = None
    workplace_name: Optional[str] = None
    workplace_group: Optional[str] = None
    qty_desired: Optional[int] = Field(None, ge=0)
    qty_processed: Optional[int] = Field(None, ge=0)
    qty_scrap: Optional[int] = Field(None, ge=0)
    planned_start_at: Optional[datetime] = None
    planned_end_at: Optional[datetime] = None
    actual_start_at: Optional[datetime] = None
    actual_end_at: Optional[datetime] = None
    t_target_processing_min: Optional[Decimal] = Field(None, ge=0)
    t_target_setup_min: Optional[Decimal] = Field(None, ge=0)
    t_target_lead_min: Optional[Decimal] = Field(None, ge=0)
    t_actual_processing_min: Optional[Decimal] = Field(None, ge=0)
    t_actual_setup_min: Optional[Decimal] = Field(None, ge=0)
    t_actual_lead_min: Optional[Decimal] = Field(None, ge=0)
    timestamp_ms: Optional[datetime] = None
    change_type: Optional[Literal["INSERT", "UPDATE", "DELETE"]] = None


class MESOperation(MESOperationBase):
    """Schema for reading MES Operation (includes all fields)"""

    timestamp_ms: datetime
    change_type: str

    model_config = ConfigDict(from_attributes=True)
