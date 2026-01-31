# Code Review Agent 设计文档

## 概述

基于 `simple-agent` SDK 构建一个专注于代码审查的 AI Agent。

**核心设计原则：Agent 只提供 System Prompt 和 Tools，整个审查过程由 LLM 自主驱动。**

## 目标

1. 提供多种代码审查入口：未提交更改、特定 commit、分支比较、Pull Request
2. LLM 自主识别用户意图并选择合适的工具调用
3. LLM 自主决定是否需要读取完整文件上下文
4. LLM 自主生成结构化、可操作的审查反馈

## 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                        LLM (Core Driver)                        │
│  - 解析用户意图                                                   │
│  - 决定工具调用顺序                                               │
│  - 分析代码变更                                                   │
│  - 生成审查报告                                                   │
├─────────────────────────────────────────────────────────────────┤
│                     Code Review Agent                           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  System Prompt (prompts/system.md)                          ││
│  │  - 定义 LLM 的角色和行为规范                                  ││
│  │  - 提供工具使用指南和示例                                     ││
│  │  - 规定审查方法论和输出格式                                   ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Tools (Passive, LLM-Invoked)                               ││
│  │  ┌──────────────┐ ┌──────────────┐                          ││
│  │  │  read_file   │ │  write_file  │                          ││
│  │  └──────────────┘ └──────────────┘                          ││
│  │  ┌──────────────┐ ┌──────────────┐                          ││
│  │  │  git_command │ │  gh_command  │                          ││
│  │  └──────────────┘ └──────────────┘                          ││
│  └─────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│  simple-agent SDK (Infrastructure)                              │
│  - Agent Loop: 执行 LLM ↔ Tools 的交互循环                       │
│  - Tool Registry: 注册和管理工具                                 │
│  - Tool Executor: 执行 LLM 请求的工具调用                        │
│  - LLM Client: 与 LLM API 通信                                  │
└─────────────────────────────────────────────────────────────────┘
```

**职责边界：**

| 组件 | 职责 | 不做什么 |
|------|------|---------|
| **Agent 代码** | 加载 prompt、注册 tools、启动循环 | 不解析用户输入、不决定调用顺序 |
| **System Prompt** | 定义 LLM 行为规范、提供决策指南 | 不包含硬编码流程 |
| **Tools** | 被动执行、返回结果 | 不做业务逻辑判断 |
| **LLM** | 理解意图、决策、调用工具、生成输出 | 核心驱动者 |

## 用户场景与 LLM 决策

以下展示 LLM 如何根据用户输入自主决策：

| 用户输入示例 | LLM 理解的意图 | LLM 选择的工具调用 |
|-------------|---------------|-------------------|
| "帮我 review 当前代码" | 审查未提交更改 | `git_command(diff)` + `git_command(diff --cached)` |
| "帮我 review 当前 branch 新代码" | 分支与 main 比较 | `git_command(diff main...HEAD)` |
| "帮我 review commit 13bad5 之后的代码" | 从 commit 到 HEAD | `git_command(diff 13bad5..HEAD)` |
| "帮我 review commit abc123" | 单个 commit | `git_command(show abc123)` |
| "帮我 review PR #42" | Pull Request | `gh_command(pr diff 42)` |

**LLM 的决策是动态的**，不是预定义的映射。LLM 会根据：
- 用户的具体表述
- 工具调用的返回结果
- 上下文需要

自主决定下一步行动。

## 工具定义

Agent 代码只负责定义和注册这些工具，具体何时调用由 LLM 决定。

### 1. read_file

```typescript
const readFileTool = defineTool({
  name: "read_file",
  description: "读取指定文件的内容。用于获取代码上下文，理解完整的代码逻辑。",
  schema: z.object({
    path: z.string().describe("相对于当前工作目录的文件路径"),
    start_line: z.number().optional().describe("起始行号（1-based）"),
    end_line: z.number().optional().describe("结束行号（1-based）"),
  }),
  execute: async (args) => {
    // 纯粹的文件读取，不含业务逻辑
  },
})
```

### 2. write_file

```typescript
const writeFileTool = defineTool({
  name: "write_file",
  description: "将内容写入指定文件。用于保存审查报告。",
  schema: z.object({
    path: z.string().describe("相对于当前工作目录的文件路径"),
    content: z.string().describe("要写入的文件内容"),
  }),
  execute: async (args) => {
    // 纯粹的文件写入，不含业务逻辑
  },
})
```

### 3. git_command

```typescript
const gitCommandTool = defineTool({
  name: "git_command",
  description: "执行 git 命令获取代码变更和仓库信息。只允许读取操作。",
  schema: z.object({
    command: z.string().describe("git 子命令（不含 'git' 前缀）"),
  }),
  execute: async (args) => {
    // 安全检查 + 命令执行
    // 不含业务逻辑，只是执行命令并返回结果
  },
})
```

### 4. gh_command

```typescript
const ghCommandTool = defineTool({
  name: "gh_command",
  description: "执行 GitHub CLI 命令获取 PR 信息。只允许读取操作。",
  schema: z.object({
    command: z.string().describe("gh 子命令（不含 'gh' 前缀）"),
  }),
  execute: async (args) => {
    // 白名单检查 + 命令执行
    // 不含业务逻辑，只是执行命令并返回结果
  },
})
```

## 项目结构

```
w6/code-review-agent/
├── src/
│   ├── index.ts              # 主入口，创建 Agent
│   └── tools/
│       ├── read-file.ts      # 文件读取工具
│       ├── write-file.ts     # 文件写入工具
│       ├── git-command.ts    # Git 命令工具（含安全检查）
│       └── gh-command.ts     # GitHub CLI 工具（含白名单）
├── prompts/
│   └── system.md             # 系统提示词（定义 LLM 行为）
├── examples/
│   └── basic.ts              # 基础使用示例
├── package.json
├── tsconfig.json
└── README.md
```

**注意：没有 parser.ts 或任何输入解析逻辑**，因为所有意图识别都由 LLM 完成。

## Agent 初始化代码

Agent 代码极其简单，只做三件事：
1. 加载 system prompt
2. 注册 tools
3. 启动 agent loop

```typescript
import { createAgent } from "simple-agent"
import { readFileSync } from "node:fs"
import { readFileTool } from "./tools/read-file.js"
import { writeFileTool } from "./tools/write-file.js"
import { gitCommandTool } from "./tools/git-command.js"
import { ghCommandTool } from "./tools/gh-command.js"

