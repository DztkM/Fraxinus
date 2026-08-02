import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

class Namespace(Base):
    __tablename__ = "namespaces"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    author_id: Mapped[str | None] = mapped_column(String, nullable=True)
    quota_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    used_bytes: Mapped[int] = mapped_column(BigInteger, default=0, server_default='0', nullable=False)
    files_count: Mapped[int] = mapped_column(BigInteger, default=0, server_default='0', nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    files: Mapped[list["File"]] = relationship("File", back_populates="namespace", passive_deletes=True)
    folders: Mapped[list["Folder"]] = relationship("Folder", back_populates="namespace", passive_deletes=True)
    api_keys: Mapped[list["NamespaceAPIKey"]] = relationship("NamespaceAPIKey", back_populates="namespace", passive_deletes=True)
