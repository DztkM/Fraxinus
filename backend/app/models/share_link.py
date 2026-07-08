import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.folder import Folder
    from models.file import File

class ShareLink(Base):
    __tablename__ = "share_links"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), nullable=True)
    folder_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("folders.id", ondelete="CASCADE"), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    file: Mapped["File | None"] = relationship("File", back_populates="share_links")
    folder: Mapped["Folder | None"] = relationship("Folder", back_populates="share_links")
