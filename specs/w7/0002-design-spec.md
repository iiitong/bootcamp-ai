# GenSlides 设计规格文档

## 1. 概述

本文档基于 [PRD](./0001-prd.md) 定义 GenSlides 的技术设计，包括项目结构、后端架构、API 接口、前端架构和数据模型。

## 2. 项目目录结构

```
w7/gen-slide/
├── backend/                          # Python 后端
│   ├── pyproject.toml                # 项目配置和依赖 (uv)
│   ├── uv.lock                       # uv 锁定文件
│   ├── .env                          # 环境变量（不提交）
│   ├── .env.example                  # 环境变量示例
│   │
│   ├── src/
│   │   └── genslide/                 # Python 包
│   │       ├── __init__.py
│   │       ├── main.py               # FastAPI 应用入口
│   │       ├── config.py             # 配置管理
│   │       │
│   │       ├── api/                  # API 层 - 路由和请求处理
│   │       │   ├── __init__.py
│   │       │   ├── router.py         # 路由注册
│   │       │   ├── projects.py       # 项目相关 API
│   │       │   ├── slides.py         # 幻灯片相关 API
│   │       │   ├── images.py         # 图片相关 API
│   │       │   └── schemas.py        # Pydantic 请求/响应模型
│   │       │
│   │       ├── services/             # 业务层 - 核心业务逻辑
│   │       │   ├── __init__.py
│   │       │   ├── project_service.py    # 项目管理服务
│   │       │   ├── slide_service.py      # 幻灯片管理服务
│   │       │   ├── image_service.py      # 图片生成服务
│   │       │   ├── gemini_client.py      # Google AI SDK 客户端封装
│   │       │   └── cost_service.py       # 成本计算服务
│   │       │
│   │       ├── storage/              # 存储层 - 数据持久化
│   │       │   ├── __init__.py
│   │       │   ├── file_storage.py   # 文件系统操作
│   │       │   └── outline_store.py  # outline.yml 读写
│   │       │
│   │       ├── models/               # 领域模型
│   │       │   ├── __init__.py
│   │       │   ├── project.py        # 项目模型
│   │       │   ├── slide.py          # 幻灯片模型
│   │       │   └── image.py          # 图片模型
│   │       │
│   │       └── utils/                # 工具函数
│   │           ├── __init__.py
│   │           └── hash.py           # blake3 哈希工具
│   │
│   └── tests/                        # 测试目录
│       ├── __init__.py
│       └── test_api.py
│
├── frontend/                         # TypeScript 前端
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   │
│   ├── src/
│   │   ├── main.tsx                  # 应用入口
│   │   ├── App.tsx                   # 根组件
│   │   │
│   │   ├── api/                      # API 客户端
│   │   │   ├── client.ts             # HTTP 客户端封装
│   │   │   ├── projects.ts           # 项目 API
│   │   │   ├── slides.ts             # 幻灯片 API
│   │   │   └── images.ts             # 图片 API
│   │   │
│   │   ├── stores/                   # Zustand 状态管理
│   │   │   ├── projectStore.ts       # 项目状态
│   │   │   ├── slideStore.ts         # 幻灯片状态
│   │   │   └── uiStore.ts            # UI 状态
│   │   │
│   │   ├── components/               # React 组件
│   │   │   ├── layout/
│   │   │   │   ├── Header.tsx        # 顶部栏
│   │   │   │   ├── Sidebar.tsx       # 左侧边栏
│   │   │   │   └── MainArea.tsx      # 主内容区
│   │   │   │
│   │   │   ├── slides/
│   │   │   │   ├── SlideList.tsx     # 幻灯片列表
│   │   │   │   ├── SlideCard.tsx     # 幻灯片卡片
│   │   │   │   └── SlideEditor.tsx   # 幻灯片编辑器
│   │   │   │
│   │   │   ├── images/
│   │   │   │   ├── ImageViewer.tsx   # 图片展示
│   │   │   │   ├── ImageThumbnails.tsx # 缩略图列表
│   │   │   │   └── GenerateButton.tsx  # 生成按钮
│   │   │   │
│   │   │   ├── player/
│   │   │   │   └── FullscreenPlayer.tsx # 全屏播放器
│   │   │   │
│   │   │   └── modals/
│   │   │       └── StylePickerModal.tsx # 风格选择弹窗
│   │   │
│   │   ├── hooks/                    # 自定义 Hooks
│   │   │   ├── useProject.ts
│   │   │   ├── useSlides.ts
│   │   │   └── useDragAndDrop.ts
│   │   │
│   │   └── types/                    # TypeScript 类型定义
│   │       └── index.ts
│   │
│   └── public/
│       └── logo.svg
│
└── data/                             # 数据存储目录（运行时生成）
    ├── slides/
    │   └── <slug>/
    │       └── outline.yml
    └── images/
        ├── <slug>/
        │   └── style.jpg
        └── <sid>/
            └── <blake3_hash>.jpg
```

