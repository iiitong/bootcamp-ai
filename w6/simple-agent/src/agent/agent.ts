import { LLMClient, type LLMClientConfig } from "../llm/client.js"
import { ToolExecutor } from "../tool/executor.js"
import { ToolRegistry } from "../tool/registry.js"
import type {
  AgentConfig,
  AgentEvent,
  Message,
  MessageContent,
  Session,
  Tool,
  ToolCallContent,
} from "../types.js"
import { generateId } from "../utils.js"

export interface AgentOptions extends AgentConfig {
  llmConfig?: LLMClientConfig
}

interface InternalConfig {
  model: string
  systemPrompt: string
  maxSteps: number
  onEvent: ((event: AgentEvent) => void) | undefined
}

export class Agent {
  private llmClient: LLMClient
  private registry: ToolRegistry
  private executor: ToolExecutor
  private config: InternalConfig

  constructor(options: AgentOptions = {}) {
    this.llmClient = new LLMClient(options.llmConfig)
    this.registry = new ToolRegistry()
    this.executor = new ToolExecutor(this.registry)
    this.config = {
      model: options.model ?? "gpt-4o",
      systemPrompt: options.systemPrompt ?? "You are a helpful assistant.",
      maxSteps: options.maxSteps ?? 20,
      onEvent: options.onEvent,
    }

    if (options.tools) {
      this.registry.registerMany(options.tools)
    }
  }

  addTool(tool: Tool): this {
    this.registry.register(tool)
    return this
  }

  addTools(tools: Tool[]): this {
    this.registry.registerMany(tools)
    return this
  }

  removeTool(name: string): boolean {
    return this.registry.unregister(name)
  }

  listTools(): Tool[] {
    return this.registry.list()
  }

  async run(session: Session, userMessage?: string): Promise<Message[]> {
    if (userMessage) {
      session.messages.push({
        id: generateId(),
        role: "user",
        content: [{ type: "text", text: userMessage }],
        createdAt: new Date(),
      })
    }

    session.status = "running"
    let step = 0
    const maxSteps = this.config.maxSteps ?? 20

    try {
      while (step < maxSteps) {
        step++
        this.emit({ type: "step", step, maxSteps })

        const response = await this.llmClient.call({
          model: session.model || this.config.model || "gpt-4o",
          messages: session.messages,
          systemPrompt: session.systemPrompt || this.config.systemPrompt || "",
          tools: this.registry.toToolDefinitions(),
        })

        const assistantMessage: Message = {
          id: generateId(),
          role: "assistant",
          content: response.content,
          createdAt: new Date(),
        }
        session.messages.push(assistantMessage)

        this.emit({ type: "message_start", role: "assistant" })

        for (const content of response.content) {
          if (content.type === "text") {
            this.emit({ type: "text", text: content.text })
          } else if (content.type === "tool_call") {
            this.emit({ type: "tool_call", name: content.name, args: content.arguments })
          }
        }

        const toolCalls = response.content.filter(
          (c): c is ToolCallContent => c.type === "tool_call",
        )

        if (toolCalls.length === 0) {
          this.emit({ type: "message_end", finishReason: response.finishReason })
          break
        }

        const results = await this.executor.executeMany(toolCalls, {
          sessionId: session.id,
          messageId: assistantMessage.id,
        })

        for (const result of results) {
          const toolCall = toolCalls.find((tc) => tc.id === result.toolCallId)
          this.emit({
            type: "tool_result",
            name: toolCall?.name ?? "unknown",
            result: result.result,
            isError: result.isError ?? false,
          })
        }

        const toolMessage: Message = {
          id: generateId(),
          role: "tool",
          content: results,
          createdAt: new Date(),
        }
        session.messages.push(toolMessage)

        this.emit({ type: "message_end", finishReason: "tool_calls" })
      }

      session.status = "completed"
      return session.messages
    } catch (error) {
      session.status = "error"
      const err = error instanceof Error ? error : new Error(String(error))
      this.emit({ type: "error", error: err })
      throw err
    }
  }

  async *stream(session: Session, userMessage?: string): AsyncGenerator<AgentEvent> {
    if (userMessage) {
      session.messages.push({
        id: generateId(),
        role: "user",
        content: [{ type: "text", text: userMessage }],
        createdAt: new Date(),
      })
    }

    session.status = "running"
    let step = 0
    const maxSteps = this.config.maxSteps ?? 20

    try {
      while (step < maxSteps) {
        step++
        yield { type: "step", step, maxSteps }
        yield { type: "message_start", role: "assistant" }

        const content: MessageContent[] = []
        const toolCalls: ToolCallContent[] = []
        const pendingToolCalls: Map<string, { id: string; name: string; arguments: string }> =
          new Map()
        let textBuffer = ""
        let finishReason = "stop"

        for await (const event of this.llmClient.stream({
          model: session.model || this.config.model || "gpt-4o",
          messages: session.messages,
          systemPrompt: session.systemPrompt || this.config.systemPrompt || "",
          tools: this.registry.toToolDefinitions(),
        })) {
          switch (event.type) {
            case "text_delta":
              textBuffer += event.text
              yield { type: "text", text: event.text }
              break

            case "tool_call_start":
              pendingToolCalls.set(event.id, {
                id: event.id,
                name: event.name,
                arguments: "",
              })
              break

            case "tool_call_delta": {
              const pending = pendingToolCalls.get(event.id)
              if (pending) {
                pending.arguments += event.arguments
              }
              break
            }

            case "tool_call_end": {
              const pending = pendingToolCalls.get(event.id)
              if (pending) {
                let parsedArgs: unknown = {}
                try {
                  parsedArgs = JSON.parse(pending.arguments || "{}")
                } catch {
                  parsedArgs = { _raw: pending.arguments }
                }
                const call: ToolCallContent = {
                  type: "tool_call",
                  id: pending.id,
                  name: pending.name,
                  arguments: parsedArgs,
                }
                toolCalls.push(call)
                content.push(call)
                yield { type: "tool_call", name: call.name, args: call.arguments }
              }
              break
            }

            case "finish":
              finishReason = event.reason
              break

            case "error":
              yield { type: "error", error: event.error }
              throw event.error
          }
        }

        // Add text content if we collected any
        if (textBuffer) {
          content.unshift({ type: "text", text: textBuffer })
        }

        const assistantMessage: Message = {
          id: generateId(),
          role: "assistant",
          content: content.length > 0 ? content : [{ type: "text", text: "" }],
          createdAt: new Date(),
        }
        session.messages.push(assistantMessage)

        if (toolCalls.length === 0) {
          yield { type: "message_end", finishReason }
          break
        }

        const results = await this.executor.executeMany(toolCalls, {
          sessionId: session.id,
          messageId: assistantMessage.id,
        })

        for (const result of results) {
          const toolCall = toolCalls.find((tc) => tc.id === result.toolCallId)
          yield {
            type: "tool_result",
            name: toolCall?.name ?? "unknown",
            result: result.result,
            isError: result.isError ?? false,
          }
        }

        const toolMessage: Message = {
          id: generateId(),
          role: "tool",
          content: results,
          createdAt: new Date(),
        }
        session.messages.push(toolMessage)

        yield { type: "message_end", finishReason: "tool_calls" }
      }

      session.status = "completed"
    } catch (error) {
      session.status = "error"
      const err = error instanceof Error ? error : new Error(String(error))
      yield { type: "error", error: err }
      throw err
    }
  }

  private emit(event: AgentEvent): void {
    this.config.onEvent?.(event)
  }
}

export function createAgent(options: AgentOptions = {}): Agent {
  return new Agent(options)
}
