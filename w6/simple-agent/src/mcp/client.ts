/**
 * MCP (Model Context Protocol) Client
 *
 * SECURITY WARNING:
 * - The stdio transport spawns child processes with the specified command
 * - Only use trusted MCP servers from verified sources
 * - Be careful with the 'env' option as it passes environment variables to child processes
 * - Never pass sensitive data (API keys, tokens) in MCP tool arguments
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js"
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js"
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js"
import type { MCPConfig, Tool, ToolResult } from "../types.js"

interface MCPToolContent {
  type: string
  text?: string
  [key: string]: unknown
}

export class MCPClient {
  private client: Client
  private config: MCPConfig
  private transport: SSEClientTransport | StdioClientTransport | null = null
  private connected = false

  constructor(config: MCPConfig) {
    this.config = config
    this.client = new Client(
      {
        name: "simple-agent",
        version: "1.0.0",
      },
      {
        capabilities: {},
      },
    )
  }

  async connect(): Promise<void> {
    if (this.connected) {
      return
    }

    if (this.config.transport === "stdio") {
      if (!this.config.command) {
        throw new Error("Command is required for stdio transport")
      }

      const transportConfig: { command: string; args?: string[]; env?: Record<string, string> } = {
        command: this.config.command,
      }

      if (this.config.args) {
        transportConfig.args = this.config.args
      }

      if (this.config.env) {
        transportConfig.env = this.config.env
      }

      this.transport = new StdioClientTransport(transportConfig)
    } else if (this.config.transport === "sse") {
      if (!this.config.url) {
        throw new Error("URL is required for SSE transport")
      }

      this.transport = new SSEClientTransport(new URL(this.config.url))
    } else {
      throw new Error(`Unsupported transport: ${this.config.transport}`)
    }

    await this.client.connect(this.transport)
    this.connected = true
  }

  async disconnect(): Promise<void> {
    if (!this.connected) {
      return
    }

    await this.client.close()
    this.connected = false
    this.transport = null
  }

  async listTools(): Promise<Tool[]> {
    if (!this.connected) {
      throw new Error("MCP client not connected")
    }

    const result = await this.client.listTools()
    return result.tools.map((tool) =>
      this.adaptTool({
        name: tool.name,
        description: tool.description ?? "",
        inputSchema: tool.inputSchema,
      }),
    )
  }

  async callTool(name: string, args: unknown): Promise<ToolResult> {
    if (!this.connected) {
      throw new Error("MCP client not connected")
    }

    try {
      const result = await this.client.callTool({
        name,
        arguments: args as Record<string, unknown>,
      })

      const contentArray = result.content as MCPToolContent[]
      const output = contentArray
        .map((c) => {
          if (c.type === "text" && c.text) {
            return c.text
          }
          return JSON.stringify(c)
        })
        .join("\n")

      const toolResult: ToolResult = {
        output,
        metadata: { isError: result.isError },
      }
      if (result.isError) {
        toolResult.error = output
      }
      return toolResult
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      return {
        output: message,
        error: message,
      }
    }
  }

  private adaptTool(mcpTool: { name: string; description: string; inputSchema: unknown }): Tool {
    return {
      name: mcpTool.name,
      description: mcpTool.description,
      parameters: (mcpTool.inputSchema as Tool["parameters"]) ?? {
        type: "object",
        properties: {},
      },
      execute: async (args: unknown): Promise<ToolResult> => {
        return this.callTool(mcpTool.name, args)
      },
    }
  }

  get isConnected(): boolean {
    return this.connected
  }

  get name(): string {
    return this.config.name
  }
}

export async function createMCPClient(config: MCPConfig): Promise<MCPClient> {
  const client = new MCPClient(config)
  await client.connect()
  return client
}
