# PostgreSQL MCP Server - 自然语言查询测试用例

本文档包含用于测试 pg-mcp 服务器自然语言到 SQL 转换能力的测试用例。测试用例按数据库规模和查询复杂度分类。

---

## 1. 简单博客系统 (small_blog.sql)

### Schema 概览
- **表**: users, posts, tags, post_tags, comments
- **视图**: recent_posts, user_stats
- **自定义类型**: post_status (draft/published/archived), user_role (reader/author/admin)

---

### 1.1 基础查询 (Level 1 - 单表简单查询)

| ID | 自然语言问题 | 预期 SQL 关键要素 |
|----|-------------|------------------|
| B-001 | 列出所有用户 | `SELECT * FROM users` |
| B-002 | 查看所有标签 | `SELECT * FROM tags` |
| B-003 | 有多少篇文章？ | `SELECT COUNT(*) FROM posts` |
| B-004 | 显示所有已发布的文章 | `WHERE status = 'published'` |
| B-005 | 查找用户名是 alice 的用户 | `WHERE username = 'alice'` |
| B-006 | 列出所有管理员用户 | `WHERE role = 'admin'` |
| B-007 | 显示浏览量最高的 5 篇文章 | `ORDER BY view_count DESC LIMIT 5` |
| B-008 | 最近发布的文章是哪一篇？ | `ORDER BY published_at DESC LIMIT 1` |
| B-009 | 有多少条待审核的评论？ | `WHERE is_approved = FALSE`, `COUNT(*)` |
| B-010 | 列出所有草稿状态的文章 | `WHERE status = 'draft'` |

---

### 1.2 中等查询 (Level 2 - 多表关联、聚合)

| ID | 自然语言问题 | 预期 SQL 关键要素 |
|----|-------------|------------------|
| B-011 | 每个作者发布了多少篇文章？ | `JOIN users`, `GROUP BY`, `COUNT(*)` |
| B-012 | Alice 写了哪些文章？ | `JOIN users ON author_id`, `WHERE username = 'alice'` |
| B-013 | 哪篇文章的评论最多？ | `JOIN comments`, `GROUP BY`, `ORDER BY COUNT(*) DESC` |
| B-014 | 每个标签下有多少篇文章？ | `JOIN post_tags`, `GROUP BY tag_id`, `COUNT(*)` |
| B-015 | Python 标签下的所有文章 | `JOIN post_tags JOIN tags`, `WHERE name = 'Python'` |
| B-016 | 显示每篇文章及其作者名称 | `JOIN users`, `SELECT posts.title, users.display_name` |
| B-017 | 哪些用户从未发表过文章？ | `LEFT JOIN posts`, `WHERE posts.id IS NULL` |
| B-018 | 统计每种文章状态的数量 | `GROUP BY status`, `COUNT(*)` |
| B-019 | 哪些文章没有任何评论？ | `LEFT JOIN comments`, `WHERE comments.id IS NULL` |
| B-020 | 每个作者的总浏览量是多少？ | `GROUP BY author_id`, `SUM(view_count)` |

---

### 1.3 高级查询 (Level 3 - 复杂关联、子查询、窗口函数)

| ID | 自然语言问题 | 预期 SQL 关键要素 |
|----|-------------|------------------|
| B-021 | 显示每篇文章的标签列表（用逗号分隔） | `STRING_AGG()` 或 `ARRAY_AGG()`, 多表 JOIN |
| B-022 | 找出同时拥有 Python 和 Tutorial 标签的文章 | 多条件 JOIN 或 INTERSECT |
| B-023 | 哪些作者的文章平均浏览量超过 1000？ | `GROUP BY`, `HAVING AVG(view_count) > 1000` |
| B-024 | 列出评论数排名前 3 的文章及评论数 | 子查询或 JOIN, `LIMIT 3` |
| B-025 | 显示嵌套评论（回复其他评论的评论） | `WHERE parent_id IS NOT NULL` |
| B-026 | 每个用户最近的一次登录时间和发表的最后一篇文章 | 多个聚合函数 `MAX()` |
| B-027 | 计算每篇已发布文章的评论数，包括 0 评论的文章 | `LEFT JOIN`, `COALESCE(COUNT, 0)` |
| B-028 | 找出在过去 7 天内发布的文章 | `WHERE published_at >= CURRENT_DATE - INTERVAL '7 days'` |
| B-029 | 显示每个用户的文章数和评论数 | 多个 LEFT JOIN, 聚合 |
| B-030 | 哪些标签从未被使用过？ | `LEFT JOIN post_tags`, `WHERE post_id IS NULL` |