## 3. 后端架构

### 3.1 分层架构

```
┌─────────────────────────────────────────────────────────┐
│                     API Layer                           │
│  (FastAPI Routes, Request/Response Schemas, Validation) │
├─────────────────────────────────────────────────────────┤
│                   Service Layer                         │
│  (Business Logic, Image Generation, Cost Calculation)   │
├─────────────────────────────────────────────────────────┤
│                   Storage Layer                         │
│  (File System, YAML Read/Write, Image Storage)          │
└─────────────────────────────────────────────────────────┘
```

### 3.2 依赖关系

- **API 层** 依赖 **Service 层**
- **Service 层** 依赖 **Storage 层** 和 **Models**
- **Storage 层** 只处理数据持久化，不包含业务逻辑

## 4. API 接口定义

### 4.1 项目管理 API

#### GET /api/projects/{slug}
获取项目详情。

**路径参数：**
| 参数 | 类型 | 描述 |
|------|------|------|
| slug | string | 项目标识符 |

**响应 200：**
```json
{
  "slug": "hello-world",
  "title": "我的演示文稿",
  "style": {
    "prompt": "赛博朋克风格",
    "image": "/api/images/hello-world/style.jpg"
  } | null,
  "slides": [
    {
      "sid": "slide-001",
      "content": "第一张幻灯片",
      "images": [
        {
          "hash": "abc123",
          "url": "/api/images/slide-001/abc123.jpg",
          "created_at": "2026-02-01T10:00:00Z"
        }
      ],
      "current_hash": "abc123",
      "has_matching_image": true
    }
  ],
  "total_cost": 0.15
}
```

**响应 404：**
```json
{
  "error": "project_not_found",
  "message": "项目不存在"
}
```

---

#### POST /api/projects/{slug}
创建新项目（如果不存在）。

**路径参数：**
| 参数 | 类型 | 描述 |
|------|------|------|
| slug | string | 项目标识符 |

**请求体：**
```json
{
  "title": "我的演示文稿"
}
```

**响应 201：**
```json
{
  "slug": "hello-world",
  "title": "我的演示文稿",
  "style": null,
  "slides": [],
  "total_cost": 0
}
```

---

#### PATCH /api/projects/{slug}
更新项目信息（标题）。

**请求体：**
```json
{
  "title": "新标题"
}
```

**响应 200：**
```json
{
  "slug": "hello-world",
  "title": "新标题"
}
```

---

### 4.2 幻灯片管理 API

#### GET /api/projects/{slug}/slides/{sid}
获取单个幻灯片详情。

**响应 200：**
```json
{
  "sid": "slide-001",
  "content": "幻灯片内容描述",
  "images": [
    {
      "hash": "abc123",
      "url": "/api/images/slide-001/abc123.jpg",
      "created_at": "2026-02-01T10:00:00Z"
    }
  ],
  "current_hash": "abc123",
  "has_matching_image": true
}
```

**响应 404：**
```json
{
  "error": "slide_not_found",
  "message": "幻灯片不存在"
}
```

---

#### POST /api/projects/{slug}/slides
创建新幻灯片。

**请求体：**
```json
{
  "content": "幻灯片内容描述",
  "after_sid": "slide-001"  // 可选，在哪个 slide 后面插入，null 表示末尾
}
```

