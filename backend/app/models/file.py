import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, LtreeType

if TYPE_CHECKING:
    from models.folder import Folder
    from models.physical_file import PhysicalFile
    from models.permissions import FileAllowedUser
    from models.share_link import ShareLink

class File(Base):
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    folder_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("folders.id", ondelete="RESTRICT"), nullable=True)
    original_name: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str | None] = mapped_column(LtreeType, nullable=True)
    uploader_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")  # pending, completed, failed
    set_access_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    actual_access_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    physical_file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("physical_files.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    folder: Mapped["Folder | None"] = relationship("Folder", back_populates="files")
    physical_file: Mapped["PhysicalFile"] = relationship("PhysicalFile", back_populates="files")
    allowed_users: Mapped[list["FileAllowedUser"]] = relationship("FileAllowedUser", back_populates="file", cascade="all, delete-orphan")
    share_links: Mapped[list["ShareLink"]] = relationship("ShareLink", back_populates="file", cascade="all, delete-orphan")
