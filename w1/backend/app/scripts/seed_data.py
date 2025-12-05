import asyncio
from app.database import AsyncSessionLocal
from app.models import Ticket, Tag


async def create_seed_data():
    async with AsyncSessionLocal() as db:
        # 创建标签
        tags_data = [
            Tag(name="feature"),
            Tag(name="bug"),
            Tag(name="enhancement"),
            Tag(name="urgent"),
            Tag(name="backend"),
            Tag(name="frontend"),
        ]
        db.add_all(tags_data)
        await db.flush()

        # 创建 Tickets
        tickets_data = [
            Ticket(
                title="实现用户登录功能",
                description="需要实现基本的用户登录功能",
                status="pending",
                tags=[tags_data[0], tags_data[4]]  # feature, backend
            ),
            Ticket(
                title="修复搜索功能 Bug",
                description="搜索时出现空指针异常",
                status="pending",
                tags=[tags_data[1], tags_data[3]]  # bug, urgent
            ),
            Ticket(
                title="优化前端性能",
                description="减少页面加载时间",
                status="completed",
                tags=[tags_data[2], tags_data[5]]  # enhancement, frontend
            ),
        ]
        db.add_all(tickets_data)
        await db.commit()

        print("✅ 种子数据创建成功！")


if __name__ == "__main__":
    asyncio.run(create_seed_data())