**响应 201：**
```json
{
  "sid": "slide-002",
  "content": "幻灯片内容描述",
  "images": [],
  "current_hash": "def456",
  "has_matching_image": false
}
```

---

#### PATCH /api/projects/{slug}/slides/{sid}
更新幻灯片内容。

**请求体：**
```json
{
  "content": "更新后的内容"
}
```

**响应 200：**
```json
{
  "sid": "slide-001",
  "content": "更新后的内容",
  "images": [...],
  "current_hash": "xyz789",
  "has_matching_image": false
}
```

---

#### DELETE /api/projects/{slug}/slides/{sid}
删除幻灯片。

**响应 204：** 无内容

---

#### PUT /api/projects/{slug}/slides/order
重新排序幻灯片。

**请求体：**
```json
{
  "order": ["slide-002", "slide-001", "slide-003"]
}
```

**响应 200：**
```json
{
  "order": ["slide-002", "slide-001", "slide-003"]
}
```

---

### 4.3 图片生成 API

#### POST /api/projects/{slug}/slides/{sid}/generate
为幻灯片生成图片。

**请求体：**
```json
{
  "content": "幻灯片内容描述"  // 可选，不传则使用当前 slide 内容
}
```

**响应 202（异步任务已接受）：**
```json
{
  "task_id": "task-uuid-123",
  "status": "pending"
}
```

---

#### GET /api/tasks/{task_id}
查询图片生成任务状态。

**响应 200：**
```json
{
  "task_id": "task-uuid-123",
  "status": "completed",  // pending | processing | completed | failed
  "result": {
    "hash": "abc123",
    "url": "/api/images/slide-001/abc123.jpg",
    "cost": 0.02
  } | null,
  "error": null | "生成失败原因"
}
```

---

### 4.4 风格图片 API

#### POST /api/projects/{slug}/style/generate
生成候选风格图片。

**请求体：**
```json
{
  "prompt": "赛博朋克风格，霓虹灯光"
}
```

**响应 202：**
```json
{
  "task_id": "style-task-uuid",
  "status": "pending"
}
```

---

#### GET /api/tasks/style/{task_id}
查询风格图片生成任务状态。

**响应 200：**
```json
{
  "task_id": "style-task-uuid",
  "status": "completed",
  "result": {
    "candidates": [
      {
        "id": "candidate-1",
        "url": "/api/images/hello-world/style-candidate-1.jpg"
      },
      {
        "id": "candidate-2",
        "url": "/api/images/hello-world/style-candidate-2.jpg"
      }
    ],
    "cost": 0.04
  }
}
```

---

#### POST /api/projects/{slug}/style/select
选择风格图片。

**请求体：**
```json
{
  "candidate_id": "candidate-1",
  "prompt": "赛博朋克风格，霓虹灯光"
}
```

**响应 200：**
```json
{
  "style": {
    "prompt": "赛博朋克风格，霓虹灯光",
    "image": "/api/images/hello-world/style.jpg"
  }
}
```

---

### 4.5 图片访问 API

#### GET /api/images/{path:path}
获取图片文件。

**响应 200：** 图片二进制数据 (image/jpeg)

**响应 404：** 图片不存在

---

### 4.6 成本统计 API

#### GET /api/projects/{slug}/cost
获取项目成本统计。

**响应 200：**
```json
{
  "total_cost": 0.25,
  "breakdown": {
    "style_generation": 0.04,
    "slide_images": 0.21
  },
  "image_count": 12
}
```

---

## 5. 数据模型

### 5.1 outline.yml 完整格式

```yaml
# 项目元数据
title: "幻灯片标题"

# 风格配置（首次设置后存在）
style:
  prompt: "赛博朋克风格，霓虹灯光，未来城市"
  image: "style.jpg"

# 成本记录
cost:
  total: 0.25
  style_generation: 0.04
  slide_images: 0.21

# 幻灯片列表（有序）
slides:
  - sid: "slide-001"
    content: "第一张幻灯片的文字描述"
    created_at: "2026-02-01T10:00:00Z"
    updated_at: "2026-02-01T10:30:00Z"
  - sid: "slide-002"
    content: "第二张幻灯片的文字描述"
    created_at: "2026-02-01T10:05:00Z"
    updated_at: "2026-02-01T10:05:00Z"
```

