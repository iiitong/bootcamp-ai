from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal
from app.schemas.tag import TagResponse


# 基础 Schema
class TicketBase(BaseModel):
    title: str = Field(..., max_length=200, description="Ticket 标题")
    description: Optional[str] = Field(None, description="Ticket 描述")


# 创建 Ticket 请求
class TicketCreate(TicketBase):
    tag_ids: Optional[list[int]] = Field(None, description="标签 ID 列表")


# 更新 Ticket 请求
class TicketUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None


# 更新 Ticket 状态请求
class TicketStatusUpdate(BaseModel):
    status: Literal["pending", "completed"] = Field(..., description="Ticket 状态")


# Ticket 响应
class TicketResponse(TicketBase):
    id: int
    status: str
    tags: list[TagResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Ticket 分页响应
class TicketPaginatedResponse(BaseModel):
    data: list[TicketResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# 添加/移除标签请求
class AddTagToTicketRequest(BaseModel):
    tag_id: Optional[int] = None
    tag_name: Optional[str] = None
