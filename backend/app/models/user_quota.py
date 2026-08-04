from datetime import datetime
from sqlalchemy import String, DateTime, func, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base

class B2BUserQuota(Base):
    __tablename__ = "b2b_user_quotas"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    allocated_quota_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