---

## 2. 电商平台 (medium_ecommerce.sql)

### Schema 概览
- **表**: categories, suppliers, products, product_variants, inventory, customers, addresses, orders, order_items, payments, shipments, coupons, order_coupons, reviews, carts, cart_items
- **视图**: product_catalog, customer_orders_summary, daily_sales, top_products, low_stock_products
- **自定义类型**: order_status, payment_status, payment_method, shipping_method, product_status, address_type

---

### 2.1 基础查询 (Level 1)

| ID | 自然语言问题 | 预期 SQL 关键要素 |
|----|-------------|------------------|
| E-001 | 列出所有商品分类 | `SELECT * FROM categories` |
| E-002 | 有多少个活跃商品？ | `WHERE status = 'active'`, `COUNT(*)` |
| E-003 | 显示价格最高的 10 个商品 | `ORDER BY price DESC LIMIT 10` |
| E-004 | 有多少已完成的订单？ | `WHERE status = 'delivered'`, `COUNT(*)` |
| E-005 | 列出所有供应商 | `SELECT * FROM suppliers` |
| E-006 | 查看今天的订单 | `WHERE DATE(created_at) = CURRENT_DATE` |
| E-007 | 有多少注册客户？ | `SELECT COUNT(*) FROM customers` |
| E-008 | 显示所有促销券 | `SELECT * FROM coupons` |
| E-009 | 哪些商品缺货了？ | `WHERE status = 'out_of_stock'` |
| E-010 | 列出所有精选商品 | `WHERE is_featured = TRUE` |

---

### 2.2 中等查询 (Level 2)

| ID | 自然语言问题 | 预期 SQL 关键要素 |
|----|-------------|------------------|
| E-011 | 每个分类下有多少商品？ | `GROUP BY category_id`, `COUNT(*)` |
| E-012 | 显示手机类别下的所有商品 | `JOIN categories`, `WHERE name = 'Smartphones'` |
| E-013 | 哪个客户的订单总额最高？ | `GROUP BY customer_id`, `SUM(total_amount)`, `ORDER BY DESC LIMIT 1` |
| E-014 | 每种支付方式的订单数量 | `JOIN payments`, `GROUP BY payment_method` |
| E-015 | 显示库存低于补货点的商品 | `JOIN inventory`, `WHERE quantity <= reorder_level` |
| E-016 | 每个供应商提供多少种商品？ | `GROUP BY supplier_id`, `COUNT(*)` |
| E-017 | 最近 30 天的销售总额是多少？ | `WHERE created_at >= NOW() - INTERVAL '30 days'`, `SUM(total_amount)` |
| E-018 | 哪些客户还没有下过订单？ | `LEFT JOIN orders`, `WHERE orders.id IS NULL` |
| E-019 | 显示每个订单的商品数量 | `JOIN order_items`, `GROUP BY order_id`, `SUM(quantity)` |
| E-020 | 列出平均评分高于 4 的商品 | `JOIN reviews`, `GROUP BY`, `HAVING AVG(rating) > 4` |

---

### 2.3 高级查询 (Level 3)

| ID | 自然语言问题 | 预期 SQL 关键要素 |
|----|-------------|------------------|
| E-021 | 计算每个月的销售额和订单数 | `DATE_TRUNC('month')`, `GROUP BY`, `SUM`, `COUNT` |
| E-022 | 找出重复购买同一商品的客户 | 复杂 JOIN, `HAVING COUNT(DISTINCT order_id) > 1` |
| E-023 | 哪些商品的实际库存与系统记录不符？ | 需要审计逻辑，可能涉及子查询 |
| E-024 | 计算每个客户的终身价值 (LTV) | `SUM(total_amount)`, 排除 cancelled/refunded |
| E-025 | 显示每个商品的销售排名 | `RANK()` 或 `ROW_NUMBER()` 窗口函数 |
| E-026 | 哪些优惠券被使用最多？ | `JOIN order_coupons`, `GROUP BY`, `ORDER BY COUNT DESC` |
| E-027 | 计算商品的退货率 | 涉及 order_status 比较, 百分比计算 |
| E-028 | 分析客户的购物篮大小分布 | 子查询计算每单商品数, 然后统计分布 |
| E-029 | 找出经常一起购买的商品组合 | 关联分析, 自连接 order_items |
| E-030 | 预测下月需要补货的商品 | 基于销售速度和当前库存计算 |
| E-031 | 计算每个分类的平均订单金额 | 多表 JOIN, `AVG()` |
| E-032 | 显示运送时间超过 7 天的订单 | `shipments.shipped_at - orders.created_at`, 时间间隔 |
| E-033 | 哪些客户超过 90 天没有购买了？ | `MAX(order_date)`, `HAVING MAX(...) < NOW() - INTERVAL '90 days'` |
| E-034 | 计算商品的价格弹性（价格变化与销量关系） | 复杂分析查询 |
| E-035 | 列出每个季度的新客户数和老客户购买比例 | 时间序列分析, 窗口函数 |

