from sqlalchemy import Column, Text, DateTime, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from app.database import Base


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = {"schema": "public"}

    id = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id"), primary_key=True)
    email = Column(Text, index=True)
    full_name = Column(Text)
    role = Column(Text, default="operator", index=True)
    workplace_access = Column(ARRAY(Text))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self):
        return f"<Profile(id={self.id}, email={self.email}, role={self.role})>"
