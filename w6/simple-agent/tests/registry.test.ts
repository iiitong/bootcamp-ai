import { describe, expect, it } from "vitest"
import { ToolRegistry } from "../src/tool/registry.js"
import type { Tool } from "../src/types.js"

const mockTool: Tool = {
  name: "test_tool",
  description: "A test tool",
  parameters: {
    type: "object",
    properties: {
      input: { type: "string" },
    },
    required: ["input"],
  },
  execute: async (args) => {
    const { input } = args as { input: string }
    return { output: `Received: ${input}` }
  },
}

describe("ToolRegistry", () => {
  it("should register a tool", () => {
    const registry = new ToolRegistry()
    registry.register(mockTool)
    expect(registry.get("test_tool")).toBe(mockTool)
  })

  it("should throw when registering duplicate tool", () => {
    const registry = new ToolRegistry()
    registry.register(mockTool)
    expect(() => registry.register(mockTool)).toThrow("already registered")
  })

  it("should unregister a tool", () => {
    const registry = new ToolRegistry()
    registry.register(mockTool)
    expect(registry.unregister("test_tool")).toBe(true)
    expect(registry.get("test_tool")).toBeUndefined()
  })

  it("should return false when unregistering non-existent tool", () => {
    const registry = new ToolRegistry()
    expect(registry.unregister("non_existent")).toBe(false)
  })

  it("should list all tools", () => {
    const registry = new ToolRegistry()
    const tool2: Tool = { ...mockTool, name: "tool2" }
    registry.register(mockTool)
    registry.register(tool2)
    const tools = registry.list()
    expect(tools).toHaveLength(2)
    expect(tools.map((t) => t.name)).toContain("test_tool")
    expect(tools.map((t) => t.name)).toContain("tool2")
  })

  it("should register many tools", () => {
    const registry = new ToolRegistry()
    const tool2: Tool = { ...mockTool, name: "tool2" }
    registry.registerMany([mockTool, tool2])
    expect(registry.list()).toHaveLength(2)
  })

  it("should convert to tool definitions", () => {
    const registry = new ToolRegistry()
    registry.register(mockTool)
    const definitions = registry.toToolDefinitions()
    expect(definitions).toHaveLength(1)
    expect(definitions[0]).toEqual({
      type: "function",
      function: {
        name: "test_tool",
        description: "A test tool",
        parameters: mockTool.parameters,
      },
    })
  })
})
