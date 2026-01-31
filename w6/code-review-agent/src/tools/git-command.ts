import { z } from "zod"
import { defineTool } from "simple-agent"
import { exec } from "node:child_process"
import { promisify } from "node:util"

const execAsync = promisify(exec)

const MAX_OUTPUT_LENGTH = 100000 // 100KB
const COMMAND_TIMEOUT = 30000 // 30 seconds

// Dangerous git commands that could modify repository state
const DANGEROUS_PATTERNS = [
  /^push\b/,
  /^reset\s+--hard\b/,
  /^clean\s+-f/,
  /^checkout\s+\.\s*$/,
  /^checkout\s+--\s+\./,
  /^rebase\b/,
  /^merge\b/,
  /^commit\b/,
  /^stash\s+drop\b/,
  /^stash\s+clear\b/,
  /^branch\s+-[dD]\b/,
  /^tag\s+-d\b/,
  /^remote\s+remove\b/,
  /^remote\s+rm\b/,
  /^gc\b/,
  /^prune\b/,
  /^filter-branch\b/,
  /^reflog\s+expire\b/,
  /^reflog\s+delete\b/,
  /^update-ref\s+-d\b/,
]

function isDangerousCommand(command: string): boolean {
  const trimmed = command.trim()
  return DANGEROUS_PATTERNS.some((pattern) => pattern.test(trimmed))
}

const schema = z.object({
  command: z
    .string()
    .describe("git 子命令（不含 'git' 前缀），例如：'diff main...HEAD'"),
})

export const gitCommandTool = defineTool({
  name: "git_command",
  description: `执行 git 命令获取代码变更和仓库信息。只允许读取操作。
常用命令示例：
- diff: 查看未暂存的更改
- diff --cached: 查看已暂存的更改
- diff main...HEAD: 查看当前分支相对于 main 的更改
- diff <commit1>..<commit2>: 查看两个 commit 之间的差异
- show <commit>: 查看某个 commit 的内容
- log --oneline -n 10: 查看最近 10 条 commit
- log --oneline <commit>..HEAD: 查看从某 commit 到 HEAD 的所有 commit
- blame <file>: 查看文件的修改历史
- status: 查看当前工作区状态
- branch -a: 查看所有分支`,
  schema,
  execute: async (args) => {
    const command = args.command.trim()

    // Security check
    if (isDangerousCommand(command)) {
      return {
        output: `错误：禁止执行危险命令。只允许读取操作。`,
        error: "DANGEROUS_COMMAND",
      }
    }

    try {
      const { stdout, stderr } = await execAsync(`git ${command}`, {
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
        metadata: { command: `git ${command}`, length: output.length },
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      // Clean up error message for LLM consumption
      const cleanMessage = message
        .replace(/Command failed: git [^\n]+\n?/, "")
        .trim()
      return {
        output: cleanMessage || `命令执行失败：git ${command}`,
        error: "COMMAND_FAILED",
      }
    }
  },
})
