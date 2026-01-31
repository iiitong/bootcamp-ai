import { createAgent, type AgentEvent, type Tool } from "simple-agent"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"
import { readFileTool } from "./tools/read-file.js"
import { writeFileTool } from "./tools/write-file.js"
import { gitCommandTool } from "./tools/git-command.js"
import { ghCommandTool } from "./tools/gh-command.js"
import { bashCommandTool } from "./tools/bash-command.js"

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// Load system prompt from file
const systemPrompt = readFileSync(
  join(__dirname, "..", "prompts", "system.md"),
  "utf-8"
)

export interface CodeReviewAgentOptions {
  /** LLM model to use (default: gpt-4o) */
  model?: string
  /** Event callback for streaming events */
  onEvent?: (event: AgentEvent) => void
  /** Maximum number of tool calling steps (default: 30) */
  maxSteps?: number
  /** LLM client configuration */
  llmConfig?: {
    apiKey?: string
    baseURL?: string
  }
}

/**
 * Creates a code review agent.
 *
 * The agent is LLM-driven - it autonomously:
 * - Interprets user intent from natural language
 * - Decides which tools to call and in what order
 * - Analyzes code changes and generates structured reviews
 *
 * @example
 * ```typescript
 * const agent = createCodeReviewAgent({
 *   onEvent: (event) => {
 *     if (event.type === "text") process.stdout.write(event.text)
 *   }
 * })
 *
 * const session = createSession()
 * await agent.run(session, "帮我 review 当前 branch 新代码")
 * ```
 */
export function createCodeReviewAgent(options?: CodeReviewAgentOptions) {
  return createAgent({
    model: options?.model ?? "gpt-4o",
    systemPrompt,
    tools: [readFileTool, writeFileTool, gitCommandTool, ghCommandTool, bashCommandTool] as Tool[],
    maxSteps: options?.maxSteps ?? 30,
    onEvent: options?.onEvent,
    llmConfig: options?.llmConfig,
  })
}

// Re-export session utilities for convenience
export { createSession, addUserMessage, getLastAssistantMessage } from "simple-agent"
export type { AgentEvent, Session, Message } from "simple-agent"

// Export tools for testing or customization
export { readFileTool } from "./tools/read-file.js"
export { writeFileTool } from "./tools/write-file.js"
export { gitCommandTool } from "./tools/git-command.js"
export { ghCommandTool } from "./tools/gh-command.js"
export { bashCommandTool } from "./tools/bash-command.js"
