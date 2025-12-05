from sqlalchemy import Column, BigInteger, DateTime, ForeignKey, func, PrimaryKeyConstraint
from app.database import Base


class TicketTag(Base):
    __tablename__ = "ticket_tags"

    ticket_id = Column(BigInteger, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    tag_id = Column(BigInteger, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint('ticket_id', 'tag_id'),
    )
