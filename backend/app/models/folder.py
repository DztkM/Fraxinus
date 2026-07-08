import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, LtreeType

if TYPE_CHECKING:
    from models.file import File
    from models.permissions import FolderAllowedUser
    from models.share_link import ShareLink

class Folder(Base):
    __tablename__ = "folders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("folders.id", ondelete="RESTRICT"), nullable=True)
    path: Mapped[str | None] = mapped_column(LtreeType, nullable=True)
    author_id: Mapped[str] = mapped_column(String, nullable=False)
    set_access_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    actual_access_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    children: Mapped[list["Folder"]] = relationship("Folder", back_populates="parent", cascade="all, delete-orphan")
    parent: Mapped["Folder | None"] = relationship("Folder", back_populates="children", remote_side=[id])
    files: Mapped[list["File"]] = relationship("File", back_populates="folder", cascade="all, delete-orphan")
    allowed_users: Mapped[list["FolderAllowedUser"]] = relationship("FolderAllowedUser", back_populates="folder", cascade="all, delete-orphan")
    share_links: Mapped[list["ShareLink"]] = relationship("ShareLink", back_populates="folder", cascade="all, delete-orphan")