### 5.2 TypeScript 类型定义

```typescript
// types/index.ts

export interface Project {
  slug: string;
  title: string;
  style: StyleConfig | null;
  slides: Slide[];
  totalCost: number;
}

export interface StyleConfig {
  prompt: string;
  image: string;  // URL
}

export interface Slide {
  sid: string;
  content: string;
  images: SlideImage[];
  currentHash: string;        // 当前内容的 blake3 hash
  hasMatchingImage: boolean;  // 是否有匹配当前 hash 的图片
}

export interface SlideImage {
  hash: string;
  url: string;
  createdAt: string;
}

export interface GenerateTask {
  taskId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result?: {
    hash: string;
    url: string;
    cost: number;
  };
  error?: string;
}

export interface StyleCandidate {
  id: string;
  url: string;
}

export interface CostBreakdown {
  totalCost: number;
  breakdown: {
    styleGeneration: number;
    slideImages: number;
  };
  imageCount: number;
}
```

### 5.3 Python Pydantic 模型

```python
# api/schemas.py

from pydantic import BaseModel
from datetime import datetime

class StyleConfig(BaseModel):
    prompt: str
    image: str

class SlideImage(BaseModel):
    hash: str
    url: str
    created_at: datetime

class SlideResponse(BaseModel):
    sid: str
    content: str
    images: list[SlideImage]
    current_hash: str
    has_matching_image: bool

class ProjectResponse(BaseModel):
    slug: str
    title: str
    style: StyleConfig | None
    slides: list[SlideResponse]
    total_cost: float

class CreateProjectRequest(BaseModel):
    title: str

class UpdateProjectRequest(BaseModel):
    title: str

class CreateSlideRequest(BaseModel):
    content: str
    after_sid: str | None = None

class UpdateSlideRequest(BaseModel):
    content: str

class ReorderSlidesRequest(BaseModel):
    order: list[str]

class GenerateImageRequest(BaseModel):
    content: str | None = None

class GenerateStyleRequest(BaseModel):
    prompt: str

class SelectStyleRequest(BaseModel):
    candidate_id: str
    prompt: str

class TaskResponse(BaseModel):
    task_id: str
    status: str  # pending | processing | completed | failed
    result: dict | None = None
    error: str | None = None

class CostResponse(BaseModel):
    total_cost: float
    breakdown: dict
    image_count: int
```

## 6. 前端状态管理

### 6.1 Project Store

```typescript
// stores/projectStore.ts

interface ProjectState {
  project: Project | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  loadProject: (slug: string) => Promise<void>;
  updateTitle: (title: string) => Promise<void>;
  setStyle: (style: StyleConfig) => void;
}
```

### 6.2 Slide Store

```typescript
// stores/slideStore.ts

interface SlideState {
  selectedSid: string | null;
  selectedImageHash: string | null;
  editingSid: string | null;
  generatingTasks: Map<string, GenerateTask>;

  // Actions
  selectSlide: (sid: string) => void;
  selectImage: (hash: string) => void;
  startEditing: (sid: string) => void;
  stopEditing: () => void;
  createSlide: (content: string, afterSid?: string) => Promise<void>;
  updateSlide: (sid: string, content: string) => Promise<void>;
  deleteSlide: (sid: string) => Promise<void>;
  reorderSlides: (order: string[]) => Promise<void>;
  generateImage: (sid: string) => Promise<void>;
}
```

### 6.3 UI Store

```typescript
// stores/uiStore.ts

interface UIState {
  isStyleModalOpen: boolean;
  isFullscreenPlaying: boolean;
  playStartSid: string | null;

  // Actions
  openStyleModal: () => void;
  closeStyleModal: () => void;
  startPlayback: (startSid: string) => void;
  stopPlayback: () => void;
}
```

## 7. 关键流程

