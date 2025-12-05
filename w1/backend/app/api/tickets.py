from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.ticket_service import TicketService
from app.schemas import (
    TicketCreate,
    TicketUpdate,
    TicketStatusUpdate,
    TicketResponse,
    TicketPaginatedResponse,
    AddTagToTicketRequest,
)
from typing import Optional, Literal
from math import ceil

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("", response_model=TicketPaginatedResponse)
async def get_tickets(
    status: Literal["all", "pending", "completed"] = Query("all", description="状态过滤"),
    tags: Optional[str] = Query(None, description="标签 ID，逗号分隔"),
    tag_filter_mode: Literal["and", "or"] = Query("and", description="标签过滤模式"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: Literal["created_at", "updated_at", "title"] = Query("created_at", description="排序字段"),
    sort_order: Literal["asc", "desc"] = Query("desc", description="排序顺序"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """获取所有 Tickets"""
    service = TicketService(db)

    # 解析标签 ID
    tag_ids = None
    if tags:
        try:
            tag_ids = [int(tag_id) for tag_id in tags.split(",")]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tag IDs"
            )

    tickets, total = await service.get_tickets(
        status=status,
        tags=tag_ids,
        tag_filter_mode=tag_filter_mode,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )

    total_pages = ceil(total / page_size)

    return TicketPaginatedResponse(
        data=tickets,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取单个 Ticket"""
    service = TicketService(db)
    ticket = await service.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    return ticket


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_data: TicketCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建 Ticket"""
    service = TicketService(db)
    ticket = await service.create_ticket(ticket_data)
    await db.commit()
    return ticket


@router.put("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: int,
    ticket_data: TicketUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新 Ticket"""
    service = TicketService(db)
    ticket = await service.update_ticket(ticket_id, ticket_data)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    await db.commit()
    return ticket


@router.patch("/{ticket_id}/status", response_model=TicketResponse)
async def update_ticket_status(
    ticket_id: int,
    status_data: TicketStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新 Ticket 状态"""
    service = TicketService(db)
    ticket = await service.update_ticket_status(ticket_id, status_data)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    await db.commit()
    return ticket


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除 Ticket"""
    service = TicketService(db)
    deleted = await service.delete_ticket(ticket_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    await db.commit()


@router.post("/{ticket_id}/tags", response_model=TicketResponse)
async def add_tag_to_ticket(
    ticket_id: int,
    tag_data: AddTagToTicketRequest,
    db: AsyncSession = Depends(get_db),
):
    """为 Ticket 添加标签"""
    service = TicketService(db)
    ticket = await service.add_tag_to_ticket(
        ticket_id,
        tag_id=tag_data.tag_id,
        tag_name=tag_data.tag_name,
    )
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket or Tag not found"
        )
    await db.commit()
    return ticket


@router.delete("/{ticket_id}/tags/{tag_id}", response_model=TicketResponse)
async def remove_tag_from_ticket(
    ticket_id: int,
    tag_id: int,
    db: AsyncSession = Depends(get_db),
):
    """从 Ticket 移除标签"""
    service = TicketService(db)
    ticket = await service.remove_tag_from_ticket(ticket_id, tag_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket or Tag not found"
        )
    await db.commit()
    return ticket
