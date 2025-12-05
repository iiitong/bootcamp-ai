from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.tag_service import TagService
from app.schemas import TagCreate, TagResponse, TagListResponse

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=TagListResponse)
async def get_all_tags(
    include_count: bool = Query(True, description="是否包含 Ticket 数量"),
    db: AsyncSession = Depends(get_db),
):
    """获取所有标签"""
    service = TagService(db)
    tags = await service.get_all_tags(include_count=include_count)
    return TagListResponse(data=tags, total=len(tags))


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_data: TagCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建标签"""
    service = TagService(db)
    try:
        tag = await service.create_tag(tag_data)
        await db.commit()
        return tag
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除标签"""
    service = TagService(db)
    deleted = await service.delete_tag(tag_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    await db.commit()
