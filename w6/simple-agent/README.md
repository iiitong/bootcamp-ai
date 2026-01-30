# Simple Agent SDK

A TypeScript SDK for building multi-turn AI agents with tool calling and MCP (Model Context Protocol) support, powered by OpenAI.

## Features

- Multi-turn conversation with tool calling
- Streaming support for real-time responses
- Custom tool definition with JSON Schema or Zod
- MCP (Model Context Protocol) integration
- Type-safe API with full TypeScript support
- Easy extensibility

## Installation

```bash
pnpm install
```

## Quick Start

```typescript
import { createAgent, createSession } from "./src/index.js"

// Create an agent
const agent = createAgent({
  model: "gpt-4o-mini",
  systemPrompt: "You are a helpful assistant.",
})

// Create a session
const session = createSession()

// Run the agent
await agent.run(session, "Hello, how are you?")
```

## Examples

### Basic Usage

```bash
pnpm example:basic
```

### Custom Tools

Define tools using JSON Schema:

```typescript
const weatherTool: Tool = {
  name: "get_weather",
  description: "Get the current weather",
  parameters: {
    type: "object",
    properties: {
      location: { type: "string", description: "City name" },
    },
    required: ["location"],
  },
  execute: async (args) => {
    const { location } = args as { location: string }
    return { output: JSON.stringify({ temp: 22, condition: "sunny" }) }
  },
}

const agent = createAgent({ tools: [weatherTool] })
```

Or use Zod for type-safe tool definitions:

```typescript
import { z } from "zod"
import { defineTool } from "./src/index.js"

const calculatorTool = defineTool({
  name: "calculator",
  description: "Perform calculations",
  schema: z.object({
    a: z.number(),
    b: z.number(),
    operation: z.enum(["add", "subtract", "multiply", "divide"]),
  }),
  execute: async ({ a, b, operation }) => {
    const result = operation === "add" ? a + b : a - b
    return { output: String(result) }
  },
})
```

Run the custom tools example:

```bash
pnpm example:tools
```

### MCP Integration

Connect to MCP servers for dynamic tool loading:

```typescript
import { createMCPClient, createAgent, createSession } from "./src/index.js"

// Connect to an MCP server
const mcpClient = await createMCPClient({
  name: "filesystem",
  transport: "stdio",
  command: "npx",
  args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
})

// Get tools from MCP server
const mcpTools = await mcpClient.listTools()

// Create agent with MCP tools
const agent = createAgent({
  model: "gpt-4o-mini",
  tools: mcpTools,
})

const session = createSession()
await agent.run(session, "List files in /tmp")

// Clean up
await mcpClient.disconnect()
```

Run the MCP example:

```bash
pnpm example:mcp
```

### Streaming

```typescript
const agent = createAgent({ model: "gpt-4o-mini" })
const session = createSession()

for await (const event of agent.stream(session, "Tell me a story")) {
  switch (event.type) {
    case "text":
      process.stdout.write(event.text)
      break
    case "tool_call":
      console.log(`Calling: ${event.name}`)
      break
    case "tool_result":
      console.log(`Result: ${event.result}`)
      break
  }
}
```

Run the streaming example:

```bash
pnpm example:streaming
```

### Advanced Example

See `examples/advanced.ts` for a complete task automation agent with multiple tools.

```bash
pnpm example:advanced
```

## API Reference

### Agent

```typescript
interface AgentOptions {
  model?: string // OpenAI model to use (default: "gpt-4o")
  systemPrompt?: string // System prompt
  tools?: Tool[] // Array of tools
  maxSteps?: number // Max agent loop iterations (default: 20)
  onEvent?: (event: AgentEvent) => void // Event callback
  llmConfig?: LLMClientConfig // OpenAI client config
}

const agent = createAgent(options)

// Run agent (non-streaming)
await agent.run(session, "user message")

// Run agent (streaming)
for await (const event of agent.stream(session, "user message")) {
  // handle events
}

// Manage tools
agent.addTool(tool)
agent.addTools([tool1, tool2])
agent.removeTool("toolName")
agent.listTools()
```

### Session

```typescript
const session = createSession({
  systemPrompt?: string,
  model?: string
})

// Add user message
addUserMessage(session, "message")

// Get last assistant response
const response = getLastAssistantMessage(session)

// Clear messages
clearMessages(session)
```

### Tool

```typescript
interface Tool {
  name: string
  description: string
  parameters: JSONSchema
  execute: (args: unknown) => Promise<ToolResult>
}

interface ToolResult {
  output: string
  metadata?: Record<string, unknown>
  error?: string
}
```

### MCP Client

```typescript
const client = await createMCPClient({
  name: string,
  transport: "stdio" | "sse",
  command?: string,     // for stdio
  args?: string[],      // for stdio
  url?: string,         // for sse
})

const tools = await client.listTools()
const result = await client.callTool("toolName", { arg: "value" })
await client.disconnect()
```

## Agent Events

```typescript
type AgentEvent =
  | { type: "step"; step: number; maxSteps: number }
  | { type: "message_start"; role: "assistant" }
  | { type: "text"; text: string }
  | { type: "tool_call"; name: string; args: unknown }
  | { type: "tool_result"; name: string; result: string; isError: boolean }
  | { type: "message_end"; finishReason: string }
  | { type: "error"; error: Error }
```

## Environment Variables

### Option 1: Using `.env` file (recommended)

Create a `.env` file in the project root:

```bash
# OpenAI
OPENAI_API_KEY=sk-your-api-key

# Or use OpenRouter / other OpenAI-compatible providers
OPENAI_API_KEY=sk-or-v1-your-openrouter-key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODEL=google/gemini-3-pro-preview
```

Then load it in your code:

```typescript
import "dotenv/config"
import { createAgent, createSession } from "./src/index.js"

const agent = createAgent()
const session = createSession()
```

### Option 2: Shell environment variables

```bash
export OPENAI_API_KEY=your-api-key
export OPENAI_BASE_URL=https://api.openai.com/v1  # optional
export DEFAULT_MODEL=gpt-4o  # optional
```

### Option 3: Pass in configuration

```typescript
const agent = createAgent({
  model: "gpt-4o",
  llmConfig: {
    apiKey: "your-api-key",
    baseURL: "https://api.openai.com/v1",
  },
})
```

### Supported Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | API key for OpenAI or compatible provider | - |
| `OPENAI_BASE_URL` | API base URL | `https://api.openai.com/v1` |
| `DEFAULT_MODEL` | Default model to use | `gpt-4o` |

## Development

```bash
# Build
pnpm build

# Type check
pnpm typecheck

# Lint
pnpm lint

# Fix lint issues
pnpm lint:fix

# Run tests
pnpm test
```

## License

ISC
