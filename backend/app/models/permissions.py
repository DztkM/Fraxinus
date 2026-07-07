import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.folder import Folder
    from app.models.file import File

class FolderAllowedUser(Base):
    __tablename__ = "folder_allowed_users"

    folder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("folders.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    folder: Mapped["Folder"] = relationship("Folder", back_populates="allowed_users")

class FileAllowedUser(Base):
    __tablename__ = "file_allowed_users"

    file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    file: Mapped["File"] = relationship("File", back_populates="allowed_users")
