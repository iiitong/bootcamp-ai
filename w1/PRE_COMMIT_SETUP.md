# Pre-commit Setup Guide

这个项目使用 pre-commit 在提交代码前自动运行代码检查和格式化。

## 🚀 快速开始

### 1. 安装 pre-commit

```bash
# 使用 pip 安装
pip install pre-commit

# 或使用 brew (macOS)
brew install pre-commit

# 或使用 uv
uv tool install pre-commit
```

### 2. 在项目中安装 git hooks

```bash
cd /Users/liheng/projects/AI-study/w1
pre-commit install
```

这会在 `.git/hooks/pre-commit` 中安装 hook，每次 `git commit` 时自动运行。

### 3. 手动运行所有检查（可选）

```bash
# 对所有文件运行检查
pre-commit run --all-files

# 只检查已暂存的文件
pre-commit run
```

## 📋 包含的检查项

### 通用检查
- ✂️ 删除行尾空格
- 📄 确保文件以换行符结尾
- ✅ 检查 YAML 格式
- 🚫 检查大文件（>1MB）
- 🔀 检查合并冲突标记
- 📦 格式化 JSON 文件

### Python 后端检查
- 🐍 **Ruff Lint**: 快速的 Python linter（替代 flake8）
- 🎨 **Ruff Format**: 代码格式化（兼容 Black）
- 🔍 **MyPy**: 类型检查

### TypeScript/React 前端检查
- 💅 **Prettier**: 代码格式化
- 🔧 **ESLint**: 代码质量检查

## 🛠️ 使用说明

### 正常 commit 流程

```bash
git add .
git commit -m "feat: add new feature"
```

Pre-commit 会自动运行并修复代码：
- ✅ 如果所有检查通过，commit 正常进行
- 🔧 如果有自动修复，需要重新 `git add` 修改的文件，然后再次 commit
- ❌ 如果有错误无法自动修复，需要手动修复后再 commit

### 跳过 pre-commit（不推荐）

如果确实需要跳过检查：

```bash
git commit -m "message" --no-verify
```

### 更新 pre-commit hooks

```bash
pre-commit autoupdate
```

## 🔧 配置文件

- `.pre-commit-config.yaml`: Pre-commit 主配置
- `backend/ruff.toml`: Python Ruff 配置
- `frontend/.prettierrc`: Prettier 配置（如果存在）
- `frontend/.eslintrc`: ESLint 配置（如果存在）

## 📚 更多信息

- [Pre-commit 官方文档](https://pre-commit.com/)
- [Ruff 文档](https://docs.astral.sh/ruff/)
- [Prettier 文档](https://prettier.io/)
- [ESLint 文档](https://eslint.org/)

## 🐛 故障排除

### Hook 没有运行？

```bash
# 重新安装 hooks
pre-commit uninstall
pre-commit install
```

### 想要禁用某个特定的 hook？

编辑 `.pre-commit-config.yaml`，注释掉或删除不需要的 hook。

### 清除缓存

```bash
pre-commit clean
```
