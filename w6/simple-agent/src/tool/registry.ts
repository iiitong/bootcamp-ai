import type { Tool, ToolDefinition } from "../types.js"

export class ToolRegistry {
  private tools: Map<string, Tool> = new Map()

  register(tool: Tool): this {
    if (this.tools.has(tool.name)) {
      throw new Error(`Tool "${tool.name}" is already registered`)
    }
    this.tools.set(tool.name, tool)
    return this
  }

  registerMany(tools: Tool[]): this {
    for (const tool of tools) {
      this.register(tool)
    }
    return this
  }

  unregister(name: string): boolean {
    return this.tools.delete(name)
  }

  get(name: string): Tool | undefined {
    return this.tools.get(name)
  }

  has(name: string): boolean {
    return this.tools.has(name)
  }

  list(): Tool[] {
    return Array.from(this.tools.values())
  }

  clear(): void {
    this.tools.clear()
  }

  get size(): number {
    return this.tools.size
  }

  toToolDefinitions(): ToolDefinition[] {
    return this.list().map((tool) => ({
      type: "function",
      function: {
        name: tool.name,
        description: tool.description,
        parameters: tool.parameters,
      },
    }))
  }
}
