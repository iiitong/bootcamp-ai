import OpenAI from "openai"
import type {
  LLMEvent,
  LLMInput,
  LLMOutput,
  Message,
  MessageContent,
  TextContent,
  ToolCallContent,
  ToolDefinition,
  ToolResultContent,
} from "../types.js"

export interface LLMClientConfig {
  apiKey?: string
  baseURL?: string
  defaultModel?: string
}

export class LLMClient {
  private client: OpenAI
  private defaultModel: string

  constructor(config: LLMClientConfig = {}) {
    const apiKey = config.apiKey ?? process.env.OPENAI_API_KEY
    const baseURL = config.baseURL ?? process.env.OPENAI_BASE_URL
    this.client = new OpenAI({ apiKey, baseURL })
    this.defaultModel = config.defaultModel ?? process.env.DEFAULT_MODEL ?? "gpt-4o"
  }

  async call(input: LLMInput): Promise<LLMOutput> {
    const hasTools = input.tools.length > 0
    const params: OpenAI.Chat.ChatCompletionCreateParamsNonStreaming = {
      model: input.model || this.defaultModel,
      messages: this.convertMessages(input.systemPrompt, input.messages),
    }

    if (hasTools) {
      params.tools = this.convertTools(input.tools)
      params.tool_choice = "auto"
    }

    const response = await this.client.chat.completions.create(params)

    if (!response.choices || response.choices.length === 0) {
      throw new Error("No response from LLM: empty choices array")
    }

    const choice = response.choices[0]
    if (!choice?.message) {
      throw new Error("Invalid response structure from LLM")
    }

    const content: MessageContent[] = []

    if (choice.message.content) {
      content.push({ type: "text", text: choice.message.content })
    }

    if (choice.message.tool_calls) {
      for (const toolCall of choice.message.tool_calls) {
        // Only handle function-type tool calls
        if (toolCall.type !== "function") {
          continue
        }
        let parsedArgs: unknown = {}
        try {
          parsedArgs = JSON.parse(toolCall.function.arguments)
        } catch {
          // If JSON parsing fails, pass the raw string wrapped in an object
          parsedArgs = { _raw: toolCall.function.arguments }
        }
        content.push({
          type: "tool_call",
          id: toolCall.id,
          name: toolCall.function.name,
          arguments: parsedArgs,
        })
      }
    }

    const finishReason = this.mapFinishReason(choice.finish_reason)

    return {
      content,
      finishReason,
      usage: {
        inputTokens: response.usage?.prompt_tokens ?? 0,
        outputTokens: response.usage?.completion_tokens ?? 0,
      },
    }
  }

  async *stream(input: LLMInput): AsyncGenerator<LLMEvent> {
    const hasTools = input.tools.length > 0
    const params: OpenAI.Chat.ChatCompletionCreateParamsStreaming = {
      model: input.model || this.defaultModel,
      messages: this.convertMessages(input.systemPrompt, input.messages),
      stream: true,
      stream_options: { include_usage: true },
    }

    if (hasTools) {
      params.tools = this.convertTools(input.tools)
      params.tool_choice = "auto"
    }

    const stream = await this.client.chat.completions.create(params)

    const toolCalls: Map<number, { id: string; name: string; arguments: string }> = new Map()
    let usage = { inputTokens: 0, outputTokens: 0 }
    let finishReason = "stop"

    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta

      if (delta?.content) {
        yield { type: "text_delta", text: delta.content }
      }

      if (delta?.tool_calls) {
        for (const toolCall of delta.tool_calls) {
          const existing = toolCalls.get(toolCall.index)

          if (!existing) {
            // New tool call
            const newCall = {
              id: toolCall.id ?? "",
              name: toolCall.function?.name ?? "",
              arguments: toolCall.function?.arguments ?? "",
            }
            toolCalls.set(toolCall.index, newCall)
            yield { type: "tool_call_start", id: newCall.id, name: newCall.name }
          } else {
            // Continue existing tool call
            if (toolCall.function?.arguments) {
              existing.arguments += toolCall.function.arguments
              yield {
                type: "tool_call_delta",
                id: existing.id,
                arguments: toolCall.function.arguments,
              }
            }
          }
        }
      }

      if (chunk.choices[0]?.finish_reason) {
        finishReason = chunk.choices[0].finish_reason
      }

      if (chunk.usage) {
        usage = {
          inputTokens: chunk.usage.prompt_tokens,
          outputTokens: chunk.usage.completion_tokens,
        }
      }
    }

    // Emit tool call end events
    for (const [, toolCall] of toolCalls) {
      yield {
        type: "tool_call_end",
        id: toolCall.id,
        name: toolCall.name,
        arguments: toolCall.arguments,
      }
    }

    yield { type: "finish", reason: finishReason, usage }
  }

  private convertMessages(
    systemPrompt: string,
    messages: Message[],
  ): OpenAI.Chat.ChatCompletionMessageParam[] {
    const result: OpenAI.Chat.ChatCompletionMessageParam[] = []

    if (systemPrompt) {
      result.push({ role: "system", content: systemPrompt })
    }

    for (const msg of messages) {
      if (msg.role === "user") {
        const textParts = msg.content.filter((c): c is TextContent => c.type === "text")
        const toolResults = msg.content.filter(
          (c): c is ToolResultContent => c.type === "tool_result",
        )

        if (textParts.length > 0) {
          result.push({
            role: "user",
            content: textParts.map((t) => t.text).join("\n"),
          })
        }

        // Tool results go as separate tool messages
        for (const tr of toolResults) {
          result.push({
            role: "tool",
            tool_call_id: tr.toolCallId,
            content: tr.result,
          })
        }
      } else if (msg.role === "assistant") {
        const textParts = msg.content.filter((c): c is TextContent => c.type === "text")
        const toolCalls = msg.content.filter((c): c is ToolCallContent => c.type === "tool_call")

        const assistantMsg: OpenAI.Chat.ChatCompletionAssistantMessageParam = {
          role: "assistant",
          content: textParts.length > 0 ? textParts.map((t) => t.text).join("\n") : null,
        }

        if (toolCalls.length > 0) {
          assistantMsg.tool_calls = toolCalls.map((tc) => ({
            id: tc.id,
            type: "function" as const,
            function: {
              name: tc.name,
              arguments: JSON.stringify(tc.arguments),
            },
          }))
        }

        result.push(assistantMsg)
      } else if (msg.role === "tool") {
        const toolResults = msg.content.filter(
          (c): c is ToolResultContent => c.type === "tool_result",
        )
        for (const tr of toolResults) {
          result.push({
            role: "tool",
            tool_call_id: tr.toolCallId,
            content: tr.result,
          })
        }
      }
    }

    return result
  }

  private convertTools(tools: ToolDefinition[]): OpenAI.Chat.ChatCompletionTool[] {
    return tools.map((tool) => ({
      type: "function",
      function: {
        name: tool.function.name,
        description: tool.function.description,
        parameters: tool.function.parameters as Record<string, unknown>,
      },
    }))
  }

  private mapFinishReason(reason: string | null): "stop" | "tool_calls" | "max_tokens" | "error" {
    switch (reason) {
      case "stop":
        return "stop"
      case "tool_calls":
        return "tool_calls"
      case "length":
        return "max_tokens"
      default:
        return "stop"
    }
  }
}
