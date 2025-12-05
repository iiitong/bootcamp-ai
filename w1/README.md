# Project Alpha - Ticket 管理工具

一个轻量级的 Ticket 管理工具，支持标签分类和高效的搜索过滤功能。

## ✨ 特性

- 📝 **Ticket 管理**: 创建、查看、更新、删除 Tickets
- 🏷️ **标签系统**: 灵活的标签管理和多标签筛选
- 🔍 **强大搜索**: 支持标题和描述的全文搜索
- ⚡ **性能优化**: 使用防抖搜索和分页加载
- 📊 **状态管理**: 清晰的 Ticket 状态跟踪（待处理/已完成）
- 🎨 **现代 UI**: 使用 Tailwind CSS 构建的响应式界面

## 🛠️ 技术栈

### 后端
- **FastAPI** - 现代、快速的 Python Web 框架
- **PostgreSQL** - 可靠的关系型数据库
- **SQLAlchemy 2.0** - 异步 ORM
- **Pydantic** - 数据验证和设置管理
- **asyncpg** - 高性能异步 PostgreSQL 驱动

### 前端
- **React 18** - UI 库
- **TypeScript** - 类型安全
- **Vite** - 快速的构建工具
- **Tailwind CSS** - 实用优先的 CSS 框架
- **Zustand** - 轻量级状态管理
- **Axios** - HTTP 客户端

### 开发工具
- **uv** - Python 包管理器
- **Yarn (Yarn Berry)** - 前端包管理器
- **Ruff** - 快速的 Python linter 和 formatter
- **ESLint + Prettier** - 前端代码质量工具
- **Pre-commit** - Git hooks 管理

## 📋 前置要求

- **Python** 3.13+
- **Node.js** 24+
- **PostgreSQL** 18+
- **uv** (Python 包管理器)
- **Yarn** 4.x (Yarn Berry)

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone <repository-url>
cd w1
```

### 2. 设置数据库

```bash
# 创建主数据库
psql -U postgres -c "CREATE DATABASE project_alpha;"

# 创建测试数据库（可选）
psql -U postgres -c "CREATE DATABASE project_alpha_test;"
```

### 3. 启动后端

```bash
cd backend

# 创建 .env 文件
cp .env.example .env
# 编辑 .env 文件，配置数据库连接

# 安装依赖（uv 会自动创建虚拟环境）
uv sync

# 启动开发服务器
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端服务器将在 http://localhost:8000 启动

### 4. 启动前端

```bash
cd frontend

# 安装依赖
yarn install

# 创建 .env 文件
cp .env.example .env

# 启动开发服务器
yarn dev
```

前端应用将在 http://localhost:5173 启动

### 5. 访问应用

- **前端应用**: http://localhost:5173
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/api/v1/docs
- **健康检查**: http://localhost:8000/health

## 📖 API 文档

FastAPI 自动生成交互式 API 文档：

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc

## 🧪 运行测试

### 后端测试

```bash
cd backend
uv run pytest

# 带覆盖率
uv run pytest --cov=app
```

### 前端测试

```bash
cd frontend
yarn test
```

## 🏗️ 项目结构

```
w1/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── models/         # SQLAlchemy 模型
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # 业务逻辑层
│   │   ├── database.py     # 数据库配置
│   │   └── main.py         # 应用入口
│   ├── tests/              # 测试文件
│   ├── .env                # 环境变量
│   └── pyproject.toml      # Python 项目配置
│
├── frontend/               # React 前端
│   ├── src/
│   │   ├── api/           # API 客户端
│   │   ├── components/    # React 组件
│   │   ├── hooks/         # 自定义 Hooks
│   │   ├── store/         # Zustand 状态管理
│   │   ├── types/         # TypeScript 类型
│   │   └── App.tsx        # 主应用组件
│   ├── .env               # 环境变量
│   └── package.json       # Node.js 项目配置
│
├── specs/                 # 项目规格和文档
│   └── w1/
│       ├── 0001-spec.md   # 需求和设计文档
│       └── 0002-implementation-plan.md  # 实施计划
│
├── .pre-commit-config.yaml # Pre-commit 配置
├── .gitignore             # Git 忽略文件
└── README.md              # 项目说明（本文件）
```

## 🔧 开发工具

### Pre-commit Hooks

项目使用 pre-commit 在提交前自动检查和格式化代码：

```bash
# 安装 pre-commit hooks
pip install pre-commit
pre-commit install

# 或使用提供的脚本
./setup-precommit.sh

# 手动运行所有检查
pre-commit run --all-files
```

### 常用命令

#### 后端

```bash
# 开发服务器
uv run uvicorn app.main:app --reload

# 运行测试
uv run pytest

# 代码格式化和检查
uv run ruff check . --fix
uv run ruff format .

# 类型检查
uv run mypy app
```

#### 前端

```bash
# 开发服务器
yarn dev

# 构建生产版本
yarn build

# 预览生产构建
yarn preview

# 类型检查
yarn tsc --noEmit

# Lint
yarn eslint .

# 格式化
yarn prettier --write .
```

#### 数据库

```bash
# 连接数据库
psql -U postgres -d project_alpha

# 查看所有表
psql -U postgres -d project_alpha -c "\dt"

# 启动/停止 PostgreSQL (macOS)
brew services start postgresql@18
brew services stop postgresql@18
```

## 🌐 生产部署

### 环境配置

1. 复制生产环境配置模板：
   ```bash
   cp backend/.env.production backend/.env
   cp frontend/.env.production frontend/.env
   ```

2. 更新配置文件中的值：
   - 数据库连接字符串
   - API 端点 URL
   - CORS 设置
   - 密钥和安全设置

### 后端部署

```bash
cd backend

# 安装生产依赖
uv sync --no-dev

# 使用生产服务器运行（如 gunicorn + uvicorn workers）
uv run gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### 前端部署

```bash
cd frontend

# 构建生产版本
yarn build

# dist/ 目录包含可部署的静态文件
# 可以部署到 Nginx、Vercel、Netlify 等
```

## 📚 文档

- [需求和设计文档](./specs/w1/0001-spec.md)
- [实现计划](./specs/w1/0002-implementation-plan.md)
- [Pre-commit 设置指南](./PRE_COMMIT_SETUP.md)
- [快速开始指南](./QUICK_START.md)

## 🐛 故障排查

### 数据库连接失败

- 检查 PostgreSQL 服务是否运行：
  ```bash
  # macOS
  brew services list | grep postgresql

  # Linux
  sudo systemctl status postgresql
  ```

- 验证数据库是否存在：
  ```bash
  psql -U postgres -c "\l" | grep project_alpha
  ```

- 检查 `.env` 文件中的 `DATABASE_URL`

### 前端 API 调用失败

- 确保后端服务器正在运行：
  ```bash
  curl http://localhost:8000/health
  ```

- 检查前端 `.env` 文件中的 `VITE_API_BASE_URL`
- 查看浏览器控制台的网络请求和错误信息
- 验证 CORS 设置

### 依赖安装问题

- 后端：确保使用 Python 3.13+
  ```bash
  python --version
  uv --version
  ```

- 前端：确保使用 Node.js 24+
  ```bash
  node --version
  yarn --version
  ```

## 🤝 贡献

欢迎贡献！请确保：
1. 代码通过所有 pre-commit 检查
2. 添加适当的测试
3. 更新相关文档

## 📄 许可证

[MIT License](LICENSE)

## 👥 作者

- 开发团队

## 🙏 致谢

感谢所有使用的开源项目和工具的贡献者。