const systemPrompt = readFileSync(
  new URL("../prompts/system.md", import.meta.url),
  "utf-8"
)

export function createCodeReviewAgent(options?: {
  model?: string
  onEvent?: (event: AgentEvent) => void
}) {
  return createAgent({
    model: options?.model ?? "gpt-4o",
    systemPrompt,
    tools: [readFileTool, writeFileTool, gitCommandTool, ghCommandTool],
    maxSteps: 30,
    onEvent: options?.onEvent,
  })
}
```

## LLM 驱动的审查流程

以下是 LLM 自主执行的典型流程（非预定义代码）：

```
用户: "帮我 review 当前 branch 新代码"
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│ LLM 思考：用户想要 review 当前分支相对于 main 的更改          │
│ LLM 决定：先获取 diff                                        │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
LLM 调用: git_command({"command": "diff main...HEAD"})
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│ LLM 分析 diff 输出                                           │
│ LLM 决定：需要读取某些文件的完整上下文                         │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
LLM 调用: read_file({"path": "src/api/handler.ts"})
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│ LLM 结合 diff 和完整文件上下文                                │
│ LLM 识别潜在问题                                             │
│ LLM 决定：是否需要更多上下文（git blame, 其他文件等）          │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
LLM 生成审查报告
```

**关键点：每一步决策都是 LLM 做的，Agent 代码不参与。**

## 工具实现细节

### 安全检查（工具层面）

工具层面只做最基本的安全检查，不做业务逻辑：

```typescript
// git_command 的安全检查
const DANGEROUS_COMMANDS = ["push", "reset --hard", "clean -f", ...]

function isDangerousCommand(command: string): boolean {
  return DANGEROUS_COMMANDS.some((d) => command.includes(d))
}

// 在 execute 中：
if (isDangerousCommand(command)) {
  return { output: "错误：禁止执行危险命令", error: "DANGEROUS_COMMAND" }
}
```

```typescript
// gh_command 的白名单检查
const ALLOWED_SUBCOMMANDS = ["pr", "issue", "api", "repo"]

// 在 execute 中：
const subCommand = command.split(/\s+/)[0]
if (!ALLOWED_SUBCOMMANDS.includes(subCommand)) {
  return { output: "错误：不支持的命令", error: "UNSUPPORTED_COMMAND" }
}
```

### 输出限制

```typescript
const MAX_OUTPUT_LENGTH = 100000 // 100KB

let output = result.stdout
if (output.length > MAX_OUTPUT_LENGTH) {
  output = output.substring(0, MAX_OUTPUT_LENGTH) + "\n\n[输出已截断...]"
}
```

## 使用示例

```typescript
import { createCodeReviewAgent } from "code-review-agent"
import { createSession } from "simple-agent"

const agent = createCodeReviewAgent({
  onEvent: (event) => {
    if (event.type === "text") process.stdout.write(event.text)
    if (event.type === "tool_call") console.log(`\n[调用工具: ${event.name}]`)
  },
})

const session = createSession()

// LLM 会自主决定如何处理这些请求
await agent.run(session, "帮我 review 当前 branch 新代码")
await agent.run(session, "请详细解释第 2 个问题")
await agent.run(session, "把审查结果保存到 REVIEW.md")
```

## System Prompt 的作用

System Prompt (`prompts/system.md`) 是唯一定义 LLM 行为的地方，包含：

1. **角色定义** - LLM 是谁，做什么
2. **工具说明** - 有哪些工具，怎么用，什么时候用
3. **审查方法论** - 关注什么，如何分析
4. **决策指南** - 如何识别用户意图，如何选择工具
5. **输出格式** - 审查报告的结构
6. **行为边界** - 什么该做，什么不该做

**Agent 代码不包含任何审查逻辑**，所有审查行为都通过 System Prompt 定义。

## 依赖项

```json
{
  "dependencies": {
    "simple-agent": "workspace:*",
    "zod": "^3.23.0"
  },
  "devDependencies": {
    "typescript": "^5.7.0",
    "tsx": "^4.19.0"
  }
}
```

## 测试策略

1. **工具单元测试** - 验证安全检查、输出格式化
2. **集成测试** - 在真实 git 仓库中测试工具
3. **端到端测试** - 验证 LLM 能正确使用工具完成审查

测试重点是工具的正确性，而非 LLM 的决策（LLM 决策由 prompt 质量保证）。