---

## 3. 企业 ERP 系统 (large_erp.sql)

### Schema 概览
- **模块**: HR（人力资源）、Finance（财务）、Inventory（库存）、CRM（客户关系）、Projects（项目管理）
- **表**: 35+ 张表
- **视图**: employee_directory, department_summary, account_balances, vendor_summary, inventory_status, customer_summary, sales_pipeline, ticket_statistics, project_status_view, employee_workload, ar_aging
- **自定义类型**: 15+ 种枚举类型

---

### 3.1 HR 模块查询

| ID | 自然语言问题 | 预期 SQL 关键要素 |
|----|-------------|------------------|
| H-001 | 列出所有在职员工 | `WHERE employment_status = 'active'` |
| H-002 | 有多少全职员工？ | `WHERE employment_type = 'full_time'`, `COUNT(*)` |
| H-003 | 工程部门有多少人？ | `JOIN departments`, `WHERE name = 'Engineering'` |
| H-004 | 显示每个部门的员工人数 | `GROUP BY department_id`, `COUNT(*)` |
| H-005 | 谁是工资最高的员工？ | `ORDER BY salary DESC LIMIT 1` |
| H-006 | 计算公司的平均工资 | `AVG(salary)` |
| H-007 | 列出最近入职的 10 名员工 | `ORDER BY hire_date DESC LIMIT 10` |
| H-008 | 哪些员工今年请假超过 10 天？ | `JOIN leave_requests`, `SUM(days_requested)`, `HAVING > 10` |
| H-009 | 显示所有待批准的请假申请 | `WHERE status = 'pending'` |
| H-010 | 每个部门的总工资支出是多少？ | `GROUP BY department_id`, `SUM(salary)` |

---

### 3.2 HR 高级查询

| ID | 自然语言问题 | 预期 SQL 关键要素 |
|----|-------------|------------------|
| H-011 | 显示组织架构（每个员工的上级） | 自连接 `employees e1 LEFT JOIN employees e2 ON e1.manager_id = e2.id` |
| H-012 | 计算每个部门的工资预算使用率 | `SUM(salary) / budget * 100` |
| H-013 | 哪些员工拥有 Python 技能且精通程度超过 3？ | `JOIN employee_skills JOIN skills`, 多条件过滤 |
| H-014 | 找出在公司工作超过 5 年的员工 | `WHERE hire_date <= NOW() - INTERVAL '5 years'` |
| H-015 | 按城市统计员工分布 | `GROUP BY city`, `COUNT(*)` |
| H-016 | 显示上个月的考勤异常（迟到或早退） | 时间比较, `attendance` 表分析 |
| H-017 | 计算每个员工的剩余年假天数 | `leave_balances.entitled_days - used_days - pending_days` |
| H-018 | 找出没有下属的管理者 | 子查询或 NOT EXISTS |
| H-019 | 分析各职位的薪资范围和实际分布 | `JOIN positions`, 统计分析 |
| H-020 | 员工技能分布统计（每种技能有多少人掌握） | `JOIN employee_skills JOIN skills`, `GROUP BY skill_id` |

---

### 3.3 财务模块查询

| ID | 自然语言问题 | 预期 SQL 关键要素 |
|----|-------------|------------------|
| F-001 | 显示所有资产类科目 | `WHERE account_type = 'asset'` |
| F-002 | 本月有多少张采购订单？ | `WHERE order_date` 在本月范围 |
| F-003 | 未付款的发票总额是多少？ | `WHERE status IN ('sent', 'overdue')`, `SUM(total_amount - paid_amount)` |
| F-004 | 哪个供应商的采购额最大？ | `JOIN purchase_orders`, `GROUP BY vendor_id`, `SUM` |
| F-005 | 显示逾期的应收账款 | `WHERE status = 'overdue' AND invoice_type = 'receivable'` |
| F-006 | 本季度的费用报销总额 | `WHERE status = 'reimbursed'`, 日期范围过滤 |
| F-007 | 每个员工的报销总额排名 | `GROUP BY employee_id`, `SUM(total_amount)`, `RANK()` |
| F-008 | 显示会计科目余额 | 使用 `account_balances` 视图或计算 debit - credit |
| F-009 | 列出待审批的采购订单（金额超过 10000） | `WHERE status = 'pending' AND total_amount > 10000` |
| F-010 | 按费用类别统计报销金额 | `JOIN expense_items`, `GROUP BY category`, `SUM(amount)` |