### 7.1 首次打开项目流程

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│ 用户访问 URL │───>│ 检查项目存在? │───>│ 存在: 加载项目   │
└─────────────┘    └──────────────┘    └─────────────────┘
                          │                     │
                          │ 不存在              │
                          ▼                     ▼
                   ┌──────────────┐    ┌─────────────────┐
                   │ 创建空项目    │    │ 检查 style 存在? │
                   └──────────────┘    └─────────────────┘
                          │                     │
                          │                     │ 不存在
                          ▼                     ▼
                   ┌──────────────────────────────────┐
                   │ 弹出风格选择 Modal                │
                   │ 1. 用户输入风格描述               │
                   │ 2. 生成 2 张候选图片              │
                   │ 3. 用户选择一张                  │
                   │ 4. 保存为项目风格                 │
                   └──────────────────────────────────┘
```

### 7.2 图片生成流程

```
┌──────────────┐    ┌──────────────┐    ┌─────────────────┐
│ 用户点击生成  │───>│ POST /generate│───>│ 返回 task_id    │
└──────────────┘    └──────────────┘    └─────────────────┘
                                               │
                                               ▼
                                        ┌─────────────────┐
                                        │ 前端轮询状态     │
                                        │ GET /tasks/{id} │
                                        └─────────────────┘
                                               │
                          ┌────────────────────┼────────────────────┐
                          │                    │                    │
                          ▼                    ▼                    ▼
                   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
                   │ pending     │      │ completed   │      │ failed      │
                   │ 继续轮询     │      │ 更新图片列表 │      │ 显示错误    │
                   └─────────────┘      └─────────────┘      └─────────────┘
```

### 7.3 幻灯片编辑流程

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐
│ 双击 slide  │───>│ 进入编辑模式  │───>│ 显示文本输入框       │
└─────────────┘    └──────────────┘    └─────────────────────┘
                                               │
                                               ▼
                                        ┌─────────────────────┐
                                        │ 用户编辑内容         │
                                        └─────────────────────┘
                                               │
                                               ▼ 失去焦点或回车
                                        ┌─────────────────────┐
                                        │ PATCH /slides/{sid} │
                                        └─────────────────────┘
                                               │
                                               ▼
                                        ┌─────────────────────┐
                                        │ 更新 current_hash    │
                                        │ 检查 has_matching    │
                                        └─────────────────────┘
                                               │
                          ┌────────────────────┴────────────────────┐
                          │                                         │
                          ▼                                         ▼
                   ┌─────────────────┐                       ┌─────────────────┐
                   │ 有匹配图片       │                       │ 无匹配图片       │
                   │ 显示对应图片     │                       │ 显示最新图片     │
                   └─────────────────┘                       │ + 生成按钮      │
                                                             └─────────────────┘
```

## 8. Google AI SDK 集成

### 8.1 依赖安装

```bash
# 使用 uv 安装依赖（在 backend 目录下）
uv sync
```

### 8.2 Gemini 客户端封装

```python
# services/gemini_client.py

from google import genai
from google.genai import types
from PIL import Image
from pathlib import Path
import io

class GeminiImageClient:
    """Google Gemini 图片生成客户端"""

    def __init__(self, api_key: str, model: str = "gemini-3-pro-image-preview"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def generate_image(
        self,
        prompt: str,
        output_path: Path,
        aspect_ratio: str = "16:9",
        image_size: str = "2K",
        style_image: Image.Image | None = None,
    ) -> Path:
        """
        生成图片并保存到指定路径

        Args:
            prompt: 图片描述文本
            output_path: 输出文件路径
            aspect_ratio: 宽高比，如 "16:9", "1:1", "9:16"
            image_size: 图片尺寸，如 "1K", "2K"
            style_image: 可选的风格参考图片

        Returns:
            保存的图片路径
        """
        # 构建请求内容
        contents = [prompt]

        # 如果有风格参考图，添加到请求中
        if style_image is not None:
            contents.insert(0, style_image)
            contents.insert(1, "请参考这张图片的风格，生成以下内容：")

        # 调用 API
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                )
            )
        )

        # 提取并保存图片
        for part in response.parts:
            if part.inline_data is not None:
                image = part.as_image()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                image.save(str(output_path))
                return output_path

        raise RuntimeError("API 响应中未包含图片数据")

    async def generate_style_candidates(
        self,
        prompt: str,
        output_dir: Path,
        count: int = 2,
    ) -> list[Path]:
        """
        生成多张风格候选图片

        Args:
            prompt: 风格描述文本
            output_dir: 输出目录
            count: 生成数量

        Returns:
            生成的图片路径列表
        """
        paths = []
        for i in range(count):
            output_path = output_dir / f"style-candidate-{i + 1}.jpg"
            # 每次生成时稍微变化 prompt 以获得不同结果
            varied_prompt = f"{prompt} (variation {i + 1})"
            await self.generate_image(varied_prompt, output_path)
            paths.append(output_path)
        return paths
```

