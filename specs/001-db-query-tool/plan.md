# Implementation Plan: 数据库查询工具

**Branch**: `001-db-query-tool` | **Date**: 2025-12-13 (更新: 2025-12-14) | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-db-query-tool/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

数据库查询工具是一个 Web 应用，支持 PostgreSQL 数据库连接管理、元数据浏览、SQL 查询执行和自然语言生成 SQL。技术栈采用 Python 3.14+ (FastAPI 后端) + TypeScript/React (Refine 前端)。新增功能：支持将查询结果导出为 CSV/JSON 格式文件（前端实现）。

## Technical Context

**Language/Version**: Python 3.14+ (后端), TypeScript 5.0+ (前端)
**Primary Dependencies**:
- 后端: FastAPI >=0.109.0, Pydantic >=2.0.0, sqlglot >=24.0.0, openai >=1.3.0, psycopg[binary] >=3.1.0
- 前端: React ^18.2.0, @refinedev/core ^5.x.x, @refinedev/antd ^5.x.x, @monaco-editor/react ^4.6.0, antd ^5.x.x
**Storage**: SQLite (本地存储连接和元数据缓存), PostgreSQL (目标查询数据库)
**Testing**: pytest (后端), vitest (前端)
**Target Platform**: Web (浏览器访问, 前后端分离)
**Project Type**: Web 应用 (frontend + backend 分离)
**Performance Goals**:
- 查询结果 5 秒内显示 (1000 行以下)
- 导出 2 秒内完成下载 (1000 行以内)
**Constraints**:
- 只允许 SELECT 查询
- 最大返回 1000 行
- 导出范围为当前显示结果（最多 1000 行）
**Scale/Scope**: 单用户本地使用，支持多个数据库连接

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 | 状态 | 说明 |
|------|------|------|
| 简洁性 | ✅ PASS | 导出功能在前端实现，不增加后端复杂度 |
| 可测试性 | ✅ PASS | 导出逻辑为纯函数，易于单元测试 |
| 技术选型 | ✅ PASS | 使用标准 Web API (Blob, URL.createObjectURL) |
| 架构一致性 | ✅ PASS | 遵循现有前后端分离模式 |

**Pre-design Gate**: ✅ PASSED
**Post-design Gate**: ✅ PASSED (2025-12-14 更新)

## Project Structure

### Documentation (this feature)

```text
specs/001-db-query-tool/
├── plan.md              # 本文件 (/speckit.plan 输出)
├── research.md          # Phase 0 技术研究
├── data-model.md        # Phase 1 数据模型
├── quickstart.md        # Phase 1 快速入门
├── contracts/           # Phase 1 API 契约
│   └── openapi.yaml
└── tasks.md             # Phase 2 任务分解 (/speckit.tasks 生成)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml       # Python 项目配置 (uv)
├── src/
│   ├── main.py          # FastAPI 入口
│   ├── api/             # API 端点
│   │   └── v1/
│   │       ├── databases.py
│   │       └── queries.py
│   ├── models/          # Pydantic 模型
│   ├── services/        # 业务逻辑
│   │   ├── connection.py
│   │   ├── metadata.py
│   │   ├── query.py
│   │   └── text_to_sql.py
│   └── storage/         # SQLite 存储
└── tests/
    ├── unit/
    └── integration/

frontend/
├── package.json         # Node.js 配置
├── src/
│   ├── App.tsx          # 应用入口
│   ├── components/      # React 组件
│   │   ├── SqlEditor.tsx
│   │   ├── ResultTable.tsx
│   │   ├── ExportButtons.tsx  # 新增: 导出按钮组件
│   │   └── MetadataTree.tsx
│   ├── pages/           # 页面组件
│   ├── providers/       # Refine providers
│   ├── utils/           # 工具函数
│   │   └── export.ts    # 新增: CSV/JSON 导出逻辑
│   └── types/           # TypeScript 类型
└── tests/
    └── unit/
        └── export.test.ts  # 新增: 导出功能测试
```

**Structure Decision**: 采用 Web 应用结构 (frontend + backend 分离)。导出功能新增文件:
- `frontend/src/components/ExportButtons.tsx` - 导出按钮 UI 组件
- `frontend/src/utils/export.ts` - CSV/JSON 导出工具函数
- `frontend/tests/unit/export.test.ts` - 导出功能单元测试

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

无违规。导出功能采用最简实现方案：
- 前端直接转换内存数据，无需后端接口
- 使用标准 Web API，无额外依赖
- 纯函数实现，易于测试和维护