---

### 3.4 库存模块查询

| ID | 自然语言问题 | 预期 SQL 关键要素 |
|----|-------------|------------------|
| I-001 | 列出所有仓库 | `SELECT * FROM warehouses` |
| I-002 | 哪些商品库存低于安全库存？ | `WHERE quantity_on_hand <= min_stock_level` |
| I-003 | 每个仓库的库存总值是多少？ | `SUM(quantity_on_hand * unit_cost)`, `GROUP BY warehouse_id` |
| I-004 | 显示今天的库存移动记录 | `WHERE DATE(created_at) = CURRENT_DATE` |
| I-005 | 哪些商品需要补货？ | `WHERE quantity_on_hand <= reorder_point` |
| I-006 | 统计每种移动类型的数量 | `GROUP BY movement_type`, `COUNT(*)` |
| I-007 | 显示库存周转最快的商品（出库最多） | `WHERE movement_type = 'issue'`, `GROUP BY product_id`, `SUM(quantity)` |
| I-008 | 计算仓库间转移的商品总量 | `WHERE movement_type = 'transfer'`, `SUM(quantity)` |
| I-009 | 哪个仓库的商品种类最多？ | `GROUP BY warehouse_id`, `COUNT(DISTINCT product_id)` |
| I-010 | 显示过去 7 天没有任何移动的商品 | 复杂子查询, NOT IN / NOT EXISTS |

---

### 3.5 CRM 模块查询

| ID | 自然语言问题 | 预期 SQL 关键要素 |
|----|-------------|------------------|
| C-001 | 有多少活跃客户？ | `WHERE is_active = TRUE`, `COUNT(*)` |
| C-002 | 每个行业有多少客户？ | `GROUP BY industry`, `COUNT(*)` |
| C-003 | 显示所有打开的工单 | `WHERE status IN ('open', 'in_progress')` |
| C-004 | 哪个客户的工单最多？ | `GROUP BY customer_id`, `COUNT(*)`, `ORDER BY DESC LIMIT 1` |
| C-005 | 本月新增了多少潜在客户？ | `leads` 表, 日期范围过滤 |
| C-006 | 销售漏斗各阶段的商机数量和金额 | `GROUP BY stage`, `SUM(expected_amount)` |
| C-007 | 显示高优先级的未解决工单 | `WHERE priority IN ('high', 'urgent', 'critical') AND status != 'closed'` |
| C-008 | 每个客户经理负责多少客户？ | `GROUP BY account_manager_id`, `COUNT(*)` |
| C-009 | 潜在客户的转化率是多少？ | `COUNT(converted) / COUNT(*)` 计算 |
| C-010 | 显示过去 30 天的客户活动记录 | `activities` 表, 日期过滤 |

---

### 3.6 CRM 高级查询

| ID | 自然语言问题 | 预期 SQL 关键要素 |
|----|-------------|------------------|
| C-011 | 计算每个客户的生命周期价值 | `SUM` 历史发票金额 |
| C-012 | 分析工单的平均响应时间和解决时间 | `AVG(first_response_at - created_at)` |
| C-013 | 哪些客户的应收账款逾期超过 60 天？ | 使用 `ar_aging` 视图或计算 |
| C-014 | 显示每月的商机赢单率 | `DATE_TRUNC`, `COUNT(won) / COUNT(*)` |
| C-015 | 找出最可能成交的前 10 个商机 | `ORDER BY probability * expected_amount DESC LIMIT 10` |
| C-016 | 分析客户投诉的主要类型 | 可能需要文本分析或分类统计 |
| C-017 | 哪些客户超过 90 天没有互动？ | `MAX(activity_date)`, 时间比较 |
| C-018 | 计算销售团队的配额完成率 | 复杂聚合和比较 |
| C-019 | 显示每个地区的客户分布和收入贡献 | `GROUP BY city/country`, 多指标聚合 |
| C-020 | 预测下季度的销售收入（基于销售漏斗） | 加权概率计算 |

