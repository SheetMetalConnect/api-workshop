from sqlalchemy import Column, Integer, Text, Numeric, DateTime, CheckConstraint
from app.database import Base


class MESOperation(Base):
    __tablename__ = "mes_operations"
    __table_args__ = {"schema": "public"}

    order_no = Column(Text, primary_key=True, nullable=False)
    asset_id = Column(Integer, primary_key=True, nullable=False)
    operation_no = Column(Text, primary_key=True, nullable=False)

    reference_url = Column(Text)
    status = Column(Text, index=True)

    activity_code = Column(Text)
    activity_description = Column(Text)

    workplace_name = Column(Text, index=True)
    workplace_group = Column(Text)

    qty_desired = Column(Integer)
    qty_processed = Column(Integer)
    qty_scrap = Column(Integer)

    planned_start_at = Column(DateTime(timezone=True))
    planned_end_at = Column(DateTime(timezone=True))

    actual_start_at = Column(DateTime(timezone=True))
    actual_end_at = Column(DateTime(timezone=True))

    t_target_processing_min = Column(Numeric)
    t_target_setup_min = Column(Numeric)
    t_target_lead_min = Column(Numeric)

    t_actual_processing_min = Column(Numeric)
    t_actual_setup_min = Column(Numeric)
    t_actual_lead_min = Column(Numeric)

    timestamp_ms = Column(DateTime(timezone=True), nullable=False)
    change_type = Column(Text, nullable=False)

    def __repr__(self):
        return f"<MESOperation(order={self.order_no}, op={self.operation_no}, status={self.status})>"
