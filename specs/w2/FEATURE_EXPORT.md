# 数据导出功能设计文档

> **项目**: db_query
> **功能**: 查询结果导出
> **最后更新**: 2025-12-23

## 概述

数据导出功能允许用户将 SQL 查询结果导出为 **CSV** 或 **JSON** 格式的文件。该功能采用**纯客户端实现**，无需额外的后端接口支持，所有数据处理均在浏览器端完成。

## 设计目标

1. **简单高效** - 无服务端开销，响应迅速
2. **格式兼容** - 支持 Excel 和常见数据分析工具
3. **国际化支持** - 正确处理中文及 Unicode 字符
4. **良好的用户体验** - 智能显隐，自动命名

---

## 架构设计

### 整体数据流

```
┌──────────────────────────────────────────────────────────────┐
│                        Frontend (React)                       │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│   QueryPage                                                   │
│   ├── SQL Editor (用户输入)                                   │
│   ├── Execute Button → POST /api/v1/dbs/{name}/query         │
│   │                                                           │
│   └── QueryResults Component                                  │
│       ├── Results Table (分页展示)                            │
│       └── ExportButtons Component                             │
│           ├── [CSV] → exportToCSV()                          │
│           │    └── escapeCSVField() + downloadBlob()         │
│           └── [JSON] → exportToJSON()                        │
│                └── JSON.stringify() + downloadBlob()         │
│                                                               │
└──────────────────────────────────────────────────────────────┘
                              ↑
                    QueryResult 数据模型
                              ↓
┌──────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                        │
├──────────────────────────────────────────────────────────────┤
│  POST /api/v1/dbs/{name}/query                               │
│  → 执行 SQL 查询                                              │
│  → 返回 QueryResult { columns, rows, rowCount, executionTimeMs }│
└──────────────────────────────────────────────────────────────┘
```

### 设计思路：客户端导出

**为什么选择客户端导出而非服务端导出？**

| 方面 | 客户端导出 | 服务端导出 |
|------|-----------|-----------|
| 服务器负载 | 无额外负载 | 需要处理文件生成 |
| 响应速度 | 即时（数据已在内存） | 需要网络往返 |
| 实现复杂度 | 简单 | 需要文件流/临时文件管理 |
| 大数据量 | 受浏览器内存限制 | 可流式处理 |
| 适用场景 | 中小结果集 | 超大数据集 |

**结论**：对于本项目的查询工具场景，结果集通常在可控范围内（有 LIMIT 限制），客户端导出是更优解。

---

## 核心文件结构

```
frontend/src/
├── utils/
│   └── export.ts              # 核心导出逻辑
├── components/
│   ├── ExportButtons.tsx      # 导出按钮组件
│   └── QueryResults.tsx       # 查询结果展示（集成导出按钮）
└── types/
    └── index.ts               # QueryResult 类型定义
```

### 关键文件说明

#### 1. `export.ts` - 导出工具函数

```typescript
// 主要导出函数
export function exportToCSV(result: QueryResult, filename?: string): void
export function exportToJSON(result: QueryResult, filename?: string): void

// 辅助函数
function escapeCSVField(field: unknown): string  // CSV 字段转义
function generateFilename(extension: string): string  // 生成时间戳文件名
function downloadBlob(blob: Blob, filename: string): void  // 触发下载
```

#### 2. `ExportButtons.tsx` - UI 组件

```typescript
interface ExportButtonsProps {
  result: QueryResult | null;  // 查询结果数据
  disabled?: boolean;          // 禁用状态
}
```

- 仅在有查询结果时显示
- 结果为空时自动隐藏
- 使用 Ant Design 图标增强可识别性

---

## 导出格式详解

### CSV 格式

**文件扩展名**: `.csv`
**文件命名**: `query_result_YYYYMMDD_HHMMSS.csv`
**编码**: UTF-8 with BOM

#### 关键特性

1. **UTF-8 BOM 支持**
   ```typescript
   const BOM = '\uFEFF';  // Byte Order Mark
   const csvContent = BOM + headers + '\n' + rows;
   ```
   > 确保 Excel 正确识别 UTF-8 编码，避免中文乱码

2. **RFC 4180 标准兼容**
   - 包含逗号的字段自动加引号
   - 字段内的引号转义为双引号：`"` → `""`
   - 保留字段内的换行符

