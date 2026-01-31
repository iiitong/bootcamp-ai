# Code Review Agent - Codex Code Review

## Overview

本文档是对 `w6/code-review-agent` 项目的代码审查报告，使用 OpenAI Codex CLI 进行审查，对照设计规范 `0003-code-review-agent-design.md` 进行验证。

**审查日期**: 2026-01-31
**审查工具**: OpenAI Codex CLI
**审查范围**: `w6/code-review-agent/` 全部源代码

---

## 设计规范合规性检查

| 要求 | 状态 | 说明 |
|------|------|------|
| Architecture (#1/#4) | ✅ Compliant | `src/index.ts:53` 仅加载 `prompts/system.md` 和注册 tools；无业务逻辑 |
| Four tools (#2) | ✅ Compliant | `read_file`, `write_file`, `git_command`, `gh_command` 均实现 (`src/tools/*.ts`) |
| Project structure (#3) | ✅ Compliant | 目录结构符合预期 (`src/index.ts`, `src/tools/*`, `prompts/system.md`, `examples/*`) |
| Output truncation (#6) | ✅ Compliant | `MAX_OUTPUT_LENGTH = 100000` 已实现 (`src/tools/read-file.ts:6`, `src/tools/git-command.ts:8`, `src/tools/gh-command.ts:8`) |
| Security checks (#5) | ⚠️ **Not Compliant** | 当前实现可被绕过，存在任意命令执行风险 |

---

## Issues Found

### Critical

#### 1. Shell Command Injection in `git_command` / `gh_command`

- **Location**: `src/tools/git-command.ts:73`, `src/tools/gh-command.ts:87`
- **Description**: 通过将不受信任的输入直接插入 `execAsync` 执行，`args.command` 可以包含 `;`, `&&`, 反引号, `$()` 等来运行任意 OS 命令，完全绕过 "dangerous command" 阻止/白名单机制
- **Impact**: 攻击者可以通过构造恶意输入执行任意系统命令
- **Example**: `git_command({ command: "status; cat /etc/passwd" })`

### High

#### 2. Path Traversal in `read_file` / `write_file`

- **Location**: `src/tools/read-file.ts:21`, `src/tools/write-file.ts:17`
- **Description**: 允许路径遍历和绝对路径，`resolve(process.cwd(), args.path)` 没有边界检查
- **Impact**: 可以读取/写入仓库外的文件（如 `.env`, SSH keys, 其他项目文件）
- **Example**: `read_file({ path: "../../../.ssh/id_rsa" })`

#### 3. Incomplete Git Command Blocklist

- **Location**: `src/tools/git-command.ts:11`, `src/tools/git-command.ts:35`
- **Description**: "read-only" 强制执行是部分黑名单，不完整且可绕过
- **Missing blocks**:
  - `reset` (without `--hard`)
  - `checkout`/`switch`/`restore`
  - `pull`, `cherry-pick`, `revert`
  - `submodule update`, `worktree`
  - Options like `-c` can define `!` shell aliases

#### 4. Regex Mismatch for `git checkout -- .`

- **Location**: `src/tools/git-command.ts:16`
- **Description**: 正则表达式 `\./` 无法可靠阻止 `git checkout -- .`
- **Impact**: 允许破坏性地丢弃更改

#### 5. Coarse `gh_command` Whitelist

- **Location**: `src/tools/gh-command.ts:12`, `src/tools/gh-command.ts:15`
- **Description**: 子命令级别的白名单粒度太粗，"dangerous operation" 正则有重大漏洞
- **Issues**:
  - `gh api` 仍可通过 GraphQL mutations 进行修改
  - flags like `-f/-F` (implies POST) 未被阻止
  - `-XPOST` / `--method=POST` 变体未覆盖
  - `pr comment` / `issue comment` 等写操作未阻止

### Medium

#### 6. Missing Line Range Validation

- **Location**: `src/tools/read-file.ts:8`
- **Description**: `start_line/end_line` 输入未验证为正整数或 `start_line <= end_line`
- **Impact**: 负索引、浮点数可能产生意外结果

#### 7. Hidden Error Diagnostics

- **Location**: `src/tools/git-command.ts:90`, `src/tools/gh-command.ts:104`
- **Description**: 错误处理仅使用 `error.message`，未利用 exec 错误附带的结构化 `stderr/stdout`
- **Impact**: 丢失有用的诊断信息

#### 8. Hard Import-time Crash for Missing Prompt

- **Location**: `src/index.ts:14`, `package.json:8`
- **Description**: `systemPrompt` 在模块导入时用 `readFileSync` 加载，`prompts/system.md` 缺失会导致硬崩溃
- **Issue**: `package.json` 未明确保证 `prompts/` 会被打包发布

### Low

#### 9. TypeScript Type Casting

- **Location**: `src/index.ts:57`
- **Description**: 使用 `as Tool[]` 类型转换
- **Suggestion**: 优先使用 `satisfies Tool[]` 或修复底层类型不匹配

#### 10. Brittle Example Code

- **Location**: `examples/basic.ts:47`, `examples/interactive.ts:54`, `examples/interactive.ts:81`
- **Description**: 示例假设 `event.result` 始终是字符串，并直接修改 `session.messages`
- **Note**: 作为演示可接受，但如果 SDK 类型更改会很脆弱

---

## Recommendations

### 1. 命令执行安全

**替换 `exec` 为 `spawn`/`execFile`（无 shell）**

```typescript
import { spawn } from "node:child_process"

// 安全地解析命令到 argv
const [cmd, ...args] = parseCommand(command)
const child = spawn("git", [cmd, ...args], { shell: false })
```

**拒绝任何元字符**

```typescript
const SHELL_METACHARACTERS = /[;&|`$(){}[\]<>!\\'"]/
if (SHELL_METACHARACTERS.test(command)) {
  return { output: "错误：命令包含不允许的字符", error: "INVALID_COMMAND" }
}
```

### 2. 使用允许列表（非阻止列表）

**git_command**:
```typescript
const ALLOWED_GIT_COMMANDS = new Set([
  "diff", "show", "log", "blame", "status",
  "rev-parse", "branch", "ls-files", "ls-tree"
])

// 禁止前导选项如 -c
if (command.startsWith("-")) {
  return { error: "INVALID_COMMAND" }
}

const subCommand = command.split(/\s+/)[0]
if (!ALLOWED_GIT_COMMANDS.has(subCommand)) {
  return { error: "UNSUPPORTED_COMMAND" }
}
```

**gh_command**:
```typescript
const ALLOWED_GH_OPERATIONS = new Set([
  "pr view", "pr diff", "pr list", "pr checks", "pr status",
  "issue view", "issue list",
  "repo view"
])

// 移除或严格限制 "api" 命令
// 如保留，需强制 GET-only，无 fields/mutations
```

### 3. 路径沙盒化

```typescript
import { realpath } from "node:fs/promises"

async function validatePath(inputPath: string): Promise<string> {
  // 拒绝绝对路径
  if (path.isAbsolute(inputPath)) {
    throw new Error("绝对路径不允许")
  }

  const resolved = path.resolve(process.cwd(), inputPath)
  const real = await realpath(resolved)
  const cwd = await realpath(process.cwd())

  // 确保路径在工作目录内
  if (!real.startsWith(cwd + path.sep)) {
    throw new Error("路径遍历不允许")
  }

  return resolved
}
```

**可选：限制 `write_file` 到特定文件名**

```typescript
const ALLOWED_WRITE_PATTERNS = [/^REVIEW.*\.md$/, /^review.*\.md$/i]
```

### 4. 收紧 Zod Schema

```typescript
const schema = z.object({
  path: z.string().min(1),
  start_line: z.number().int().positive().optional(),
  end_line: z.number().int().positive().optional(),
}).refine(
  (data) => !data.start_line || !data.end_line || data.start_line <= data.end_line,
  { message: "start_line must be <= end_line" }
)
```

### 5. 确保 Prompt 文件打包

**package.json**:
```json
{
  "files": [
    "dist",
    "prompts"
  ]
}
```

**或在构建时嵌入**:
```typescript
// 使用 esbuild 或类似工具在构建时将 prompt 内联
const systemPrompt = `# Code Review Agent ...`
```

---

## Overall Assessment

| 方面 | 评估 |
|------|------|
| **架构设计** | ✅ 符合设计规范：简洁的 "prompt + tools" 架构 |
| **代码结构** | ✅ 清晰的模块划分和文件组织 |
| **类型安全** | ⚠️ 基本完善，有小问题（类型转换） |
| **安全性** | ❌ **不符合要求**：命令注入和不完整的白名单/阻止机制破坏了核心安全要求 |
| **错误处理** | ⚠️ 基本完善，可以改进诊断信息 |
| **生产就绪** | ❌ 需要先解决 Critical/High 级别问题 |

### 结论

项目的整体架构和结构设计良好，遵循了设计规范中的 "Agent 只提供 System Prompt 和 Tools" 原则。但当前的工具实现存在严重的安全漏洞：

1. **命令注入**是最严重的问题，必须立即修复
2. **路径遍历**可能导致敏感信息泄露
3. **阻止列表不完整**使得 "read-only" 保证无法实现

**建议优先级**:
1. 🔴 **Critical**: 替换 `exec` 为 `execFile`/`spawn`，实施命令白名单
2. 🟠 **High**: 添加路径沙盒化，完善 git/gh 命令过滤
3. 🟡 **Medium**: 改进输入验证和错误处理
4. 🟢 **Low**: TypeScript 优化和示例代码健壮性

在将此 agent 用于任何包含敏感代码或凭据的环境之前，必须先解决 Critical 和 High 级别的问题。
