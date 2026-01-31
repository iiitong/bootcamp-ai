import { z } from "zod"
import { defineTool } from "simple-agent"
import { exec } from "node:child_process"
import { promisify } from "node:util"

const execAsync = promisify(exec)

const MAX_OUTPUT_LENGTH = 100000 // 100KB
const COMMAND_TIMEOUT = 30000 // 30 seconds

// Allowed command prefixes (whitelist approach for safety)
const ALLOWED_COMMANDS = new Set([
  "ls",
  "find",
  "cat",
  "head",
  "tail",
  "wc",
  "grep",
  "rg",
  "tree",
  "file",
  "stat",
  "du",
  "pwd",
  "echo",
  "which",
  "type",
  "env",
  "printenv",
  "node",
  "npm",
  "pnpm",
  "yarn",
  "npx",
  "tsc",
  "eslint",
  "prettier",
  "biome",
  "python",
  "python3",
  "pip",
  "pip3",
  "cargo",
  "rustc",
  "go",
  "java",
  "javac",
  "mvn",
  "gradle",
])

// Dangerous patterns that should never be allowed
const DANGEROUS_PATTERNS = [
  /\brm\s/,
  /\brmdir\b/,
  /\bmv\s/,
  /\bcp\s.*-r/,
  /\bchmod\b/,
  /\bchown\b/,
  /\bsudo\b/,
  /\bsu\b/,
  /\bdd\b/,
  /\bmkfs\b/,
  /\bformat\b/,
  /\bshutdown\b/,
  /\breboot\b/,
  /\bkill\b/,
  /\bpkill\b/,
  /\bkillall\b/,
  />\s*\//, // redirect to absolute path
  />\s*~/, // redirect to home
  /\bcurl\b.*\|\s*(ba)?sh/, // curl | sh pattern
  /\bwget\b.*\|\s*(ba)?sh/, // wget | sh pattern
  /\beval\b/,
  /\bexec\b/,
  /`[^`]+`/, // backticks
  /\$\([^)]+\)/, // command substitution
]

function isAllowedCommand(command: string): boolean {
  const trimmed = command.trim()
  const firstWord = trimmed.split(/\s+/)[0]
  return ALLOWED_COMMANDS.has(firstWord)
}

function isDangerousCommand(command: string): boolean {
  return DANGEROUS_PATTERNS.some((pattern) => pattern.test(command))
}

const schema = z.object({
  command: z
    .string()
    .describe("要执行的 bash 命令，只允许安全的只读命令"),
})

export const bashCommandTool = defineTool({
  name: "bash_command",
  description: `执行简单的 bash 命令来辅助代码审查。只允许安全的只读命令。
允许的命令包括：
- 文件浏览: ls, find, cat, head, tail, tree, file, stat, du
- 搜索: grep, rg (ripgrep)
- 统计: wc
- 包管理器检查: npm, pnpm, yarn, pip, cargo, go, mvn, gradle
- 代码工具: tsc, eslint, prettier, biome (仅检查模式)
- 环境信息: pwd, which, type, env, node --version 等

禁止的操作：
- 文件修改/删除: rm, mv, cp, chmod, chown
- 系统操作: sudo, shutdown, kill
- 危险模式: curl|sh, eval, 命令替换`,
  schema,
  execute: async (args) => {
    const command = args.command.trim()

    // Check if command is in whitelist
    if (!isAllowedCommand(command)) {
      const firstWord = command.split(/\s+/)[0]
      return {
        output: `错误：命令 '${firstWord}' 不在允许列表中。只允许安全的只读命令。`,
        error: "COMMAND_NOT_ALLOWED",
      }
    }

    // Check for dangerous patterns
    if (isDangerousCommand(command)) {
      return {
        output: `错误：检测到危险的命令模式。`,
        error: "DANGEROUS_COMMAND",
      }
    }

    try {
      const { stdout, stderr } = await execAsync(command, {
        timeout: COMMAND_TIMEOUT,
        maxBuffer: 10 * 1024 * 1024, // 10MB buffer
        shell: "/bin/bash",
      })

      let output = stdout || stderr || "(无输出)"

      // Truncate if too long
      if (output.length > MAX_OUTPUT_LENGTH) {
        output =
          output.substring(0, MAX_OUTPUT_LENGTH) + "\n\n[输出已截断...]"
      }

      return {
        output,
        metadata: { command, length: output.length },
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      // Clean up error message
      const cleanMessage = message
        .replace(/Command failed: [^\n]+\n?/, "")
        .trim()
      return {
        output: cleanMessage || `命令执行失败：${command}`,
        error: "COMMAND_FAILED",
      }
    }
  },
})