3. **字段转义逻辑**
   ```typescript
   function escapeCSVField(field: unknown): string {
     if (field === null || field === undefined) return '';
     const str = String(field);
     if (str.includes(',') || str.includes('"') || str.includes('\n')) {
       return `"${str.replace(/"/g, '""')}"`;
     }
     return str;
   }
   ```

#### 输出示例

```csv
id,name,description
1,张三,"包含逗号,的描述"
2,李四,"包含""引号""的内容"
```

### JSON 格式

**文件扩展名**: `.json`
**文件命名**: `query_result_YYYYMMDD_HHMMSS.json`
**编码**: UTF-8

#### 关键特性

1. **对象数组格式**
   ```json
   [
     { "column1": "value1", "column2": "value2" },
     { "column1": "value3", "column2": "value4" }
   ]
   ```

2. **可读性优化**
   ```typescript
   JSON.stringify(result.rows, null, 2)  // 2 空格缩进
   ```

3. **类型保真**
   - 字符串、数字、布尔值、null 均按原类型输出
   - 嵌套对象自动序列化

---

## 下载机制

### Blob API 实现

```typescript
function downloadBlob(blob: Blob, filename: string): void {
  // 1. 创建临时 URL
  const url = URL.createObjectURL(blob);

  // 2. 创建隐藏的 <a> 元素并触发点击
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();

  // 3. 清理资源
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
```

**优势**：
- 纯浏览器实现，无需服务器参与
- 支持所有现代浏览器
- 自动清理内存，防止泄漏

### 文件命名策略

```typescript
function generateFilename(extension: string): string {
  const now = new Date();
  const timestamp = now.toISOString()
    .replace(/[-:]/g, '')
    .replace('T', '_')
    .slice(0, 15);
  return `query_result_${timestamp}.${extension}`;
}
// 输出: query_result_20251223_143052.csv
```

**设计考量**：
- 时间戳命名避免覆盖
- 格式清晰，便于识别导出时间
- 无需服务器时间，使用客户端本地时间

---

## 用户体验设计

### 按钮交互

```
┌─────────────────────────────────────────────┐
│  查询结果 (123 行, 耗时 45ms)               │
│  ┌──────────────┐  ┌──────────────┐        │
│  │  📊 导出 CSV │  │  📄 导出 JSON │        │
│  └──────────────┘  └──────────────┘        │
├─────────────────────────────────────────────┤
│  id  │  name  │  email                      │
│  1   │  张三  │  zhang@test.com            │
│  ... │  ...   │  ...                        │
└─────────────────────────────────────────────┘
```

### 智能显隐规则

| 场景 | 按钮状态 |
|------|---------|
| 未执行查询 | 隐藏 |
| 查询中 | 禁用（可见） |
| 查询成功且有数据 | 启用 |
| 查询成功但无数据 | 隐藏 |
| 查询失败 | 隐藏 |

---

## 测试覆盖

测试文件：`frontend/tests/unit/export.test.ts`

### 测试用例分类

1. **CSV 字段转义**
   - null/undefined 处理
   - 特殊字符（逗号、引号、换行）
   - 中文及 Unicode 字符

2. **文件名生成**
   - 时间戳格式正确性
   - 扩展名自动添加

3. **CSV 内容验证**
   - 表头行正确性
   - 数据行格式
   - UTF-8 BOM 存在性

4. **JSON 格式验证**
   - 有效 JSON 语法
   - 缩进格式（2 空格）

5. **下载机制**
   - Blob 对象创建
   - DOM 元素操作
   - 资源清理

---

## 技术选型说明

| 技术点 | 选择 | 理由 |
|--------|------|------|
| 前端框架 | React + TypeScript | 类型安全，组件化 |
| UI 组件 | Ant Design | 统一风格，开箱即用 |
| 测试框架 | Vitest | 快速，与 Vite 集成 |
| 下载实现 | Blob API | 浏览器原生，无依赖 |

---

## 扩展性考虑

### 未来可能的增强方向

1. **更多格式支持**
   - Excel (.xlsx) - 需引入 xlsx 库
   - Parquet - 需 WASM 支持
   - SQL INSERT 语句

2. **大数据量优化**
   - 流式导出 (Web Streams API)
   - 分块处理避免内存溢出
   - 后端流式接口支持

3. **自定义选项**
   - 列选择（部分列导出）
   - 分隔符自定义（CSV）
   - 日期格式化

4. **用户偏好**
   - 记住上次选择的格式
   - 自定义默认文件名模板

---

## 相关文件索引

| 文件路径 | 用途 |
|----------|------|
| `frontend/src/utils/export.ts` | 核心导出逻辑 |
| `frontend/src/components/ExportButtons.tsx` | 导出按钮 UI |
| `frontend/src/components/QueryResults.tsx` | 结果展示组件 |
| `frontend/src/types/index.ts` | TypeScript 类型定义 |
| `frontend/tests/unit/export.test.ts` | 单元测试 |
| `backend/src/models/query.py` | QueryResult 模型定义 |

---

## 总结

数据导出功能采用**客户端导出架构**，通过浏览器原生 API 实现了轻量、高效的数据导出体验。设计上充分考虑了：

- **实用性** - 支持 CSV/JSON 两种主流格式
- **兼容性** - UTF-8 BOM 确保 Excel 正确识别中文
- **标准性** - CSV 格式遵循 RFC 4180 规范
- **用户体验** - 智能显隐、自动命名、即时下载
- **可维护性** - 类型安全、测试覆盖、模块化设计
