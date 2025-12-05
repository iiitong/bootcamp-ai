from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import selectinload
from app.models import Ticket, Tag, TicketTag
from app.schemas import TicketCreate, TicketUpdate, TicketStatusUpdate
from app.services.tag_service import TagService
from typing import Optional, Literal
from math import ceil


class TicketService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tag_service = TagService(db)

    async def get_tickets(
        self,
        status: Optional[Literal["all", "pending", "completed"]] = "all",
        tags: Optional[list[int]] = None,
        tag_filter_mode: Literal["and", "or"] = "and",
        search: Optional[str] = None,
        sort_by: Literal["created_at", "updated_at", "title"] = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Ticket], int]:
        """获取 Tickets（带分页和过滤）"""
        query = select(Ticket).options(selectinload(Ticket.tags))

        # 状态过滤
        if status != "all":
            query = query.where(Ticket.status == status)

        # 搜索标题
        if search:
            query = query.where(Ticket.title.ilike(f"%{search}%"))

        # 标签过滤
        if tags:
            if tag_filter_mode == "and":
                # AND 逻辑：Ticket 必须包含所有选中的标签
                for tag_id in tags:
                    subquery = select(TicketTag.ticket_id).where(
                        TicketTag.tag_id == tag_id
                    )
                    query = query.where(Ticket.id.in_(subquery))
            else:
                # OR 逻辑：Ticket 包含任一标签即可
                subquery = select(TicketTag.ticket_id).where(
                    TicketTag.tag_id.in_(tags)
                ).distinct()
                query = query.where(Ticket.id.in_(subquery))

        # 排序
        if sort_order == "asc":
            query = query.order_by(getattr(Ticket, sort_by).asc())
        else:
            query = query.order_by(getattr(Ticket, sort_by).desc())

        # 获取总数（在分页之前）
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        tickets = result.scalars().all()

        return list(tickets), total

    async def get_ticket_by_id(self, ticket_id: int) -> Optional[Ticket]:
        """根据 ID 获取 Ticket"""
        query = select(Ticket).options(selectinload(Ticket.tags)).where(
            Ticket.id == ticket_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_ticket(self, ticket_data: TicketCreate) -> Ticket:
        """创建 Ticket"""
        ticket = Ticket(
            title=ticket_data.title,
            description=ticket_data.description,
            status="pending",
        )
        self.db.add(ticket)
        await self.db.flush()
        await self.db.refresh(ticket, attribute_names=["tags"])

        # 添加标签
        if ticket_data.tag_ids:
            for tag_id in ticket_data.tag_ids:
                tag = await self.tag_service.get_tag_by_id(tag_id)
                if tag:
                    ticket.tags.append(tag)

        await self.db.flush()
        await self.db.refresh(ticket, attribute_names=["tags"])
        return ticket

    async def update_ticket(
        self, ticket_id: int, ticket_data: TicketUpdate
    ) -> Optional[Ticket]:
        """更新 Ticket"""
        ticket = await self.get_ticket_by_id(ticket_id)
        if not ticket:
            return None

        if ticket_data.title is not None:
            ticket.title = ticket_data.title
        if ticket_data.description is not None:
            ticket.description = ticket_data.description

        await self.db.flush()
        await self.db.refresh(ticket)
        return ticket

    async def update_ticket_status(
        self, ticket_id: int, status_data: TicketStatusUpdate
    ) -> Optional[Ticket]:
        """更新 Ticket 状态"""
        ticket = await self.get_ticket_by_id(ticket_id)
        if not ticket:
            return None

        ticket.status = status_data.status
        await self.db.flush()
        await self.db.refresh(ticket)
        return ticket

    async def delete_ticket(self, ticket_id: int) -> bool:
        """删除 Ticket"""
        ticket = await self.get_ticket_by_id(ticket_id)
        if not ticket:
            return False

        await self.db.delete(ticket)
        await self.db.flush()
        return True

    async def add_tag_to_ticket(
        self, ticket_id: int, tag_id: Optional[int] = None, tag_name: Optional[str] = None
    ) -> Optional[Ticket]:
        """为 Ticket 添加标签"""
        ticket = await self.get_ticket_by_id(ticket_id)
        if not ticket:
            return None

        # 根据 tag_id 或 tag_name 获取或创建标签
        if tag_id:
            tag = await self.tag_service.get_tag_by_id(tag_id)
        elif tag_name:
            tag = await self.tag_service.get_tag_by_name(tag_name)
            if not tag:
                from app.schemas import TagCreate
                tag = await self.tag_service.create_tag(TagCreate(name=tag_name))
        else:
            return None

        if not tag:
            return None

        # 检查标签是否已关联
        if tag not in ticket.tags:
            ticket.tags.append(tag)
            await self.db.flush()
            await self.db.refresh(ticket)

        return ticket

    async def remove_tag_from_ticket(
        self, ticket_id: int, tag_id: int
    ) -> Optional[Ticket]:
        """从 Ticket 移除标签"""
        ticket = await self.get_ticket_by_id(ticket_id)
        if not ticket:
            return None

        tag = await self.tag_service.get_tag_by_id(tag_id)
        if not tag:
            return None

        if tag in ticket.tags:
            ticket.tags.remove(tag)
            await self.db.flush()
            await self.db.refresh(ticket)

        return ticket