---

### 3.7 项目管理模块查询

| ID | 自然语言问题 | 预期 SQL 关键要素 |
|----|-------------|------------------|
| P-001 | 列出所有进行中的项目 | `WHERE status = 'active'` |
| P-002 | 每个项目有多少任务？ | `GROUP BY project_id`, `COUNT(*)` |
| P-003 | 显示逾期的任务 | `WHERE due_date < CURRENT_DATE AND status != 'done'` |
| P-004 | 哪个员工分配的任务最多？ | `GROUP BY assigned_to`, `COUNT(*)`, `ORDER BY DESC LIMIT 1` |
| P-005 | 本周记录了多少工时？ | `WHERE entry_date` 在本周, `SUM(hours)` |
| P-006 | 每个项目的完成进度是多少？ | `COUNT(done) / COUNT(*)` 计算百分比 |
| P-007 | 显示项目预算使用情况 | `actual_cost / budget * 100` |
| P-008 | 哪些项目超出预算？ | `WHERE actual_cost > budget` |
| P-009 | 每个部门有多少活跃项目？ | `JOIN departments`, `GROUP BY`, `COUNT(*)` |
| P-010 | 显示被阻塞的任务及其原因 | `WHERE status = 'blocked'` |

---

### 3.8 项目管理高级查询

| ID | 自然语言问题 | 预期 SQL 关键要素 |
|----|-------------|------------------|
| P-011 | 计算每个员工的工时利用率 | `SUM(billable_hours) / total_available_hours` |
| P-012 | 分析项目延期的主要原因 | 比较 `target_end_date` 和 `actual_end_date` |
| P-013 | 显示每个项目经理的项目组合表现 | 多项目聚合, 成功率计算 |
| P-014 | 找出资源过载的团队成员 | 分配任务过多, 可能需要配置阈值 |
| P-015 | 计算项目的投资回报率 | 收入与成本比较 (如果有收入数据) |
| P-016 | 显示跨部门协作的项目 | `project_members` 涉及多部门员工 |
| P-017 | 预估项目完成时间（基于当前进度） | 进度外推计算 |
| P-018 | 分析任务优先级分布 | `GROUP BY priority`, `COUNT(*)` |
| P-019 | 显示每个团队成员上周的工作摘要 | `time_entries` 聚合 |
| P-020 | 找出关键路径上的任务 | 复杂依赖分析 |

---

### 3.9 跨模块复杂查询

| ID | 自然语言问题 | 预期 SQL 关键要素 |
|----|-------------|------------------|
| X-001 | 显示每个部门的员工数、项目数和平均工资 | 多表 JOIN 和聚合 |
| X-002 | 哪些客户有未解决的工单和逾期的应收账款？ | `tickets` + `invoices` JOIN |
| X-003 | 分析采购订单和库存水平的关系 | PO + inventory 多表分析 |
| X-004 | 计算每个客户的项目收入和支持成本 | 跨项目和工单的成本分析 |
| X-005 | 显示高绩效销售人员的客户留存率 | 员工业绩 + 客户活跃度 |
| X-006 | 预测下月的人力资源需求（基于项目计划） | 项目 + 人员配置分析 |
| X-007 | 分析库存周转率和采购周期的关系 | 库存移动 + 采购订单时间分析 |
| X-008 | 计算每个产品线的盈利能力 | 收入 - 成本（可能涉及多模块数据） |
| X-009 | 显示员工技能与项目需求的匹配度 | 技能矩阵分析 |
| X-010 | 生成综合管理仪表板数据 | 多模块 KPI 聚合 |

---

## 4. 测试场景与边界条件

### 4.1 SQL 安全测试 (应被拒绝的查询)

| ID | 自然语言问题 | 预期结果 |
|----|-------------|---------|
| S-001 | 删除所有用户 | 拒绝执行，返回安全错误 |
| S-002 | 更新 Alice 的密码为 123456 | 拒绝执行 |
| S-003 | 在 users 表中插入一条新记录 | 拒绝执行 |
| S-004 | 删除 posts 表 | 拒绝执行 |
| S-005 | 执行 pg_sleep(10) | 拒绝执行，检测到危险函数 |
| S-006 | 将查询结果导出到文件 | 拒绝执行 |

---

### 4.2 模糊查询测试

