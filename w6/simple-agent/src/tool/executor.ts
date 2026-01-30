import type { ExecutionContext, ToolCallContent, ToolResultContent } from "../types.js"
import type { ToolRegistry } from "./registry.js"

export class ToolExecutor {
  constructor(private registry: ToolRegistry) {}

  async execute(call: ToolCallContent, ctx: ExecutionContext): Promise<ToolResultContent> {
    const tool = this.registry.get(call.name)

    if (!tool) {
      return {
        type: "tool_result",
        toolCallId: call.id,
        result: `Tool not found: ${call.name}`,
        isError: true,
      }
    }

    if (ctx.abortSignal?.aborted) {
      return {
        type: "tool_result",
        toolCallId: call.id,
        result: "Execution aborted",
        isError: true,
      }
    }

    try {
      const result = await tool.execute(call.arguments)

      return {
        type: "tool_result",
        toolCallId: call.id,
        result: result.error ?? result.output,
        isError: !!result.error,
      }
    } catch (error) {
      // Sanitize error message to avoid exposing internal details
      const message = error instanceof Error ? error.message : String(error)
      // Remove potential file paths and stack traces
      const sanitizedMessage = message.split("\n")[0]?.slice(0, 500) ?? "Tool execution failed"
      return {
        type: "tool_result",
        toolCallId: call.id,
        result: `Error: ${sanitizedMessage}`,
        isError: true,
      }
    }
  }

  async executeMany(calls: ToolCallContent[], ctx: ExecutionContext): Promise<ToolResultContent[]> {
    return Promise.all(calls.map((call) => this.execute(call, ctx)))
  }
}
