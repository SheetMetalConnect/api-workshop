from sqlalchemy import Column, Text, Boolean, DateTime, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.sql import func
from app.database import Base


class OperationEvent(Base):
    __tablename__ = "operation_events"
    __table_args__ = (
        CheckConstraint(
            "action_type = ANY (ARRAY['START'::text, 'STOP'::text, 'COMPLETE'::text, 'REPORT_QUANTITY'::text, 'FINISH'::text])",
            name="operation_events_action_type_check",
        ),
        {"schema": "public"},
    )

    id = Column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    action_type = Column(Text, nullable=False, index=True)
    order_no = Column(Text, nullable=False, index=True)
    operation_no = Column(Text, nullable=False)
    workplace_name = Column(Text, nullable=False, index=True)

    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id"))
    user_email = Column(Text)

    operation_data = Column(JSONB)

    webhook_success = Column(Boolean, default=False)
    webhook_response = Column(Text)
    error_message = Column(Text)

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self):
        return f"<OperationEvent(id={self.id}, action={self.action_type}, order={self.order_no})>"
