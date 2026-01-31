import { z } from "zod"
import { defineTool } from "simple-agent"
import { writeFile, mkdir } from "node:fs/promises"
import { resolve, dirname } from "node:path"

const schema = z.object({
  path: z.string().describe("相对于当前工作目录的文件路径"),
  content: z.string().describe("要写入的文件内容"),
})

export const writeFileTool = defineTool({
  name: "write_file",
  description: "将内容写入指定文件。用于保存审查报告或其他输出文件。",
  schema,
  execute: async (args) => {
    try {
      const absolutePath = resolve(process.cwd(), args.path)

      // Ensure directory exists
      await mkdir(dirname(absolutePath), { recursive: true })

      await writeFile(absolutePath, args.content, "utf-8")

      return {
        output: `成功写入文件：${args.path}（${args.content.length} 字符）`,
        metadata: { path: args.path, length: args.content.length },
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      return {
        output: `错误：无法写入文件 ${args.path}`,
        error: message,
      }
    }
  },
})
