from sqlalchemy import Column, BigInteger, String, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.ticket import Ticket


class Tag(Base):
    __tablename__ = "tags"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 关系
    tickets = relationship(
        "Ticket",
        secondary="ticket_tags",
        back_populates="tags",
        lazy="selectin"
    )