| ID | 自然语言问题 | 预期行为 |
|----|-------------|---------|
| A-001 | 销售情况怎么样？ | 询问用户需要哪种销售指标 |
| A-002 | 显示最近的数据 | 询问用户想查看哪个表的数据 |
| A-003 | 老用户有哪些？ | 询问"老用户"的定义（注册时间？购买次数？） |
| A-004 | 表现好的员工 | 询问评判标准 |

---

### 4.3 错误处理测试

| ID | 自然语言问题 | 预期行为 |
|----|-------------|---------|
| ERR-001 | 查询 nonexistent_table 表 | 返回 UNKNOWN_DATABASE 或表不存在错误 |
| ERR-002 | [空查询] | 返回需要提供查询内容的提示 |
| ERR-003 | asdfghjkl | 返回无法理解查询意图的错误 |
| ERR-004 | 查询100亿条记录 | 应用 LIMIT 限制，返回提示 |

---

## 5. 预期 SQL 示例

### 5.1 Blog 数据库示例

```sql
-- B-011: 每个作者发布了多少篇文章？
SELECT
    u.username,
    u.display_name,
    COUNT(p.id) AS post_count
FROM users u
LEFT JOIN posts p ON u.id = p.author_id AND p.status = 'published'
WHERE u.role = 'author'
GROUP BY u.id, u.username, u.display_name
ORDER BY post_count DESC;

-- B-021: 显示每篇文章的标签列表
SELECT
    p.title,
    STRING_AGG(t.name, ', ' ORDER BY t.name) AS tags
FROM posts p
LEFT JOIN post_tags pt ON p.id = pt.post_id
LEFT JOIN tags t ON pt.tag_id = t.id
WHERE p.status = 'published'
GROUP BY p.id, p.title
ORDER BY p.published_at DESC;
```

### 5.2 E-commerce 数据库示例

```sql
-- E-021: 计算每个月的销售额和订单数
SELECT
    DATE_TRUNC('month', created_at) AS month,
    COUNT(DISTINCT id) AS order_count,
    SUM(total_amount) AS total_sales
FROM orders
WHERE status NOT IN ('cancelled', 'refunded')
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month DESC;

-- E-025: 显示每个商品的销售排名
SELECT
    p.name,
    p.sku,
    SUM(oi.quantity) AS total_sold,
    RANK() OVER (ORDER BY SUM(oi.quantity) DESC) AS sales_rank
FROM products p
JOIN order_items oi ON p.id = oi.product_id
JOIN orders o ON oi.order_id = o.id
WHERE o.status NOT IN ('cancelled', 'refunded')
GROUP BY p.id, p.name, p.sku
ORDER BY sales_rank;
```

### 5.3 ERP 数据库示例

```sql
-- H-011: 显示组织架构
SELECT
    e.employee_number,
    e.first_name || ' ' || e.last_name AS employee_name,
    d.name AS department,
    p.title AS position,
    m.first_name || ' ' || m.last_name AS manager_name
FROM employees e
LEFT JOIN departments d ON e.department_id = d.id
LEFT JOIN positions p ON e.position_id = p.id
LEFT JOIN employees m ON e.manager_id = m.id
WHERE e.employment_status = 'active'
ORDER BY d.name, e.last_name;

-- X-001: 显示每个部门的员工数、项目数和平均工资
SELECT
    d.name AS department,
    COUNT(DISTINCT e.id) AS employee_count,
    COUNT(DISTINCT p.id) AS project_count,
    AVG(e.salary)::DECIMAL(12,2) AS avg_salary
FROM departments d
LEFT JOIN employees e ON d.id = e.department_id AND e.employment_status = 'active'
LEFT JOIN projects p ON d.id = p.department_id AND p.status = 'active'
GROUP BY d.id, d.name
ORDER BY employee_count DESC;
```

---

## 6. 测试执行说明

### 6.1 测试环境准备

1. 加载对应的 fixture SQL 文件到 PostgreSQL
2. 配置 pg-mcp 服务器连接
3. 确保 OpenAI API 密钥有效

### 6.2 测试方法

1. **单元测试**: 验证 SQL 解析和安全检查
2. **集成测试**: 端到端自然语言到结果的验证
3. **回归测试**: 确保更新不影响现有功能

### 6.3 验收标准

- Level 1 查询: 100% 准确率
- Level 2 查询: >= 95% 准确率
- Level 3 查询: >= 85% 准确率
- 安全测试: 100% 正确拒绝
- 平均响应时间 < 5 秒

---

## 7. 版本历史

| 版本 | 日期 | 修改内容 |
|------|------|---------|
| 1.0 | 2026-01-11 | 初始版本 |
