import { describe, expect, it } from "vitest"
import {
  addUserMessage,
  clearMessages,
  createSession,
  getLastAssistantMessage,
} from "../src/session/session.js"

describe("createSession", () => {
  it("should create a session with defaults", () => {
    const session = createSession()
    expect(session.id).toBeDefined()
    expect(session.messages).toEqual([])
    expect(session.systemPrompt).toBe("You are a helpful assistant.")
    expect(session.status).toBe("idle")
  })

  it("should create a session with custom options", () => {
    const session = createSession({
      systemPrompt: "Custom prompt",
      model: "gpt-4",
    })
    expect(session.systemPrompt).toBe("Custom prompt")
    expect(session.model).toBe("gpt-4")
  })
})

describe("addUserMessage", () => {
  it("should add a user message to session", () => {
    const session = createSession()
    const message = addUserMessage(session, "Hello")
    expect(message.role).toBe("user")
    expect(message.content).toEqual([{ type: "text", text: "Hello" }])
    expect(session.messages).toHaveLength(1)
    expect(session.messages[0]).toBe(message)
  })
})

describe("getLastAssistantMessage", () => {
  it("should return undefined when no assistant message", () => {
    const session = createSession()
    expect(getLastAssistantMessage(session)).toBeUndefined()
  })

  it("should return the last assistant message text", () => {
    const session = createSession()
    session.messages.push({
      id: "1",
      role: "assistant",
      content: [{ type: "text", text: "Hello!" }],
      createdAt: new Date(),
    })
    expect(getLastAssistantMessage(session)).toBe("Hello!")
  })

  it("should return the last assistant message when multiple exist", () => {
    const session = createSession()
    session.messages.push({
      id: "1",
      role: "assistant",
      content: [{ type: "text", text: "First" }],
      createdAt: new Date(),
    })
    session.messages.push({
      id: "2",
      role: "user",
      content: [{ type: "text", text: "Question" }],
      createdAt: new Date(),
    })
    session.messages.push({
      id: "3",
      role: "assistant",
      content: [{ type: "text", text: "Second" }],
      createdAt: new Date(),
    })
    expect(getLastAssistantMessage(session)).toBe("Second")
  })
})

describe("clearMessages", () => {
  it("should clear all messages and reset status", () => {
    const session = createSession()
    addUserMessage(session, "Hello")
    session.status = "running"
    clearMessages(session)
    expect(session.messages).toEqual([])
    expect(session.status).toBe("idle")
  })
})
