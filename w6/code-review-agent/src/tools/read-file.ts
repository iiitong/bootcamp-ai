import { z } from "zod"
import { defineTool } from "simple-agent"
import { readFile } from "node:fs/promises"
import { resolve } from "node:path"

const MAX_OUTPUT_LENGTH = 100000 // 100KB

const schema = z.object({
  path: z.string().describe("相对于当前工作目录的文件路径"),
  start_line: z.number().optional().describe("起始行号（1-based）"),
  end_line: z.number().optional().describe("结束行号（1-based）"),
})

export const readFileTool = defineTool({
  name: "read_file",
  description:
    "读取指定文件的内容。用于获取代码上下文，理解完整的代码逻辑。可以指定起始和结束行号来读取部分内容。",
  schema,
  execute: async (args) => {
    try {
      const absolutePath = resolve(process.cwd(), args.path)
      let content = await readFile(absolutePath, "utf-8")

      // Handle line range if specified
      if (args.start_line !== undefined || args.end_line !== undefined) {
        const lines = content.split("\n")
        const start = (args.start_line ?? 1) - 1 // Convert to 0-based
        const end = args.end_line ?? lines.length
        content = lines.slice(start, end).join("\n")
      }

      // Truncate if too long
      if (content.length > MAX_OUTPUT_LENGTH) {
        content =
          content.substring(0, MAX_OUTPUT_LENGTH) + "\n\n[输出已截断...]"
      }

      return {
        output: content,
        metadata: { path: args.path, length: content.length },
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      return {
        output: `错误：无法读取文件 ${args.path}`,
        error: message,
      }
    }
  },
})
