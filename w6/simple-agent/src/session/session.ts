import type { Message, Session, TextContent } from "../types.js"
import { generateId } from "../utils.js"

export interface CreateSessionOptions {
  systemPrompt?: string
  model?: string
}

export function createSession(options: CreateSessionOptions = {}): Session {
  return {
    id: generateId(),
    messages: [],
    systemPrompt: options.systemPrompt ?? "You are a helpful assistant.",
    model: options.model ?? process.env.DEFAULT_MODEL ?? "gpt-4o",
    status: "idle",
  }
}

export function addUserMessage(session: Session, text: string): Message {
  const message: Message = {
    id: generateId(),
    role: "user",
    content: [{ type: "text", text }],
    createdAt: new Date(),
  }
  session.messages.push(message)
  return message
}

export function getLastAssistantMessage(session: Session): string | undefined {
  for (let i = session.messages.length - 1; i >= 0; i--) {
    const msg = session.messages[i]
    if (msg?.role === "assistant") {
      const textParts = msg.content.filter((c): c is TextContent => c.type === "text")
      return textParts.map((t) => t.text).join("\n")
    }
  }
  return undefined
}

export function clearMessages(session: Session): void {
  session.messages = []
  session.status = "idle"
}
