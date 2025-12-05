from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.models import Tag, TicketTag
from app.schemas import TagCreate
from typing import Optional


class TagService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_tags(self, include_count: bool = True) -> list[Tag]:
        """获取所有标签"""
        query = select(Tag).order_by(Tag.name)
        result = await self.db.execute(query)
        tags = result.scalars().all()

        if include_count:
            # 为每个标签添加 ticket_count
            for tag in tags:
                count_query = select(func.count(TicketTag.ticket_id)).where(
                    TicketTag.tag_id == tag.id
                )
                count_result = await self.db.execute(count_query)
                tag.ticket_count = count_result.scalar() or 0

        return list(tags)

    async def get_tag_by_id(self, tag_id: int) -> Optional[Tag]:
        """根据 ID 获取标签"""
        query = select(Tag).where(Tag.id == tag_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_tag_by_name(self, name: str) -> Optional[Tag]:
        """根据名称获取标签"""
        query = select(Tag).where(Tag.name == name.lower().strip())
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_tag(self, tag_data: TagCreate) -> Tag:
        """创建标签"""
        # 标签名称转小写并去除空格
        tag_name = tag_data.name.lower().strip()

        # 检查是否已存在
        existing_tag = await self.get_tag_by_name(tag_name)
        if existing_tag:
            raise ValueError("Tag already exists")

        tag = Tag(name=tag_name)
        self.db.add(tag)
        await self.db.flush()
        await self.db.refresh(tag)
        return tag

    async def delete_tag(self, tag_id: int) -> bool:
        """删除标签"""
        tag = await self.get_tag_by_id(tag_id)
        if not tag:
            return False

        await self.db.delete(tag)
        await self.db.flush()
        return True