### 8.3 图片生成服务

```python
# services/image_service.py

from pathlib import Path
from PIL import Image
import asyncio
from uuid import uuid4

from .gemini_client import GeminiImageClient
from ..storage.file_storage import FileStorage
from ..storage.outline_store import OutlineStore
from ..utils.hash import compute_content_hash
from ..config import settings

class ImageService:
    """图片生成业务服务"""

    def __init__(self):
        self.gemini = GeminiImageClient(
            api_key=settings.google_api_key,
            model=settings.image_model,
        )
        self.file_storage = FileStorage()
        self.outline_store = OutlineStore()

        # 任务状态存储（生产环境应使用 Redis 等）
        self._tasks: dict[str, dict] = {}

    async def generate_slide_image(
        self,
        slug: str,
        sid: str,
        content: str,
    ) -> str:
        """
        创建幻灯片图片生成任务

        Returns:
            task_id
        """
        task_id = str(uuid4())
        self._tasks[task_id] = {"status": "pending", "result": None, "error": None}

        # 启动后台任务
        asyncio.create_task(self._do_generate(task_id, slug, sid, content))

        return task_id

    async def _do_generate(
        self,
        task_id: str,
        slug: str,
        sid: str,
        content: str,
    ):
        """执行实际的图片生成"""
        try:
            self._tasks[task_id]["status"] = "processing"

            # 计算内容哈希
            content_hash = compute_content_hash(content)

            # 获取输出路径
            output_path = self.file_storage.get_image_path(sid, content_hash)

            # 加载风格图片（如果存在）
            style_image = None
            outline = self.outline_store.load(slug)
            if outline.get("style", {}).get("image"):
                style_path = self.file_storage.get_style_image_path(slug)
                if style_path.exists():
                    style_image = Image.open(style_path)

            # 生成图片
            await self.gemini.generate_image(
                prompt=content,
                output_path=output_path,
                aspect_ratio=settings.image_aspect_ratio,
                image_size=settings.image_size,
                style_image=style_image,
            )

            # 更新任务状态
            self._tasks[task_id] = {
                "status": "completed",
                "result": {
                    "hash": content_hash,
                    "url": f"/api/images/{sid}/{content_hash}.jpg",
                    "cost": settings.slide_image_cost,
                },
                "error": None,
            }

            # 更新成本
            self.outline_store.add_cost(slug, settings.slide_image_cost)

        except Exception as e:
            self._tasks[task_id] = {
                "status": "failed",
                "result": None,
                "error": str(e),
            }

    def get_task_status(self, task_id: str) -> dict | None:
        """获取任务状态"""
        return self._tasks.get(task_id)
```

## 9. 图片存储与哈希策略

### 9.1 Blake3 哈希计算

```python
# utils/hash.py

import blake3

def compute_content_hash(content: str) -> str:
    """计算内容的 blake3 哈希值，返回 16 字符的十六进制字符串"""
    h = blake3.blake3(content.encode('utf-8'))
    return h.hexdigest()[:16]  # 取前 16 位，足够唯一
```

### 9.2 图片文件组织

```
data/images/
├── hello-world/                    # 项目风格图片
│   ├── style.jpg                   # 最终选中的风格图
│   ├── style-candidate-1.jpg       # 候选图（可选保留）
│   └── style-candidate-2.jpg
│
├── slide-001/                      # slide-001 的所有图片
│   ├── a1b2c3d4e5f6g7h8.jpg       # hash 对应的图片
│   └── i9j0k1l2m3n4o5p6.jpg
│
└── slide-002/
    └── q7r8s9t0u1v2w3x4.jpg
```

## 10. 错误处理

### 10.1 HTTP 错误码

