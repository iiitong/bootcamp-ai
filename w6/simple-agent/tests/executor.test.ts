import { describe, expect, it } from "vitest"
import { ToolExecutor } from "../src/tool/executor.js"
import { ToolRegistry } from "../src/tool/registry.js"
import type { ExecutionContext, Tool, ToolCallContent } from "../src/types.js"

const createMockTool = (name: string, handler: (args: unknown) => Promise<string>): Tool => ({
  name,
  description: `Mock ${name}`,
  parameters: { type: "object", properties: {} },
  execute: async (args) => ({ output: await handler(args) }),
})

const defaultCtx: ExecutionContext = {
  sessionId: "test-session",
  messageId: "test-message",
}

describe("ToolExecutor", () => {
  it("should execute a tool and return result", async () => {
    const registry = new ToolRegistry()
    const tool = createMockTool("greet", async () => "Hello!")
    registry.register(tool)

    const executor = new ToolExecutor(registry)
    const toolCall: ToolCallContent = {
      type: "tool_call",
      id: "call_1",
      name: "greet",
      arguments: {},
    }

    const result = await executor.execute(toolCall, defaultCtx)
    expect(result.toolCallId).toBe("call_1")
    expect(result.result).toBe("Hello!")
    expect(result.isError).toBe(false)
  })

  it("should return error for unknown tool", async () => {
    const registry = new ToolRegistry()
    const executor = new ToolExecutor(registry)
    const toolCall: ToolCallContent = {
      type: "tool_call",
      id: "call_1",
      name: "unknown",
      arguments: {},
    }

    const result = await executor.execute(toolCall, defaultCtx)
    expect(result.isError).toBe(true)
    expect(result.result).toContain("not found")
  })

  it("should catch tool execution errors", async () => {
    const registry = new ToolRegistry()
    const tool = createMockTool("failing", async () => {
      throw new Error("Tool failed")
    })
    registry.register(tool)

    const executor = new ToolExecutor(registry)
    const toolCall: ToolCallContent = {
      type: "tool_call",
      id: "call_1",
      name: "failing",
      arguments: {},
    }

    const result = await executor.execute(toolCall, defaultCtx)
    expect(result.isError).toBe(true)
    expect(result.result).toContain("Tool failed")
  })

  it("should execute multiple tools in parallel", async () => {
    const registry = new ToolRegistry()
    const executionOrder: string[] = []

    const tool1 = createMockTool("slow", async () => {
      await new Promise((r) => setTimeout(r, 50))
      executionOrder.push("slow")
      return "slow done"
    })
    const tool2 = createMockTool("fast", async () => {
      executionOrder.push("fast")
      return "fast done"
    })

    registry.register(tool1)
    registry.register(tool2)

    const executor = new ToolExecutor(registry)
    const toolCalls: ToolCallContent[] = [
      { type: "tool_call", id: "1", name: "slow", arguments: {} },
      { type: "tool_call", id: "2", name: "fast", arguments: {} },
    ]

    const results = await executor.executeMany(toolCalls, defaultCtx)
    expect(results).toHaveLength(2)
    // Fast should complete before slow due to parallel execution
    expect(executionOrder[0]).toBe("fast")
    expect(executionOrder[1]).toBe("slow")
  })

  it("should return error when aborted", async () => {
    const registry = new ToolRegistry()
    const tool = createMockTool("test", async () => "done")
    registry.register(tool)

    const abortController = new AbortController()
    abortController.abort()

    const executor = new ToolExecutor(registry)
    const toolCall: ToolCallContent = {
      type: "tool_call",
      id: "call_1",
      name: "test",
      arguments: {},
    }

    const result = await executor.execute(toolCall, {
      ...defaultCtx,
      abortSignal: abortController.signal,
    })
    expect(result.isError).toBe(true)
    expect(result.result).toContain("aborted")
  })
})
