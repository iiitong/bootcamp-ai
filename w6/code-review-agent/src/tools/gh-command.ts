import { z } from "zod"
import { defineTool } from "simple-agent"
import { exec } from "node:child_process"
import { promisify } from "node:util"

const execAsync = promisify(exec)

const MAX_OUTPUT_LENGTH = 100000 // 100KB
const COMMAND_TIMEOUT = 60000 // 60 seconds for API calls

// Allowed gh subcommands (read-only operations)
const ALLOWED_SUBCOMMANDS = ["pr", "issue", "api", "repo"]

// Dangerous operations within allowed subcommands
const DANGEROUS_OPERATIONS = [
  /\bpr\s+merge\b/,
  /\bpr\s+close\b/,
  /\bpr\s+reopen\b/,
  /\bpr\s+edit\b/,
  /\bpr\s+create\b/,
  /\bissue\s+close\b/,
  /\bissue\s+reopen\b/,
  /\bissue\s+edit\b/,
  /\bissue\s+create\b/,
  /\bissue\s+delete\b/,
  /\brepo\s+create\b/,
  /\brepo\s+delete\b/,
  /\brepo\s+edit\b/,
  /\brepo\s+rename\b/,
  /\brepo\s+archive\b/,
  /\bapi\s+.*-X\s+(POST|PUT|PATCH|DELETE)\b/i,
  /\bapi\s+.*--method\s+(POST|PUT|PATCH|DELETE)\b/i,
]

function isAllowedCommand(command: string): boolean {
  const trimmed = command.trim()
  const subCommand = trimmed.split(/\s+/)[0]
  return ALLOWED_SUBCOMMANDS.includes(subCommand)
}

function isDangerousOperation(command: string): boolean {
  return DANGEROUS_OPERATIONS.some((pattern) => pattern.test(command))
}

const schema = z.object({
  command: z
    .string()
    .describe("gh 子命令（不含 'gh' 前缀），例如：'pr diff 42'"),
})

export const ghCommandTool = defineTool({
  name: "gh_command",
  description: `执行 GitHub CLI 命令获取 PR 和 Issue 信息。只允许读取操作。
支持的子命令：pr, issue, api, repo
常用命令示例：
- pr list: 列出所有 PR
- pr view <number>: 查看 PR 详情
- pr diff <number>: 查看 PR 的代码差异
- pr checks <number>: 查看 PR 的 CI 状态
- pr status: 查看与当前分支相关的 PR 状态
- issue list: 列出所有 issue
- issue view <number>: 查看 issue 详情
- repo view: 查看当前仓库信息
- api repos/{owner}/{repo}/pulls: 调用 GitHub API`,
  schema,
  execute: async (args) => {
    const command = args.command.trim()

    // Check if subcommand is allowed
    if (!isAllowedCommand(command)) {
      const subCommand = command.split(/\s+/)[0]
      return {
        output: `错误：不支持的命令 '${subCommand}'。只允许以下子命令：${ALLOWED_SUBCOMMANDS.join(", ")}`,
        error: "UNSUPPORTED_COMMAND",
      }
    }

    // Check for dangerous operations
    if (isDangerousOperation(command)) {
      return {
        output: `错误：禁止执行修改操作。只允许读取操作。`,
        error: "DANGEROUS_OPERATION",
      }
    }

    try {
      const { stdout, stderr } = await execAsync(`gh ${command}`, {
        timeout: COMMAND_TIMEOUT,
        maxBuffer: 10 * 1024 * 1024, // 10MB buffer
      })

      let output = stdout || stderr || "(无输出)"

      // Truncate if too long
      if (output.length > MAX_OUTPUT_LENGTH) {
        output =
          output.substring(0, MAX_OUTPUT_LENGTH) + "\n\n[输出已截断...]"
      }

      return {
        output,
        metadata: { command: `gh ${command}`, length: output.length },
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      // Clean up error message for LLM consumption
      const cleanMessage = message
        .replace(/Command failed: gh [^\n]+\n?/, "")
        .trim()
      return {
        output: cleanMessage || `命令执行失败：gh ${command}`,
        error: "COMMAND_FAILED",
      }
    }
  },
})
