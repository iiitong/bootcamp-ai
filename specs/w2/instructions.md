# Insructions

## constitution

- 后端使用 Ergonomic Python 风格来编写代码，前端使用 typescript。
- 前后端要有严格的类型标注。
- 使用 pydantic 来定义数据模。
- 所有后端生成的 JSON 数据，使用 camelCase 格式。
- 不需要 authentication，任何用户都可以使用。

## 基本思路

这是一个数据库查询工具，用户可以添加一个 db url，系统会连接到数据库，获取数据库的 metadata，然后将数据库中的 table 和  view 的信息展示出来，然后用户可以自己输入 sql 查询，也可以通过自然语言来生成 sql 查询。

基本想法：
- 数据库连接字符串和数据库的 metadata 都会存储到 sqlite 数据库中，我们可以根据 postgres 的功能来查询系统的 table 和 view 的信息。然后用 LLM 来将这些信息转成 json 个是，然后存储到 sqlite 数据库中，这个信息以后可以复用。
- 当用户使用 LLM 来生成 sql 查询时，我们可以把系统中的表和试图的信息作为 context 传递给 LLM，然后 LLM 会根据这些信息来生成 sql 查询。
- 任何输入的 sql 语句，都需要经过 sqlparser 解析，确保语法正确，并且仅包含 select 语句，如果语法不正确，需要给出错误信息。
    - 如果查询不包含 limit 子句，则默认添加 limit 1000 子句。
- 输出格式是 json，前端将其组织成表格，并显示出来。

后端使用 Python (uv) / FastAPI / sqlglot / openai sdk 来实现。 前端使用 React / refine 5 / tailwind / ant design 来实现, 使用 yarn 来作为包管理工具。sql editor 使用 monaco editor 来实现。

OpenAI API key 在环境变量 OPENAI_API_KEY 中。数据库连接和 metadata 存储在 sqlite 数据库中，放在 ~/.db_query/db_query.db 中。

后端 API 需要支持 cors，允许所有 origin。大致 API 如下：

```
# 获取所有已存储的数据库
GET /api/v1/dbs
# 添加一个数据库
PUT /api/v1/dbs/{name}

{
  "url": "postgres://postgres:postgres@localhost:5432/postgres"
}

# 获取一个数据库的 metadata
GET /api/v1/dbs/{name}

# 查询某个数据库的信息
POST /api/v1/dbs/{name}/query

{
  "sql": "SELECT * FROM users"
}

# 根据自然语言生成 sql
POST /api/v1/dbs/{name}/query/natural

{
  "prompt": "查询用户表的所有信息"
}
```

## 补充功能
需要增加一个 查询结果导出的功能，查询之后，点击导出按钮，可以选择导出 csv/json 格式文件。

## 添加 MySQL db 支持

参考 ./w2/db_query/backend 中的 PostgreSQL 实现，实现 MySQL 的 metadata 提取和查询支持，同时自然语言生成 sql 也支持 MySQL。另外需要生成一个生成测试数据库和测试数据的文件来进行 mysql 连接、查询的测试，测试 DB 要包含不少于 5 张表，至少一张表要有大于 1000 条的测试数据，使用 `mysql -u root"` 可以访问到我的数据库。

## 更新 make db-setup & 测试 MySQL db 支持

- 把生成的 scripts/setup_mysql_testdb.sql 移动到 fixtures/ 目录下。
- 现在 make db-setup 没有添加初始化 mysql db 的测试数据，修正一下。
- 在 ./w2/db_query/fixtures/test.rest 中添加 MySQL db 支持的测试用例，然后运行测试。
- 如果后端测试 ok，那么打开后端和前端，使用 playwright 测试前端，确保 MySQL db 的基本功能：
  - 添加 新的数据库 ecommerce_test 为 mysql://root@localhost:3306/ecommerce_test
  - 生成 sql，查询 ecommerce_test

针对 mysql 支持的测试，也请添加相关的单元测试。
