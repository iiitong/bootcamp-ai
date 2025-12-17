# Quickstart: MySQL 数据库支持

**Feature**: 002-mysql-support
**Date**: 2025-12-16

## 前置条件

### 1. MySQL 服务

确保 MySQL 服务正在运行并可通过 root 用户访问：

```bash
# 检查 MySQL 服务状态
mysql -u root -e "SELECT VERSION();"
```

### 2. 创建测试数据库

运行测试数据库创建脚本：

```bash
cd w2/db_query
make db-setup-mysql
# 或者直接运行:
# mysql -u root < fixtures/setup_mysql_testdb.sql
```

### 3. 安装依赖

```bash
cd w2/db_query/backend
pip install -e ".[dev]"
```

## 快速验证

### 1. 启动后端服务

```bash
cd w2/db_query/backend
uvicorn src.main:app --reload
```

### 2. 添加 MySQL 连接

```bash
curl -X PUT "http://localhost:8000/api/v1/dbs/mysql_test" \
  -H "Content-Type: application/json" \
  -d '{"url": "mysql://root@localhost:3306/ecommerce_test"}'
```

预期响应：

```json
{
  "name": "mysql_test",
  "url": "mysql://root:***@localhost:3306/ecommerce_test",
  "dbType": "mysql",
  "tables": [...],
  "views": [],
  "cachedAt": "2025-12-16T..."
}
```

### 3. 执行查询

```bash
curl -X POST "http://localhost:8000/api/v1/dbs/mysql_test/query" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM users LIMIT 5"}'
```

### 4. 自然语言查询

```bash
curl -X POST "http://localhost:8000/api/v1/dbs/mysql_test/query/natural" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "查询订单金额最高的前10个订单"}'
```

## 关键文件

| 文件 | 说明 |
|------|------|
| `backend/src/services/metadata_mysql.py` | MySQL 元数据提取服务 |
| `backend/src/services/query_mysql.py` | MySQL 查询执行器 |
| `backend/src/services/query.py` | SQL 处理器（支持 MySQL 方言） |
| `fixtures/setup_mysql_testdb.sql` | 测试数据库创建脚本 |
| `fixtures/test.rest` | REST API 测试用例（包含 MySQL） |

## 测试命令

```bash
# 运行所有测试
cd w2/db_query/backend
pytest

# 仅运行 MySQL 相关测试
pytest tests/test_metadata_mysql.py tests/test_query_mysql.py -v

# 运行 SQL 处理器测试（包含 MySQL 方言）
pytest tests/test_sql_processor.py -v
```

## 常见问题

### Q: 连接失败 "Access denied"
确保 MySQL 允许 root 用户无密码登录（开发环境）：
```sql
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '';
FLUSH PRIVILEGES;
```

### Q: 中文显示乱码
确保数据库字符集为 UTF-8：
```sql
ALTER DATABASE ecommerce_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Q: 自然语言查询返回错误
检查 `OPENAI_API_KEY` 环境变量是否已设置：
```bash
export OPENAI_API_KEY="your-api-key"
```
