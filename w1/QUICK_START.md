# Pre-commit 快速开始

## 一键安装

```bash
# 方式 1: 使用安装脚本（推荐）
cd /Users/liheng/projects/AI-study/w1
./setup-precommit.sh
```

```bash
# 方式 2: 手动安装
pip install pre-commit
pre-commit install
```

## 测试配置

运行一次检查所有文件：

```bash
pre-commit run --all-files
```

## 使用说明

配置已自动生效，每次 `git commit` 时会自动运行检查：

```bash
git add .
git commit -m "feat: your commit message"
```

Pre-commit 会自动：
- ✂️ 删除行尾空格
- 🎨 格式化 Python 代码（Ruff）
- 🔍 检查代码质量（Ruff Lint）
- 💅 格式化前端代码（Prettier）
- 🔧 检查 TypeScript/React（ESLint）
- ✅ 类型检查（MyPy）

## 工具说明

### Ruff（替代 Black + flake8 + isort）
- **10-100倍更快** 的 Python 格式化和检查工具
- 100% 兼容 Black 的格式化风格
- 配置文件：`backend/ruff.toml`

更多信息：详见 `PRE_COMMIT_SETUP.md`
