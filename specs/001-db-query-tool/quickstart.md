# 快速入门：数据库查询工具

本指南帮助你在本地快速启动和运行数据库查询工具。

## 前置条件

- Python 3.14+
- Node.js 18+
- yarn
- uv (Python 包管理器)
- PostgreSQL (用于测试的目标数据库)

### 安装 uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 pip
pip install uv
```

## 项目设置

### 1. 克隆仓库并进入目录

```bash
git clone <repository-url>
cd AI-study
git checkout 001-db-query-tool
```

### 2. 后端设置

```bash
cd backend

# 安装依赖
uv sync

# 设置环境变量
export OPENAI_API_KEY="your-openai-api-key"

# 启动开发服务器
uv run uvicorn src.main:app --reload --port 8000
```

后端将在 http://localhost:8000 运行。

访问 http://localhost:8000/docs 查看 API 文档。

### 3. 前端设置

打开新的终端窗口：

```bash
cd frontend

# 安装依赖
yarn install

# 启动开发服务器
yarn dev
```

前端将在 http://localhost:5173 运行。

## 验证安装

### 检查后端健康状态

```bash
curl http://localhost:8000/api/v1/dbs
# 应返回: []
```

### 添加测试数据库

```bash
curl -X PUT http://localhost:8000/api/v1/dbs/testdb \
  -H "Content-Type: application/json" \
  -d '{"url": "postgresql://postgres:postgres@localhost:5432/postgres"}'
```

### 执行测试查询

```bash
curl -X POST http://localhost:8000/api/v1/dbs/testdb/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT version()"}'
```

## 目录结构

```
.
├── backend/
│   ├── pyproject.toml      # Python 项目配置
│   ├── src/
│   │   ├── main.py         # FastAPI 入口
│   │   ├── api/            # API 端点
│   │   ├── models/         # Pydantic 模型
│   │   ├── services/       # 业务逻辑
│   │   └── storage/        # 数据存储
│   └── tests/              # 测试
│
├── frontend/
│   ├── package.json        # Node.js 配置
│   ├── src/
│   │   ├── App.tsx         # 应用入口
│   │   ├── components/     # React 组件
│   │   ├── pages/          # 页面组件
│   │   └── providers/      # Refine providers
│   └── tests/              # 测试
│
└── specs/001-db-query-tool/
    ├── spec.md             # 功能规范
    ├── plan.md             # 实现计划
    ├── research.md         # 技术研究
    ├── data-model.md       # 数据模型
    └── contracts/          # API 契约
```

## 常用命令

### 后端

```bash
# 运行测试
uv run pytest

# 运行类型检查
uv run mypy src

# 格式化代码
uv run ruff format src tests
uv run ruff check --fix src tests
```

### 前端

```bash
# 运行测试
yarn test

# 类型检查
yarn typecheck

# 构建生产版本
yarn build

# 预览生产构建
yarn preview
```

## 配置

### 环境变量

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | (必需) |
| `DB_QUERY_DATA_DIR` | 数据存储目录 | `~/.db_query` |

### SQLite 数据库位置

默认位置: `~/.db_query/db_query.db`

可通过 `DB_QUERY_DATA_DIR` 环境变量修改。

## 故障排除

### 后端无法启动

1. 确保 Python 3.11+ 已安装: `python --version`
2. 确保 uv 已安装: `uv --version`
3. 检查端口 8000 是否被占用: `lsof -i :8000`

### 前端无法连接后端

1. 确保后端正在运行
2. 检查 CORS 配置 (默认允许所有 origin)
3. 确认后端地址: `http://localhost:8000`

### 数据库连接失败

1. 确保 PostgreSQL 正在运行
2. 验证连接 URL 格式: `postgresql://user:pass@host:port/dbname`
3. 检查网络连接和防火墙设置

### OpenAI API 错误

1. 确保 `OPENAI_API_KEY` 已设置
2. 验证 API 密钥有效
3. 检查 API 配额

## 下一步

- 查看 [API 文档](http://localhost:8000/docs)
- 阅读 [spec.md](./spec.md) 了解功能详情
- 阅读 [data-model.md](./data-model.md) 了解数据结构
