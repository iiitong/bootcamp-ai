from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# 基础 Schema
class TagBase(BaseModel):
    name: str = Field(..., max_length=50, description="标签名称")


# 创建 Tag 请求
class TagCreate(TagBase):
    pass


# Tag 响应
class TagResponse(TagBase):
    id: int
    created_at: datetime
    ticket_count: Optional[int] = None

    model_config = {"from_attributes": True}


# Tag 列表响应
class TagListResponse(BaseModel):
    data: list[TagResponse]
    total: int
