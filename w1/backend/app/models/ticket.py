from sqlalchemy import Column, BigInteger, String, Text, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.tag import Tag


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(BigInteger, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 关系
    tags = relationship(
        "Tag",
        secondary="ticket_tags",
        back_populates="tickets",
        lazy="selectin"
    )
