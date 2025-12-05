# Project Alpha - 详细实现计划

**文档版本**: v1.0
**创建日期**: 2025-12-04
**项目代号**: Project Alpha
**项目根目录**: `./w1`

---

## 目录

1. [项目概述](#1-项目概述)
2. [开发环境准备](#2-开发环境准备)
3. [第一阶段：项目初始化](#3-第一阶段项目初始化)
4. [第二阶段：数据库设计和初始化](#4-第二阶段数据库设计和初始化)
5. [第三阶段：后端 API 开发](#5-第三阶段后端-api-开发)
6. [第四阶段：前端基础架构](#6-第四阶段前端基础架构)
7. [第五阶段：前端功能实现](#7-第五阶段前端功能实现)
8. [第六阶段：集成测试和优化](#8-第六阶段集成测试和优化)
9. [第七阶段：部署和文档](#9-第七阶段部署和文档)
10. [里程碑和时间估算](#10-里程碑和时间估算)

---

## 1. 项目概述

### 1.1 项目目标
实现一个轻量级的 Ticket 管理工具，支持任务创建、标签分类、搜索过滤等核心功能。

### 1.2 技术栈
- **后端**: FastAPI 0.123.0 + Python 3.14.1 + PostgreSQL 18.1
- **前端**: React 19.2.1 + TypeScript 5.9.3 + Vite 7.2.6 + Tailwind CSS 4.1.17
- **包管理**: uv (后端) + yarn (前端)
- **数据库**: PostgreSQL 18 (本地部署)

### 1.3 项目结构
```
w1/
├── backend/              # 后端代码
│   ├── app/
│   │   ├── api/         # API 路由
│   │   ├── models/      # 数据库模型
│   │   ├── schemas/     # Pydantic 模型
│   │   ├── services/    # 业务逻辑
│   │   ├── database.py  # 数据库配置
│   │   └── main.py      # 应用入口
│   ├── alembic/         # 数据库迁移
│   ├── tests/           # 测试文件
│   ├── pyproject.toml   # Python 依赖
│   └── .env             # 环境变量
├── frontend/            # 前端代码
│   ├── src/
│   │   ├── components/  # React 组件
│   │   ├── api/         # API 客户端
│   │   ├── types/       # TypeScript 类型
│   │   ├── hooks/       # 自定义 Hooks
│   │   ├── lib/         # 工具函数
│   │   └── App.tsx      # 应用入口
│   ├── public/          # 静态资源
│   ├── package.json     # Node 依赖
│   ├── tsconfig.json    # TypeScript 配置
│   └── .env             # 环境变量
└── README.md            # 项目说明
```

---

## 2. 开发环境准备

### 2.1 必需软件安装

#### 2.1.1 基础工具
- [x] 安装 **Python 3.14+**
  ```bash
  使用 uv 自动安装
  curl -LsSf https://astral.sh/uv/install.sh | sh
  uv python install 3.14
  ```

- [x] 安装 **Node.js 24.x LTS**
  ```bash
  # macOS (使用 Homebrew)
  brew install node@24

  # 或使用 nvm
  nvm install 24
  nvm use 24
  ```

#### 2.1.2 前端包管理器 (yarn)
- [x] 安装 yarn
  ```bash
  # 使用 corepack (Node.js 内置)
  corepack enable
  corepack prepare yarn@stable --activate

  # 验证安装
  yarn --version
  ```

### 2.2 IDE 和编辑器配置

#### 2.2.1 推荐使用 VS Code
- [x] 安装 **VS Code**
- [x] 安装扩展:
  - Python (ms-python.python)
  - Pylance (ms-python.vscode-pylance)
  - ESLint (dbaeumer.vscode-eslint)
  - Prettier (esbenp.prettier-vscode)
  - Tailwind CSS IntelliSense (bradlc.vscode-tailwindcss)
  - TypeScript Vue Plugin (Vue.volar)

#### 2.2.2 VS Code 配置
创建 `.vscode/settings.json`:
```json
{
  "python.linting.enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

### 2.3 数据库环境
- [x] 验证 PostgreSQL 18 服务运行
  ```bash
  # macOS
  brew services list | grep postgresql

  # Linux
  sudo systemctl status postgresql

  # 如果服务未运行，启动服务
  # macOS: brew services start postgresql@18
  # Linux: sudo systemctl start postgresql
  ```

- [x] 创建项目数据库
  ```bash
  # 连接到 PostgreSQL
  psql postgres

  # 在 psql 中创建数据库
  CREATE DATABASE project_alpha;

  # 验证数据库创建成功
  \l

  # 退出
  \q
  ```

- [x] 验证数据库连接
  ```bash
  # 连接到项目数据库
  psql -h localhost -p 5432 -U postgres -d project_alpha

  # 如果连接成功，应该看到 psql 提示符
  # project_alpha=#
  ```

---

## 3. 第一阶段：项目初始化

### 3.1 创建项目目录结构

#### 3.1.1 初始化 Git 仓库
- [x] 初始化 Git
  ```bash
  git init
  ```

- [x] 创建 `.gitignore`
  ```gitignore
  # Python
  __pycache__/
  *.py[cod]
  *$py.class
  *.so
  .Python
  build/
  develop-eggs/
  dist/
  downloads/
  eggs/
  .eggs/
  lib/
  lib64/
  parts/
  sdist/
  var/
  wheels/
  *.egg-info/
  .installed.cfg
  *.egg
  .venv/
  venv/
  ENV/
  env/

  # Node
  node_modules/
  npm-debug.log*
  yarn-debug.log*
  yarn-error.log*
  .pnp.*
  dist/
  dist-ssr/

  # Environment variables
  .env
  .env.local
  .env.*.local

  # IDE
  .vscode/
  .idea/
  *.swp
  *.swo
  *~
  .DS_Store

  # Database
  *.db
  *.sqlite
  *.sqlite3
  ```

### 3.2 后端项目初始化

#### 3.2.1 创建后端目录
- [x] 创建后端目录结构
  ```bash
  mkdir -p backend
  cd backend
  ```

#### 3.2.2 使用 uv 初始化项目
- [x] 初始化 Python 项目
  ```bash
  uv init
  ```

- [x] 安装生产依赖
  ```bash
  uv add fastapi uvicorn[standard] sqlalchemy asyncpg alembic pydantic pydantic-settings python-dotenv
  ```

- [x] 安装开发依赖
  ```bash
  uv add --dev pytest pytest-asyncio pytest-cov black ruff mypy types-psycopg2
  ```

#### 3.2.3 配置 pyproject.toml
- [x] 编辑 `pyproject.toml`，添加工具配置:
  ```toml
  [project]
  name = "project-alpha-backend"
  version = "0.1.0"
  description = "Project Alpha Backend API"
  requires-python = ">=3.14"
  dependencies = [
      "fastapi>=0.123.0",
      "uvicorn[standard]>=0.38.0",
      "sqlalchemy>=2.0.44",
      "asyncpg>=0.30.0",
      "alembic>=1.17.2",
      "pydantic>=2.12.5",
      "pydantic-settings>=2.7.0",
      "python-dotenv>=1.0.1",
  ]

  [tool.black]
  line-length = 88
  target-version = ['py314']

  [tool.ruff]
  line-length = 88
  target-version = "py314"

  [tool.mypy]
  python_version = "3.14"
  strict = true
  warn_return_any = true
  warn_unused_configs = true
  disallow_untyped_defs = true
  plugins = ["pydantic.mypy"]

  [tool.pydantic-mypy]
  init_forbid_extra = true
  init_typed = true
  warn_required_dynamic_aliases = true

  [tool.pytest.ini_options]
  asyncio_mode = "auto"
  testpaths = ["tests"]
  ```

#### 3.2.4 创建环境变量文件
- [x] 创建 `.env` 文件
  ```env
  # Database
  DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/project_alpha

  # API
  API_V1_PREFIX=/api/v1
  PROJECT_NAME=Project Alpha

  # CORS
  BACKEND_CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

  # Development
  DEBUG=True
  ```

- [x] 创建 `.env.example` (用于版本控制)
  ```bash
  cp .env .env.example
  # 编辑 .env.example，移除敏感信息，保留键名
  ```

#### 3.2.5 创建基础目录结构
- [x] 创建应用目录
  ```bash
  mkdir -p app/{api,models,schemas,services,core}
  mkdir -p tests
  touch app/__init__.py
  touch app/api/__init__.py
  touch app/models/__init__.py
  touch app/schemas/__init__.py
  touch app/services/__init__.py
  touch app/core/__init__.py
  ```

### 3.3 前端项目初始化

#### 3.3.1 创建前端项目
- [x] 使用 Vite 创建项目
  ```bash
  cd ..  # 返回 w1 目录
  yarn create vite frontend --template react-ts
  cd frontend
  ```

#### 3.3.2 安装依赖
- [x] 安装基础依赖
  ```bash
  yarn install
  ```

- [x] 安装 Tailwind CSS
  ```bash
  yarn add -D tailwindcss postcss autoprefixer
  yarn add -D @tailwindcss/forms @tailwindcss/typography
  npx tailwindcss init -p
  ```

- [x] 安装 Shadcn UI 依赖
  ```bash
  yarn add @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-label
  yarn add @radix-ui/react-select @radix-ui/react-separator @radix-ui/react-slot
  yarn add @radix-ui/react-toast @radix-ui/react-tooltip @radix-ui/react-checkbox
  yarn add class-variance-authority clsx tailwind-merge lucide-react
  ```

- [x] 安装 API 客户端和状态管理
  ```bash
  yarn add axios @tanstack/react-query
  yarn add zustand  # 轻量级状态管理
  ```

- [x] 安装开发工具
  ```bash
  yarn add -D @types/node
  yarn add -D eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin
  yarn add -D prettier eslint-config-prettier eslint-plugin-prettier
  ```

#### 3.3.3 配置 Tailwind CSS
- [x] 编辑 `tailwind.config.js`
  ```js
  /** @type {import('tailwindcss').Config} */
  export default {
    content: [
      "./index.html",
      "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
      extend: {},
    },
    plugins: [
      require('@tailwindcss/forms'),
      require('@tailwindcss/typography'),
    ],
  }
  ```

- [x] 更新 `src/index.css`
  ```css
  @tailwind base;
  @tailwind components;
  @tailwind utilities;
  ```

#### 3.3.4 配置 TypeScript
- [x] 编辑 `tsconfig.json`
  ```json
  {
    "compilerOptions": {
      "target": "ES2020",
      "useDefineForClassFields": true,
      "lib": ["ES2020", "DOM", "DOM.Iterable"],
      "module": "ESNext",
      "skipLibCheck": true,

      /* 类型检查 */
      "strict": true,
      "noUnusedLocals": true,
      "noUnusedParameters": true,
      "noFallthroughCasesInSwitch": true,
      "noImplicitAny": true,

      /* Bundler mode */
      "moduleResolution": "bundler",
      "allowImportingTsExtensions": true,
      "resolveJsonModule": true,
      "isolatedModules": true,
      "noEmit": true,
      "jsx": "react-jsx",

      /* Path mapping */
      "baseUrl": ".",
      "paths": {
        "@/*": ["./src/*"]
      }
    },
    "include": ["src"],
    "references": [{ "path": "./tsconfig.node.json" }]
  }
  ```

#### 3.3.5 创建环境变量文件
- [x] 创建 `.env`
  ```env
  VITE_API_BASE_URL=http://localhost:8000/api/v1
  ```

- [x] 创建 `.env.example`
  ```bash
  cp .env .env.example
  ```

#### 3.3.6 配置 Vite
- [x] 编辑 `vite.config.ts`，添加路径别名
  ```ts
  import { defineConfig } from 'vite'
  import react from '@vitejs/plugin-react'
  import path from 'path'

  export default defineConfig({
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
  })
  ```

#### 3.3.7 创建基础目录结构
- [x] 创建前端目录
  ```bash
  mkdir -p src/{components,api,types,hooks,lib,store}
  ```

---

## 4. 第二阶段：数据库设计和初始化

### 4.1 创建数据库配置文件

#### 4.1.1 创建数据库连接配置
- [ ] 创建 `backend/app/core/config.py`
  ```python
  from pydantic_settings import BaseSettings, SettingsConfigDict
  from typing import List


  class Settings(BaseSettings):
      # Database
      DATABASE_URL: str

      # API
      API_V1_PREFIX: str = "/api/v1"
      PROJECT_NAME: str = "Project Alpha"

      # CORS
      BACKEND_CORS_ORIGINS: List[str] = []

      # Development
      DEBUG: bool = False

      model_config = SettingsConfigDict(
          env_file=".env",
          case_sensitive=True,
          extra="ignore"
      )


  settings = Settings()
  ```

#### 4.1.2 创建数据库引擎配置
- [ ] 创建 `backend/app/database.py`
  ```python
  from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
  from sqlalchemy.orm import DeclarativeBase
  from app.core.config import settings


  # 创建异步引擎
  engine = create_async_engine(
      settings.DATABASE_URL,
      echo=settings.DEBUG,  # 开发环境启用 SQL 日志
      pool_size=5,
      max_overflow=10,
  )

  # 创建异步 session maker
  AsyncSessionLocal = async_sessionmaker(
      engine,
      class_=AsyncSession,
      expire_on_commit=False,
  )


  # Base 模型
  class Base(DeclarativeBase):
      pass


  # 依赖注入函数
  async def get_db() -> AsyncSession:
      async with AsyncSessionLocal() as session:
          try:
              yield session
              await session.commit()
          except Exception:
              await session.rollback()
              raise
          finally:
              await session.close()
  ```

### 4.2 创建数据库模型

#### 4.2.1 创建 Ticket 模型
- [ ] 创建 `backend/app/models/ticket.py`
  ```python
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
  ```

#### 4.2.2 创建 Tag 模型
- [ ] 创建 `backend/app/models/tag.py`
  ```python
  from sqlalchemy import Column, BigInteger, String, DateTime, func
  from sqlalchemy.orm import relationship
  from app.database import Base
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from app.models.ticket import Ticket


  class Tag(Base):
      __tablename__ = "tags"

      id = Column(BigInteger, primary_key=True, index=True)
      name = Column(String(50), nullable=False, unique=True, index=True)
      created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

      # 关系
      tickets = relationship(
          "Ticket",
          secondary="ticket_tags",
          back_populates="tags",
          lazy="selectin"
      )
  ```

#### 4.2.3 创建 TicketTag 关联模型
- [ ] 创建 `backend/app/models/ticket_tag.py`
  ```python
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
  ```

#### 4.2.4 更新模型 __init__.py
- [ ] 编辑 `backend/app/models/__init__.py`
  ```python
  from app.models.ticket import Ticket
  from app.models.tag import Tag
  from app.models.ticket_tag import TicketTag

  __all__ = ["Ticket", "Tag", "TicketTag"]
  ```

### 4.3 设置 Alembic 数据库迁移

#### 4.3.1 初始化 Alembic
- [ ] 在 backend 目录初始化 Alembic
  ```bash
  cd backend
  uv run alembic init alembic
  ```

#### 4.3.2 配置 Alembic
- [ ] 编辑 `backend/alembic.ini`
  ```ini
  # 注释掉这一行
  # sqlalchemy.url = driver://user:pass@localhost/dbname
  ```

- [ ] 编辑 `backend/alembic/env.py`
  ```python
  from logging.config import fileConfig
  from sqlalchemy import pool
  from sqlalchemy.engine import Connection
  from sqlalchemy.ext.asyncio import async_engine_from_config
  from alembic import context

  # 导入 Base 和 settings
  from app.database import Base
  from app.core.config import settings

  # 导入所有模型（确保被注册）
  from app.models import Ticket, Tag, TicketTag

  config = context.config

  # 从环境变量设置数据库 URL
  config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

  if config.config_file_name is not None:
      fileConfig(config.config_file_name)

  target_metadata = Base.metadata


  def run_migrations_offline() -> None:
      url = config.get_main_option("sqlalchemy.url")
      context.configure(
          url=url,
          target_metadata=target_metadata,
          literal_binds=True,
          dialect_opts={"paramstyle": "named"},
      )

      with context.begin_transaction():
          context.run_migrations()


  def do_run_migrations(connection: Connection) -> None:
      context.configure(connection=connection, target_metadata=target_metadata)

      with context.begin_transaction():
          context.run_migrations()


  async def run_async_migrations() -> None:
      configuration = config.get_section(config.config_ini_section)
      configuration["sqlalchemy.url"] = settings.DATABASE_URL
      connectable = async_engine_from_config(
          configuration,
          prefix="sqlalchemy.",
          poolclass=pool.NullPool,
      )

      async with connectable.connect() as connection:
          await connection.run_sync(do_run_migrations)

      await connectable.dispose()


  def run_migrations_online() -> None:
      import asyncio
      asyncio.run(run_async_migrations())


  if context.is_offline_mode():
      run_migrations_offline()
  else:
      run_migrations_online()
  ```

#### 4.3.3 创建初始迁移
- [ ] 生成初始迁移文件
  ```bash
  uv run alembic revision --autogenerate -m "Initial migration"
  ```

- [ ] 检查生成的迁移文件 (在 `alembic/versions/` 目录)

#### 4.3.4 执行数据库迁移
- [ ] 应用迁移到数据库
  ```bash
  uv run alembic upgrade head
  ```

- [ ] 验证数据库表已创建
  ```bash
  psql -U postgres -d project_alpha -c "\dt"
  ```

### 4.4 创建数据库种子数据

#### 4.4.1 创建种子数据脚本
- [ ] 创建 `backend/app/scripts/seed_data.py`
  ```python
  import asyncio
  from app.database import AsyncSessionLocal
  from app.models import Ticket, Tag, TicketTag


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
  ```

- [ ] 执行种子数据脚本
  ```bash
  uv run python -m app.scripts.seed_data
  ```

---

## 5. 第三阶段：后端 API 开发

### 5.1 创建 Pydantic Schemas

#### 5.1.1 创建 Tag Schema
- [x] 创建 `backend/app/schemas/tag.py`
  ```python
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
  ```

#### 5.1.2 创建 Ticket Schema
- [x] 创建 `backend/app/schemas/ticket.py`
  ```python
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
  ```

#### 5.1.3 更新 schemas __init__.py
- [x] 编辑 `backend/app/schemas/__init__.py`
  ```python
  from app.schemas.ticket import (
      TicketCreate,
      TicketUpdate,
      TicketStatusUpdate,
      TicketResponse,
      TicketPaginatedResponse,
      AddTagToTicketRequest,
  )
  from app.schemas.tag import (
      TagCreate,
      TagResponse,
      TagListResponse,
  )

  __all__ = [
      "TicketCreate",
      "TicketUpdate",
      "TicketStatusUpdate",
      "TicketResponse",
      "TicketPaginatedResponse",
      "AddTagToTicketRequest",
      "TagCreate",
      "TagResponse",
      "TagListResponse",
  ]
  ```

### 5.2 创建业务逻辑层 (Services)

#### 5.2.1 创建 Tag Service
- [x] 创建 `backend/app/services/tag_service.py`
  ```python
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
  ```

#### 5.2.2 创建 Ticket Service
- [x] 创建 `backend/app/services/ticket_service.py`
  ```python
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

          # 添加标签
          if ticket_data.tag_ids:
              for tag_id in ticket_data.tag_ids:
                  tag = await self.tag_service.get_tag_by_id(tag_id)
                  if tag:
                      ticket.tags.append(tag)

          await self.db.flush()
          await self.db.refresh(ticket)
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
  ```

### 5.3 创建 API 路由

#### 5.3.1 创建 Tag API 路由
- [x] 创建 `backend/app/api/tags.py`
  ```python
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
  ```

#### 5.3.2 创建 Ticket API 路由
- [x] 创建 `backend/app/api/tickets.py`
  ```python
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
  ```

#### 5.3.3 创建 API 路由聚合
- [x] 创建 `backend/app/api/__init__.py`
  ```python
  from fastapi import APIRouter
  from app.api import tickets, tags

  api_router = APIRouter()
  api_router.include_router(tickets.router)
  api_router.include_router(tags.router)
  ```

### 5.4 创建主应用

#### 5.4.1 创建 FastAPI 应用
- [x] 创建 `backend/app/main.py`
  ```python
  from fastapi import FastAPI
  from fastapi.middleware.cors import CORSMiddleware
  from app.core.config import settings
  from app.api import api_router

  app = FastAPI(
      title=settings.PROJECT_NAME,
      openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
      docs_url=f"{settings.API_V1_PREFIX}/docs",
      redoc_url=f"{settings.API_V1_PREFIX}/redoc",
  )

  # CORS 中间件
  if settings.BACKEND_CORS_ORIGINS:
      app.add_middleware(
          CORSMiddleware,
          allow_origins=settings.BACKEND_CORS_ORIGINS,
          allow_credentials=True,
          allow_methods=["*"],
          allow_headers=["*"],
      )

  # 注册路由
  app.include_router(api_router, prefix=settings.API_V1_PREFIX)


  @app.get("/")
  async def root():
      return {"message": "Welcome to Project Alpha API"}


  @app.get("/health")
  async def health_check():
      return {"status": "ok"}
  ```

### 5.5 运行和测试后端

#### 5.5.1 启动开发服务器
- [x] 运行开发服务器
  ```bash
  cd backend
  uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```

#### 5.5.2 测试 API
- [x] 访问 API 文档: `http://localhost:8000/api/v1/docs`
- [x] 测试健康检查: `http://localhost:8000/health`
- [x] 使用 Swagger UI 测试所有端点

#### 5.5.3 使用 curl 测试（可选）
- [x] 测试创建 Tag
  ```bash
  curl -X POST http://localhost:8000/api/v1/tags \
    -H "Content-Type: application/json" \
    -d '{"name": "test-tag"}'
  ```

- [x] 测试创建 Ticket
  ```bash
  curl -X POST http://localhost:8000/api/v1/tickets \
    -H "Content-Type: application/json" \
    -d '{
      "title": "Test Ticket",
      "description": "This is a test",
      "tag_ids": [1]
    }'
  ```

---

## 6. 第四阶段：前端基础架构

### 6.1 创建 TypeScript 类型定义

#### 6.1.1 创建 Tag 类型
- [x] 创建 `frontend/src/types/tag.ts`
  ```typescript
  export interface Tag {
    id: number;
    name: string;
    created_at?: string;
    ticket_count?: number;
  }

  export interface CreateTagDto {
    name: string;
  }

  export interface TagListResponse {
    data: Tag[];
    total: number;
  }
  ```

#### 6.1.2 创建 Ticket 类型
- [x] 创建 `frontend/src/types/ticket.ts`
  ```typescript
  import { Tag } from './tag';

  export type TicketStatus = 'pending' | 'completed';

  export interface Ticket {
    id: number;
    title: string;
    description: string | null;
    status: TicketStatus;
    tags: Tag[];
    created_at: string;
    updated_at: string;
  }

  export interface CreateTicketDto {
    title: string;
    description?: string;
    tag_ids?: number[];
  }

  export interface UpdateTicketDto {
    title?: string;
    description?: string;
  }

  export interface UpdateTicketStatusDto {
    status: TicketStatus;
  }

  export interface AddTagToTicketDto {
    tag_id?: number;
    tag_name?: string;
  }

  export interface PaginatedResponse<T> {
    data: T[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  }

  export interface GetTicketsParams {
    status?: 'all' | 'pending' | 'completed';
    tags?: string;  // 逗号分隔的 tag IDs
    tag_filter_mode?: 'and' | 'or';
    search?: string;
    sort_by?: 'created_at' | 'updated_at' | 'title';
    sort_order?: 'asc' | 'desc';
    page?: number;
    page_size?: number;
  }
  ```

#### 6.1.3 创建 API 错误类型
- [x] 创建 `frontend/src/types/api.ts`
  ```typescript
  export interface ApiError {
    detail: string;
  }
  ```

### 6.2 创建 API 客户端

#### 6.2.1 创建 Axios 客户端
- [x] 创建 `frontend/src/api/client.ts`
  ```typescript
  import axios from 'axios';

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

  export const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // 响应拦截器（可选：处理错误）
  apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
      console.error('API Error:', error.response?.data || error.message);
      return Promise.reject(error);
    }
  );
  ```

#### 6.2.2 创建 Tag API
- [x] 创建 `frontend/src/api/tags.ts`
  ```typescript
  import { apiClient } from './client';
  import { Tag, CreateTagDto, TagListResponse } from '@/types/tag';

  export const tagApi = {
    getAll: (includeCount = true) =>
      apiClient.get<TagListResponse>('/tags', {
        params: { include_count: includeCount },
      }),

    create: (data: CreateTagDto) =>
      apiClient.post<Tag>('/tags', data),

    delete: (id: number) =>
      apiClient.delete(`/tags/${id}`),
  };
  ```

#### 6.2.3 创建 Ticket API
- [x] 创建 `frontend/src/api/tickets.ts`
  ```typescript
  import { apiClient } from './client';
  import {
    Ticket,
    CreateTicketDto,
    UpdateTicketDto,
    UpdateTicketStatusDto,
    AddTagToTicketDto,
    PaginatedResponse,
    GetTicketsParams,
  } from '@/types/ticket';

  export const ticketApi = {
    getAll: (params?: GetTicketsParams) =>
      apiClient.get<PaginatedResponse<Ticket>>('/tickets', { params }),

    getById: (id: number) =>
      apiClient.get<Ticket>(`/tickets/${id}`),

    create: (data: CreateTicketDto) =>
      apiClient.post<Ticket>('/tickets', data),

    update: (id: number, data: UpdateTicketDto) =>
      apiClient.put<Ticket>(`/tickets/${id}`, data),

    updateStatus: (id: number, data: UpdateTicketStatusDto) =>
      apiClient.patch<Ticket>(`/tickets/${id}/status`, data),

    delete: (id: number) =>
      apiClient.delete(`/tickets/${id}`),

    addTag: (ticketId: number, data: AddTagToTicketDto) =>
      apiClient.post<Ticket>(`/tickets/${ticketId}/tags`, data),

    removeTag: (ticketId: number, tagId: number) =>
      apiClient.delete<Ticket>(`/tickets/${ticketId}/tags/${tagId}`),
  };
  ```

### 6.3 设置状态管理 (Zustand)

#### 6.3.1 创建 Zustand Store
- [x] 创建 `frontend/src/store/useAppStore.ts`
  ```typescript
  import { create } from 'zustand';
  import { Ticket, GetTicketsParams } from '@/types/ticket';
  import { Tag } from '@/types/tag';

  interface FilterState {
    status: 'all' | 'pending' | 'completed';
    selectedTags: number[];
    tagFilterMode: 'and' | 'or';
    searchQuery: string;
    sortBy: 'created_at' | 'updated_at' | 'title';
    sortOrder: 'asc' | 'desc';
  }

  interface PaginationState {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  }

  interface AppState {
    // Tickets
    tickets: Ticket[];
    ticketsLoading: boolean;
    ticketsError: string | null;

    // Tags
    tags: Tag[];
    tagsLoading: boolean;

    // Filters
    filters: FilterState;

    // Pagination
    pagination: PaginationState;

    // Actions
    setTickets: (tickets: Ticket[]) => void;
    setTicketsLoading: (loading: boolean) => void;
    setTicketsError: (error: string | null) => void;

    setTags: (tags: Tag[]) => void;
    setTagsLoading: (loading: boolean) => void;

    setFilter: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
    resetFilters: () => void;

    setPagination: (pagination: Partial<PaginationState>) => void;
  }

  const initialFilters: FilterState = {
    status: 'all',
    selectedTags: [],
    tagFilterMode: 'and',
    searchQuery: '',
    sortBy: 'created_at',
    sortOrder: 'desc',
  };

  const initialPagination: PaginationState = {
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
  };

  export const useAppStore = create<AppState>((set) => ({
    // Initial state
    tickets: [],
    ticketsLoading: false,
    ticketsError: null,

    tags: [],
    tagsLoading: false,

    filters: initialFilters,
    pagination: initialPagination,

    // Actions
    setTickets: (tickets) => set({ tickets }),
    setTicketsLoading: (loading) => set({ ticketsLoading: loading }),
    setTicketsError: (error) => set({ ticketsError: error }),

    setTags: (tags) => set({ tags }),
    setTagsLoading: (loading) => set({ tagsLoading: loading }),

    setFilter: (key, value) =>
      set((state) => ({
        filters: { ...state.filters, [key]: value },
      })),

    resetFilters: () => set({ filters: initialFilters }),

    setPagination: (pagination) =>
      set((state) => ({
        pagination: { ...state.pagination, ...pagination },
      })),
  }));
  ```

### 6.4 创建工具函数

#### 6.4.1 创建颜色工具函数
- [x] 创建 `frontend/src/lib/colors.ts`
  ```typescript
  /**
   * 根据字符串生成一致的颜色
   * 使用简单的哈希算法
   */
  export function getColorForTag(tagName: string): string {
    let hash = 0;
    for (let i = 0; i < tagName.length; i++) {
      hash = tagName.charCodeAt(i) + ((hash << 5) - hash);
    }

    const colors = [
      'bg-blue-100 text-blue-800',
      'bg-green-100 text-green-800',
      'bg-yellow-100 text-yellow-800',
      'bg-red-100 text-red-800',
      'bg-purple-100 text-purple-800',
      'bg-pink-100 text-pink-800',
      'bg-indigo-100 text-indigo-800',
      'bg-orange-100 text-orange-800',
    ];

    const index = Math.abs(hash) % colors.length;
    return colors[index];
  }
  ```

#### 6.4.2 创建日期格式化工具
- [x] 创建 `frontend/src/lib/date.ts`
  ```typescript
  /**
   * 格式化日期为易读格式
   */
  export function formatDate(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      return '今天';
    } else if (days === 1) {
      return '昨天';
    } else if (days < 7) {
      return `${days} 天前`;
    } else {
      return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    }
  }

  /**
   * 格式化完整日期时间
   */
  export function formatDateTime(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
  ```

#### 6.4.3 创建 cn 工具函数（用于合并 className）
- [x] 创建 `frontend/src/lib/utils.ts`
  ```typescript
  import { type ClassValue, clsx } from 'clsx';
  import { twMerge } from 'tailwind-merge';

  export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
  }
  ```

---

## 7. 第五阶段：前端功能实现

### 7.1 创建基础 UI 组件

#### 7.1.1 创建 Button 组件
- [x] 创建 `frontend/src/components/ui/Button.tsx`
  ```typescript
  import { ButtonHTMLAttributes, forwardRef } from 'react';
  import { cn } from '@/lib/utils';

  interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
    size?: 'sm' | 'md' | 'lg';
  }

  export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant = 'primary', size = 'md', ...props }, ref) => {
      const baseStyles = 'inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50';

      const variants = {
        primary: 'bg-blue-600 text-white hover:bg-blue-700 focus-visible:ring-blue-600',
        secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 focus-visible:ring-gray-400',
        danger: 'bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-600',
        ghost: 'hover:bg-gray-100 focus-visible:ring-gray-400',
      };

      const sizes = {
        sm: 'h-8 px-3 text-sm',
        md: 'h-10 px-4',
        lg: 'h-12 px-6 text-lg',
      };

      return (
        <button
          ref={ref}
          className={cn(baseStyles, variants[variant], sizes[size], className)}
          {...props}
        />
      );
    }
  );

  Button.displayName = 'Button';
  ```

#### 7.1.2 创建 Input 组件
- [x] 创建 `frontend/src/components/ui/Input.tsx`
  ```typescript
  import { InputHTMLAttributes, forwardRef } from 'react';
  import { cn } from '@/lib/utils';

  interface InputProps extends InputHTMLAttributes<HTMLInputElement> {}

  export const Input = forwardRef<HTMLInputElement, InputProps>(
    ({ className, type, ...props }, ref) => {
      return (
        <input
          type={type}
          className={cn(
            'flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm',
            'placeholder:text-gray-400',
            'focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent',
            'disabled:cursor-not-allowed disabled:opacity-50',
            className
          )}
          ref={ref}
          {...props}
        />
      );
    }
  );

  Input.displayName = 'Input';
  ```

#### 7.1.3 创建 Card 组件
- [x] 创建 `frontend/src/components/ui/Card.tsx`
  ```typescript
  import { HTMLAttributes, forwardRef } from 'react';
  import { cn } from '@/lib/utils';

  export const Card = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
    ({ className, ...props }, ref) => (
      <div
        ref={ref}
        className={cn(
          'rounded-lg border border-gray-200 bg-white shadow-sm',
          className
        )}
        {...props}
      />
    )
  );
  Card.displayName = 'Card';

  export const CardHeader = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
    ({ className, ...props }, ref) => (
      <div
        ref={ref}
        className={cn('flex flex-col space-y-1.5 p-6', className)}
        {...props}
      />
    )
  );
  CardHeader.displayName = 'CardHeader';

  export const CardTitle = forwardRef<HTMLHeadingElement, HTMLAttributes<HTMLHeadingElement>>(
    ({ className, ...props }, ref) => (
      <h3
        ref={ref}
        className={cn('text-lg font-semibold leading-none tracking-tight', className)}
        {...props}
      />
    )
  );
  CardTitle.displayName = 'CardTitle';

  export const CardContent = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
    ({ className, ...props }, ref) => (
      <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
    )
  );
  CardContent.displayName = 'CardContent';
  ```

### 7.2 创建业务组件

#### 7.2.1 创建 TagBadge 组件
- [x] 创建 `frontend/src/components/TagBadge.tsx`
  ```typescript
  import { Tag } from '@/types/tag';
  import { getColorForTag } from '@/lib/colors';
  import { cn } from '@/lib/utils';
  import { X } from 'lucide-react';

  interface TagBadgeProps {
    tag: Tag;
    onRemove?: () => void;
    clickable?: boolean;
    onClick?: () => void;
  }

  export function TagBadge({ tag, onRemove, clickable, onClick }: TagBadgeProps) {
    const colorClass = getColorForTag(tag.name);

    return (
      <span
        className={cn(
          'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium',
          colorClass,
          clickable && 'cursor-pointer hover:opacity-80',
        )}
        onClick={onClick}
      >
        {tag.name}
        {tag.ticket_count !== undefined && ` (${tag.ticket_count})`}
        {onRemove && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            className="ml-0.5 hover:bg-black/10 rounded-full p-0.5"
          >
            <X className="h-3 w-3" />
          </button>
        )}
      </span>
    );
  }
  ```

#### 7.2.2 创建 TicketCard 组件
- [x] 创建 `frontend/src/components/TicketCard.tsx`
  ```typescript
  import { Ticket } from '@/types/ticket';
  import { Card, CardContent } from '@/components/ui/Card';
  import { TagBadge } from '@/components/TagBadge';
  import { formatDate } from '@/lib/date';
  import { Checkbox } from '@/components/ui/Checkbox';
  import { Trash2 } from 'lucide-react';
  import { cn } from '@/lib/utils';

  interface TicketCardProps {
    ticket: Ticket;
    onToggleStatus: (id: number) => void;
    onDelete: (id: number) => void;
    onRemoveTag: (ticketId: number, tagId: number) => void;
  }

  export function TicketCard({
    ticket,
    onToggleStatus,
    onDelete,
    onRemoveTag,
  }: TicketCardProps) {
    const isCompleted = ticket.status === 'completed';

    return (
      <Card className={cn('transition-all', isCompleted && 'opacity-60')}>
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            {/* Checkbox */}
            <Checkbox
              checked={isCompleted}
              onCheckedChange={() => onToggleStatus(ticket.id)}
              className="mt-1"
            />

            {/* Content */}
            <div className="flex-1 min-w-0">
              {/* Title */}
              <h3
                className={cn(
                  'text-base font-medium mb-1',
                  isCompleted && 'line-through text-gray-500'
                )}
              >
                {ticket.title}
              </h3>

              {/* Description */}
              {ticket.description && (
                <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                  {ticket.description}
                </p>
              )}

              {/* Tags */}
              {ticket.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {ticket.tags.map((tag) => (
                    <TagBadge
                      key={tag.id}
                      tag={tag}
                      onRemove={() => onRemoveTag(ticket.id, tag.id)}
                    />
                  ))}
                </div>
              )}

              {/* Meta */}
              <div className="flex items-center gap-3 text-xs text-gray-500">
                <span>创建: {formatDate(ticket.created_at)}</span>
                {ticket.updated_at !== ticket.created_at && (
                  <span>更新: {formatDate(ticket.updated_at)}</span>
                )}
              </div>
            </div>

            {/* Delete Button */}
            <button
              onClick={() => onDelete(ticket.id)}
              className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
              title="删除"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        </CardContent>
      </Card>
    );
  }
  ```

#### 7.2.3 创建 Checkbox 组件
- [x] 创建 `frontend/src/components/ui/Checkbox.tsx`
  ```typescript
  import { forwardRef, InputHTMLAttributes } from 'react';
  import { cn } from '@/lib/utils';
  import { Check } from 'lucide-react';

  interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'onCheckedChange'> {
    onCheckedChange?: (checked: boolean) => void;
  }

  export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
    ({ className, onCheckedChange, ...props }, ref) => {
      return (
        <div className="relative inline-flex items-center">
          <input
            type="checkbox"
            ref={ref}
            className="sr-only peer"
            onChange={(e) => onCheckedChange?.(e.target.checked)}
            {...props}
          />
          <div
            className={cn(
              'h-5 w-5 rounded border-2 border-gray-300 bg-white',
              'peer-checked:bg-blue-600 peer-checked:border-blue-600',
              'peer-focus-visible:ring-2 peer-focus-visible:ring-blue-600 peer-focus-visible:ring-offset-2',
              'flex items-center justify-center transition-colors cursor-pointer',
              className
            )}
          >
            <Check className="h-3.5 w-3.5 text-white opacity-0 peer-checked:opacity-100" />
          </div>
        </div>
      );
    }
  );

  Checkbox.displayName = 'Checkbox';
  ```

#### 7.2.4 创建 TicketForm 组件
- [x] 创建 `frontend/src/components/TicketForm.tsx`
  ```typescript
  import { useState, FormEvent } from 'react';
  import { Input } from '@/components/ui/Input';
  import { Button } from '@/components/ui/Button';
  import { Tag } from '@/types/tag';
  import { TagBadge } from '@/components/TagBadge';

  interface TicketFormProps {
    tags: Tag[];
    onSubmit: (data: { title: string; description: string; tag_ids: number[] }) => void;
    onCancel: () => void;
  }

  export function TicketForm({ tags, onSubmit, onCancel }: TicketFormProps) {
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);

    const handleSubmit = (e: FormEvent) => {
      e.preventDefault();
      if (!title.trim()) return;

      onSubmit({
        title: title.trim(),
        description: description.trim(),
        tag_ids: selectedTagIds,
      });

      // Reset form
      setTitle('');
      setDescription('');
      setSelectedTagIds([]);
    };

    const toggleTag = (tagId: number) => {
      setSelectedTagIds((prev) =>
        prev.includes(tagId)
          ? prev.filter((id) => id !== tagId)
          : [...prev, tagId]
      );
    };

    return (
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">
            标题 *
          </label>
          <Input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="输入 Ticket 标题"
            maxLength={200}
            required
          />
        </div>

        <div>
          <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
            描述
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="输入 Ticket 描述（可选）"
            className="flex min-h-[100px] w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
            rows={4}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            标签（可选）
          </label>
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <TagBadge
                key={tag.id}
                tag={tag}
                clickable
                onClick={() => toggleTag(tag.id)}
                className={selectedTagIds.includes(tag.id) ? 'ring-2 ring-blue-600' : ''}
              />
            ))}
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-4">
          <Button type="button" variant="secondary" onClick={onCancel}>
            取消
          </Button>
          <Button type="submit" variant="primary">
            创建
          </Button>
        </div>
      </form>
    );
  }
  ```

#### 7.2.5 创建 SearchBar 组件
- [x] 创建 `frontend/src/components/SearchBar.tsx`
  ```typescript
  import { Input } from '@/components/ui/Input';
  import { Search, X } from 'lucide-react';

  interface SearchBarProps {
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
  }

  export function SearchBar({
    value,
    onChange,
    placeholder = '搜索 Tickets...',
  }: SearchBarProps) {
    return (
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="pl-10 pr-10"
        />
        {value && (
          <button
            type="button"
            onClick={() => onChange('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    );
  }
  ```

#### 7.2.6 创建 FilterPanel 组件
- [x] 创建 `frontend/src/components/FilterPanel.tsx`
  ```typescript
  import { Tag } from '@/types/tag';
  import { TagBadge } from '@/components/TagBadge';
  import { Button } from '@/components/ui/Button';

  interface FilterPanelProps {
    tags: Tag[];
    selectedStatus: 'all' | 'pending' | 'completed';
    selectedTagIds: number[];
    onStatusChange: (status: 'all' | 'pending' | 'completed') => void;
    onTagToggle: (tagId: number) => void;
    onResetFilters: () => void;
  }

  export function FilterPanel({
    tags,
    selectedStatus,
    selectedTagIds,
    onStatusChange,
    onTagToggle,
    onResetFilters,
  }: FilterPanelProps) {
    const hasActiveFilters = selectedStatus !== 'all' || selectedTagIds.length > 0;

    return (
      <div className="space-y-6">
        {/* Status Filter */}
        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">状态</h3>
          <div className="space-y-2">
            {(['all', 'pending', 'completed'] as const).map((status) => (
              <label key={status} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="status"
                  checked={selectedStatus === status}
                  onChange={() => onStatusChange(status)}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-600"
                />
                <span className="text-sm text-gray-700">
                  {status === 'all' && '全部'}
                  {status === 'pending' && '待办'}
                  {status === 'completed' && '已完成'}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Tag Filter */}
        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">标签</h3>
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <TagBadge
                key={tag.id}
                tag={tag}
                clickable
                onClick={() => onTagToggle(tag.id)}
                className={selectedTagIds.includes(tag.id) ? 'ring-2 ring-blue-600' : ''}
              />
            ))}
          </div>
        </div>

        {/* Reset Button */}
        {hasActiveFilters && (
          <Button
            variant="secondary"
            size="sm"
            onClick={onResetFilters}
            className="w-full"
          >
            重置筛选
          </Button>
        )}
      </div>
    );
  }
  ```

### 7.3 创建主应用组件

#### 7.3.1 创建 App 组件
- [x] 编辑 `frontend/src/App.tsx`
  ```typescript
  import { useEffect, useState } from 'react';
  import { useAppStore } from '@/store/useAppStore';
  import { ticketApi } from '@/api/tickets';
  import { tagApi } from '@/api/tags';
  import { TicketCard } from '@/components/TicketCard';
  import { TicketForm } from '@/components/TicketForm';
  import { SearchBar } from '@/components/SearchBar';
  import { FilterPanel } from '@/components/FilterPanel';
  import { Button } from '@/components/ui/Button';
  import { Plus } from 'lucide-react';

  function App() {
    const [showForm, setShowForm] = useState(false);

    const {
      tickets,
      ticketsLoading,
      tags,
      filters,
      pagination,
      setTickets,
      setTicketsLoading,
      setTags,
      setFilter,
      resetFilters,
      setPagination,
    } = useAppStore();

    // Load tags on mount
    useEffect(() => {
      loadTags();
    }, []);

    // Load tickets when filters change
    useEffect(() => {
      loadTickets();
    }, [filters, pagination.page]);

    const loadTags = async () => {
      try {
        const response = await tagApi.getAll(true);
        setTags(response.data.data);
      } catch (error) {
        console.error('Failed to load tags:', error);
      }
    };

    const loadTickets = async () => {
      setTicketsLoading(true);
      try {
        const response = await ticketApi.getAll({
          status: filters.status,
          tags: filters.selectedTags.length > 0 ? filters.selectedTags.join(',') : undefined,
          tag_filter_mode: filters.tagFilterMode,
          search: filters.searchQuery || undefined,
          sort_by: filters.sortBy,
          sort_order: filters.sortOrder,
          page: pagination.page,
          page_size: pagination.pageSize,
        });

        setTickets(response.data.data);
        setPagination({
          total: response.data.total,
          totalPages: response.data.total_pages,
        });
      } catch (error) {
        console.error('Failed to load tickets:', error);
      } finally {
        setTicketsLoading(false);
      }
    };

    const handleCreateTicket = async (data: any) => {
      try {
        await ticketApi.create(data);
        setShowForm(false);
        loadTickets();
        loadTags(); // Reload tags to update counts
      } catch (error) {
        console.error('Failed to create ticket:', error);
      }
    };

    const handleToggleStatus = async (id: number) => {
      const ticket = tickets.find((t) => t.id === id);
      if (!ticket) return;

      try {
        await ticketApi.updateStatus(id, {
          status: ticket.status === 'pending' ? 'completed' : 'pending',
        });
        loadTickets();
      } catch (error) {
        console.error('Failed to update ticket status:', error);
      }
    };

    const handleDeleteTicket = async (id: number) => {
      if (!window.confirm('确定要删除这个 Ticket 吗？')) return;

      try {
        await ticketApi.delete(id);
        loadTickets();
        loadTags();
      } catch (error) {
        console.error('Failed to delete ticket:', error);
      }
    };

    const handleRemoveTag = async (ticketId: number, tagId: number) => {
      try {
        await ticketApi.removeTag(ticketId, tagId);
        loadTickets();
        loadTags();
      } catch (error) {
        console.error('Failed to remove tag:', error);
      }
    };

    const handleTagToggle = (tagId: number) => {
      const newSelectedTags = filters.selectedTags.includes(tagId)
        ? filters.selectedTags.filter((id) => id !== tagId)
        : [...filters.selectedTags, tagId];
      setFilter('selectedTags', newSelectedTags);
    };

    return (
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center justify-between">
              <h1 className="text-2xl font-bold text-gray-900">Project Alpha</h1>
              <div className="flex items-center gap-4">
                <SearchBar
                  value={filters.searchQuery}
                  onChange={(value) => setFilter('searchQuery', value)}
                />
                <Button onClick={() => setShowForm(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  新建
                </Button>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            {/* Sidebar */}
            <aside className="lg:col-span-1">
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <FilterPanel
                  tags={tags}
                  selectedStatus={filters.status}
                  selectedTagIds={filters.selectedTags}
                  onStatusChange={(status) => setFilter('status', status)}
                  onTagToggle={handleTagToggle}
                  onResetFilters={resetFilters}
                />
              </div>
            </aside>

            {/* Ticket List */}
            <main className="lg:col-span-3">
              {showForm && (
                <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
                  <h2 className="text-lg font-semibold mb-4">新建 Ticket</h2>
                  <TicketForm
                    tags={tags}
                    onSubmit={handleCreateTicket}
                    onCancel={() => setShowForm(false)}
                  />
                </div>
              )}

              {ticketsLoading ? (
                <div className="text-center py-12">
                  <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
                  <p className="mt-2 text-sm text-gray-500">加载中...</p>
                </div>
              ) : tickets.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-500">暂无 Tickets</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {tickets.map((ticket) => (
                    <TicketCard
                      key={ticket.id}
                      ticket={ticket}
                      onToggleStatus={handleToggleStatus}
                      onDelete={handleDeleteTicket}
                      onRemoveTag={handleRemoveTag}
                    />
                  ))}
                </div>
              )}

              {/* Pagination */}
              {pagination.totalPages > 1 && (
                <div className="mt-6 flex justify-center gap-2">
                  <Button
                    variant="secondary"
                    disabled={pagination.page === 1}
                    onClick={() => setPagination({ page: pagination.page - 1 })}
                  >
                    上一页
                  </Button>
                  <span className="px-4 py-2 text-sm text-gray-700">
                    第 {pagination.page} / {pagination.totalPages} 页
                  </span>
                  <Button
                    variant="secondary"
                    disabled={pagination.page === pagination.totalPages}
                    onClick={() => setPagination({ page: pagination.page + 1 })}
                  >
                    下一页
                  </Button>
                </div>
              )}
            </main>
          </div>
        </div>
      </div>
    );
  }

  export default App;
  ```

### 7.4 运行和测试前端

#### 7.4.1 启动前端开发服务器
- [x] 运行前端
  ```bash
  cd frontend
  yarn dev
  ```

#### 7.4.2 测试功能
- [x] 打开浏览器访问 `http://localhost:5173`
- [x] 测试创建 Ticket
- [x] 测试标签过滤
- [x] 测试搜索功能
- [x] 测试状态切换
- [x] 测试删除 Ticket

---

## 8. 第六阶段：集成测试和优化

### 8.1 后端测试

#### 8.1.1 创建测试配置
- [x] 创建 `backend/tests/conftest.py`
  ```python
  import pytest
  import asyncio
  from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
  from app.database import Base
  from app.models import Ticket, Tag, TicketTag

  # 测试数据库 URL
  TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/project_alpha_test"


  @pytest.fixture(scope="session")
  def event_loop():
      loop = asyncio.get_event_loop_policy().new_event_loop()
      yield loop
      loop.close()


  @pytest.fixture(scope="session")
  async def test_engine():
      engine = create_async_engine(TEST_DATABASE_URL, echo=False)

      # 创建表
      async with engine.begin() as conn:
          await conn.run_sync(Base.metadata.create_all)

      yield engine

      # 清理
      async with engine.begin() as conn:
          await conn.run_sync(Base.metadata.drop_all)

      await engine.dispose()


  @pytest.fixture
  async def db_session(test_engine):
      AsyncSessionLocal = async_sessionmaker(
          test_engine,
          class_=AsyncSession,
          expire_on_commit=False,
      )

      async with AsyncSessionLocal() as session:
          yield session
          await session.rollback()
  ```

#### 8.1.2 创建 Service 测试
- [x] 创建 `backend/tests/test_ticket_service.py`
  ```python
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
  ```

#### 8.1.3 运行后端测试
- [x] 执行测试
  ```bash
  cd backend
  uv run pytest
  ```

### 8.2 前端测试

#### 8.2.1 安装测试依赖
- [x] 安装 Vitest 和 Testing Library
  ```bash
  cd frontend
  yarn add -D vitest @testing-library/react @testing-library/jest-dom
  ```

#### 8.2.2 创建简单组件测试
- [x] 创建 `frontend/src/components/__tests__/Button.test.tsx`
  ```typescript
  import { describe, it, expect } from 'vitest';
  import { render, screen } from '@testing-library/react';
  import { Button } from '../ui/Button';

  describe('Button', () => {
    it('renders with text', () => {
      render(<Button>Click me</Button>);
      expect(screen.getByText('Click me')).toBeInTheDocument();
    });
  });
  ```

### 8.3 性能优化

#### 8.3.1 后端优化
- [x] 添加数据库查询优化
  - 使用 `selectinload` 预加载关联数据
  - 添加适当的索引
  - 使用分页减少数据量

#### 8.3.2 前端优化
- [x] 实现防抖搜索
  - 创建 `frontend/src/hooks/useDebounce.ts`
  ```typescript
  import { useEffect, useState } from 'react';

  export function useDebounce<T>(value: T, delay: number): T {
    const [debouncedValue, setDebouncedValue] = useState(value);

    useEffect(() => {
      const handler = setTimeout(() => {
        setDebouncedValue(value);
      }, delay);

      return () => {
        clearTimeout(handler);
      };
    }, [value, delay]);

    return debouncedValue;
  }
  ```

- [x] 在 SearchBar 中使用防抖
  ```typescript
  // In App.tsx
  const debouncedSearch = useDebounce(filters.searchQuery, 300);

  useEffect(() => {
    loadTickets();
  }, [debouncedSearch, /* other deps */]);
  ```

---

## 9. 第七阶段：部署和文档

### 9.1 创建生产环境配置

#### 9.1.1 后端生产配置
- [x] 创建 `backend/.env.production`
  ```env
  DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
  DEBUG=False
  BACKEND_CORS_ORIGINS=["https://your-domain.com"]
  ```

#### 9.1.2 前端生产配置
- [x] 创建 `frontend/.env.production`
  ```env
  VITE_API_BASE_URL=https://api.your-domain.com/api/v1
  ```

### 9.2 文档编写

#### 9.2.1 创建 README
- [x] 创建项目根目录 `README.md`
  ```markdown
  # Project Alpha - Ticket 管理工具

  一个轻量级的 Ticket 管理工具，支持标签分类和高效的搜索过滤功能。

  ## 技术栈

  - 后端: FastAPI + PostgreSQL
  - 前端: React + TypeScript + Tailwind CSS

  ## 快速开始

  ### 前置要求

  - Python 3.14+
  - Node.js 24+
  - PostgreSQL 18+

  ### 安装

  1. 克隆仓库
  2. 创建数据库: `psql postgres -c "CREATE DATABASE project_alpha;"`
  3. 启动后端: `cd backend && uv run uvicorn app.main:app --reload`
  4. 启动前端: `cd frontend && yarn dev`

  ## 文档

  - [需求和设计文档](./specs/w1/0001-spec.md)
  - [实现计划](./specs/w1/0002-implementation-plan.md)
  ```

#### 9.2.2 创建 API 文档
- [x] FastAPI 自动生成，访问 `/api/v1/docs`

---

## 10. 里程碑和时间估算

### 里程碑

| 阶段 | 里程碑 | 预计时间 |
|------|--------|----------|
| 1 | 项目初始化完成 | 1 天 |
| 2 | 数据库设计完成 | 0.5 天 |
| 3 | 后端 API 开发完成 | 2-3 天 |
| 4 | 前端基础架构完成 | 1 天 |
| 5 | 前端功能实现完成 | 2-3 天 |
| 6 | 集成测试和优化完成 | 1-2 天 |
| 7 | 部署和文档完成 | 1 天 |
| **总计** | **项目完成** | **8-11 天** |

### 优先级

**P0 (必须完成)**:
- 项目初始化
- 数据库设计
- Ticket CRUD API
- Tag CRUD API
- 基础前端界面
- Ticket 列表和创建

**P1 (重要)**:
- 标签过滤
- 搜索功能
- 状态管理
- 基础测试

**P2 (可选)**:
- 高级过滤
- 性能优化
- 完整测试覆盖
- 生产环境部署

---

## 附录

### A. 常用命令

#### 后端命令
```bash
# 开发服务器
uv run uvicorn app.main:app --reload

# 数据库迁移
uv run alembic revision --autogenerate -m "message"
uv run alembic upgrade head

# 运行测试
uv run pytest

# 代码格式化
uv run black .
uv run ruff check .
```

#### 前端命令
```bash
# 开发服务器
yarn dev

# 构建
yarn build

# 类型检查
yarn tsc --noEmit

# Lint
yarn eslint .
```

#### 数据库命令
```bash
# 连接数据库
psql -U postgres -d project_alpha

# 查看数据库列表
psql -U postgres -c "\l"

# 查看表
psql -U postgres -d project_alpha -c "\dt"

# 启动/停止 PostgreSQL 服务
# macOS:
brew services start postgresql@18
brew services stop postgresql@18

# Linux:
sudo systemctl start postgresql
sudo systemctl stop postgresql
```

### B. 故障排查

#### 数据库连接失败
- 检查 PostgreSQL 服务是否运行:
  - macOS: `brew services list | grep postgresql`
  - Linux: `sudo systemctl status postgresql`
  - Windows: 在服务管理器中查找 postgresql 服务
- 检查 `.env` 中的 `DATABASE_URL`
- 验证数据库端口: `lsof -i :5432` (macOS/Linux) 或 `netstat -an | findstr 5432` (Windows)
- 尝试手动连接: `psql -U postgres -d project_alpha`

#### 前端 API 调用失败
- 检查后端是否运行: `curl http://localhost:8000/health`
- 检查 CORS 配置
- 查看浏览器控制台错误

---

**文档结束**
