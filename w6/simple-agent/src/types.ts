import type { z } from "zod"

// Message Types
export interface Message {
  id: string
  role: "user" | "assistant" | "tool"
  content: MessageContent[]
  createdAt: Date
}

export type MessageContent = TextContent | ToolCallContent | ToolResultContent

export interface TextContent {
  type: "text"
  text: string
}

export interface ToolCallContent {
  type: "tool_call"
  id: string
  name: string
  arguments: unknown
}

export interface ToolResultContent {
  type: "tool_result"
  toolCallId: string
  result: string
  isError?: boolean
}

// Tool Types
export interface JSONSchema {
  type: string
  properties?: Record<string, JSONSchema>
  required?: string[]
  description?: string
  items?: JSONSchema
  enum?: unknown[]
  [key: string]: unknown
}

export interface ToolResult {
  output: string
  metadata?: Record<string, unknown>
  error?: string
}

export interface Tool<TArgs = unknown> {
  name: string
  description: string
  parameters: JSONSchema
  execute: (args: TArgs) => Promise<ToolResult>
}

// Session Types
export interface Session {
  id: string
  messages: Message[]
  systemPrompt: string
  model: string
  status: "idle" | "running" | "completed" | "error"
}

// Agent Types
export type AgentEvent =
  | { type: "message_start"; role: "assistant" }
  | { type: "text"; text: string }
  | { type: "tool_call"; name: string; args: unknown }
  | { type: "tool_result"; name: string; result: string; isError: boolean }
  | { type: "message_end"; finishReason: string }
  | { type: "error"; error: Error }
  | { type: "step"; step: number; maxSteps: number }

export interface AgentConfig {
  model?: string
  systemPrompt?: string
  tools?: Tool[]
  maxSteps?: number
  onEvent?: (event: AgentEvent) => void
}

// LLM Types
export interface LLMInput {
  model: string
  messages: Message[]
  systemPrompt: string
  tools: ToolDefinition[]
  abortSignal?: AbortSignal
}

export interface ToolDefinition {
  type: "function"
  function: {
    name: string
    description: string
    parameters: JSONSchema
  }
}

export interface LLMOutput {
  content: MessageContent[]
  finishReason: "stop" | "tool_calls" | "max_tokens" | "error"
  usage: {
    inputTokens: number
    outputTokens: number
  }
}

export type LLMEvent =
  | { type: "text_delta"; text: string }
  | { type: "tool_call_start"; id: string; name: string }
  | { type: "tool_call_delta"; id: string; arguments: string }
  | { type: "tool_call_end"; id: string; name: string; arguments: string }
  | { type: "finish"; reason: string; usage: { inputTokens: number; outputTokens: number } }
  | { type: "error"; error: Error }

// Execution Context
export interface ExecutionContext {
  sessionId: string
  messageId: string
  abortSignal?: AbortSignal
}

// MCP Types
export interface MCPConfig {
  name: string
  transport: "stdio" | "sse"
  command?: string
  args?: string[]
  url?: string
  env?: Record<string, string>
}

// Retry Config
export interface RetryConfig {
  maxRetries: number
  baseDelay: number
  maxDelay: number
  retryableErrors: string[]
}

// Zod Schema Tool Helper
export type ZodTool<TSchema extends z.ZodType> = {
  name: string
  description: string
  schema: TSchema
  execute: (args: z.infer<TSchema>) => Promise<ToolResult>
}