| 状态码 | 含义 | 场景 |
|--------|------|------|
| 200 | 成功 | 正常响应 |
| 201 | 创建成功 | 创建项目/幻灯片 |
| 202 | 已接受 | 异步任务已创建 |
| 204 | 无内容 | 删除成功 |
| 400 | 请求错误 | 参数验证失败 |
| 404 | 未找到 | 项目/幻灯片/图片不存在 |
| 500 | 服务器错误 | 内部错误 |
| 503 | 服务不可用 | AI 服务调用失败 |

### 10.2 错误响应格式

```json
{
  "error": "error_code",
  "message": "用户友好的错误描述",
  "details": {}  // 可选，额外的错误详情
}
```

## 11. 依赖管理与开发命令

### 11.1 后端 pyproject.toml

```toml
[project]
name = "genslide"
version = "0.1.0"
description = "AI-powered slide image generator"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    "google-genai>=1.5.0",
    "pillow>=11.1.0",
    "pyyaml>=6.0.2",
    "blake3>=1.0.4",
    "python-multipart>=0.0.20",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.25.0",
    "httpx>=0.28.0",
    "ruff>=0.9.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/genslide"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### 11.2 后端开发命令

```bash
# 进入后端目录
cd w7/gen-slide/backend

# 初始化项目（首次）
uv init

# 安装依赖
uv sync

# 安装开发依赖
uv sync --extra dev

# 运行开发服务器
uv run uvicorn genslide.main:app --reload --port 3003

# 运行测试
uv run pytest

# 代码检查
uv run ruff check .

# 代码格式化
uv run ruff format .

# 添加新依赖
uv add <package-name>

# 添加开发依赖
uv add --dev <package-name>

# 更新所有依赖到最新版本
uv lock --upgrade
uv sync
```

### 11.3 前端 package.json

```json
{
  "name": "genslide-frontend",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --port 5173",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "zustand": "^5.0.0",
    "@dnd-kit/core": "^6.3.0",
    "@dnd-kit/sortable": "^9.0.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.0",
    "eslint": "^9.0.0",
    "postcss": "^8.5.0",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.7.0",
    "vite": "^6.0.0"
  }
}
```

### 11.4 前端开发命令

```bash
# 进入前端目录
cd w7/gen-slide/frontend

# 安装依赖
pnpm install

# 运行开发服务器
pnpm dev

# 构建生产版本
pnpm build

# 类型检查
pnpm typecheck
```

## 12. 配置项

### 12.1 后端配置 (config.py)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 3003

    # 存储配置
    data_dir: str = "./data"
    slides_dir: str = "./data/slides"
    images_dir: str = "./data/images"

    # AI 配置
    google_api_key: str
    image_model: str = "gemini-3-pro-image-preview"
    image_aspect_ratio: str = "16:9"
    image_size: str = "2K"

    # 成本配置（美元/张）
    style_image_cost: float = 0.02
    slide_image_cost: float = 0.02

    # 轮询配置
    task_poll_interval: int = 1000  # 毫秒
    task_timeout: int = 60000       # 毫秒

    model_config = {"env_file": ".env"}
```

### 12.2 环境变量示例 (.env.example)

```bash
# Google AI API Key (必填)
GOOGLE_API_KEY=your-api-key-here

# 可选配置
# DATA_DIR=./data
# IMAGE_MODEL=gemini-3-pro-image-preview
# IMAGE_ASPECT_RATIO=16:9
# IMAGE_SIZE=2K
```

### 12.3 前端配置

```typescript
// config.ts

export const config = {
  apiBaseUrl: '/api',
  taskPollInterval: 1000,  // ms
  taskTimeout: 60000,      // ms
  playbackInterval: 5000,  // ms, 走马灯间隔
};
```

## 13. 版本历史

| 版本 | 日期 | 描述 |
|------|------|------|
| 0.1 | 2026-02-01 | 初始设计文档 |
| 0.2 | 2026-02-01 | 更新 Google AI SDK 集成，模型使用 gemini-3-pro-image-preview |
| 0.3 | 2026-02-01 | 项目根目录改为 w7/gen-slide，使用 uv 管理依赖，更新至最新版本 |
