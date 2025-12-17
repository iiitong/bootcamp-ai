# Implementation Plan: MySQL 数据库支持

**Branch**: `002-mysql-support` | **Date**: 2025-12-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-mysql-support/spec.md`

## Summary

在现有的 PostgreSQL 数据库查询工具基础上增加 MySQL 支持，包括：连接管理、元数据提取、查询执行、自然语言 SQL 生成。同时提供电商领域的测试数据库创建脚本（5 张表，订单表 1000+ 条记录）。技术方案采用策略模式抽象数据库操作，使用 aiomysql 作为异步 MySQL 驱动，sqlglot 支持 MySQL 方言。

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- FastAPI >= 0.109.0 (REST API 框架)
- Pydantic >= 2.0.0 (数据验证)
- sqlglot >= 24.0.0 (SQL 解析，支持 MySQL 方言)
- aiomysql >= 0.2.0 (异步 MySQL 驱动)
- psycopg >= 3.1.0 (现有 PostgreSQL 支持)
- openai >= 1.3.0 (自然语言 SQL 生成)

**Storage**: SQLite (本地元数据缓存，扩展支持 db_type 字段)
**Testing**: pytest, pytest-asyncio
**Target Platform**: Linux/macOS server
**Project Type**: Web application (后端 API)
**Performance Goals**:
- 元数据提取 < 10 秒 (100 张表)
- 简单查询 < 2 秒
- 自然语言 SQL 生成 90% 正确率

**Constraints**:
- MySQL 5.7+ 版本支持
- 后端 API 变更对前端透明
- 仅支持 SELECT/UNION 查询

**Scale/Scope**: 单用户开发工具，支持多数据库连接管理

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

项目未配置具体的 constitution 规则（模板占位符），因此不存在违规项。

- [x] 无强制性原则冲突
- [x] 继续执行 Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/002-mysql-support/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
w2/db_query/backend/
├── src/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理
│   ├── api/v1/
│   │   ├── router.py        # API 路由
│   │   └── databases.py     # 数据库管理端点
│   ├── models/
│   │   ├── database.py      # 数据库连接和元数据模型
│   │   ├── query.py         # 查询请求/响应模型
│   │   └── errors.py        # 错误响应模型
│   ├── services/
│   │   ├── metadata.py      # [修改] PostgreSQL 元数据提取 → 重构为策略模式
│   │   ├── metadata_mysql.py # [新增] MySQL 元数据提取
│   │   ├── query.py         # [修改] SQL 处理器 → 支持 MySQL 方言
│   │   ├── query_mysql.py   # [新增] MySQL 查询执行器
│   │   └── llm.py           # [修改] 自然语言 SQL 生成 → 支持 MySQL
│   └── storage/
│       └── sqlite.py        # [修改] SQLite 存储 → 增加 db_type 字段
└── tests/
    ├── test_sql_processor.py     # [修改] 增加 MySQL 方言测试
    ├── test_storage.py           # [修改] 增加 db_type 测试
    ├── test_metadata_mysql.py    # [新增] MySQL 元数据提取测试
    └── test_query_mysql.py       # [新增] MySQL 查询执行测试

w2/db_query/backend/scripts/
└── setup_mysql_testdb.sql   # [新增] MySQL 测试数据库创建脚本
```

**Structure Decision**: 扩展现有 Web 应用后端结构，新增 MySQL 相关服务文件，保持与 PostgreSQL 实现并行的代码组织方式。

## Complexity Tracking

> 无 Constitution 违规需要记录

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
