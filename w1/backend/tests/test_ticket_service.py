import pytest
from app.services.ticket_service import TicketService
from app.schemas import TicketCreate


@pytest.mark.asyncio
async def test_create_ticket(db_session):
    service = TicketService(db_session)

    ticket_data = TicketCreate(
        title="Test Ticket",
        description="Test Description",
    )

    ticket = await service.create_ticket(ticket_data)
    await db_session.commit()

    assert ticket.id is not None
    assert ticket.title == "Test Ticket"
    assert ticket.status == "pending"


@pytest.mark.asyncio
async def test_get_tickets(db_session):
    service = TicketService(db_session)

    # Create test tickets
    for i in range(3):
        await service.create_ticket(
            TicketCreate(title=f"Ticket {i}")
        )
    await db_session.commit()

    tickets, total = await service.get_tickets()

    assert total == 3
    assert len(tickets) == 3
