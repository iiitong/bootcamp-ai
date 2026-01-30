/**
 * MCP Integration Example: Using MCP servers with the agent
 *
 * This example demonstrates:
 * - Connecting to an MCP server
 * - Loading tools from MCP
 * - Using MCP tools in agent conversations
 *
 * Prerequisites:
 * - Install an MCP server, e.g., @modelcontextprotocol/server-filesystem
 *   pnpm add -D @modelcontextprotocol/server-filesystem
 *
 * Run with:
 *   pnpm example:mcp
 */

import "dotenv/config"
import { createAgent, createMCPClient, createSession, type Tool } from "../src/index.js"

async function main() {
  console.log("=== MCP Integration Example ===\n")

  // Example 1: Connect to a filesystem MCP server
  // This server provides tools for file system operations
  // Note: On macOS, /tmp is a symlink to /private/tmp, so we use /private/tmp
  console.log("Connecting to filesystem MCP server...")

  let mcpTools: Tool[] = []

  try {
    const mcpClient = await createMCPClient({
      name: "filesystem",
      transport: "stdio",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/private/tmp"],
    })

    // List available tools from the MCP server
    mcpTools = await mcpClient.listTools()
    console.log(
      "Available MCP tools:",
      mcpTools.map((t) => t.name),
    )

    // Create an agent with MCP tools
    const agent = createAgent({
      model: process.env.DEFAULT_MODEL || "gpt-4o-mini",
      systemPrompt: `You are a helpful assistant with access to file system tools.
You can read files, list directories, and perform file operations.
Be careful with file operations and always confirm what you're about to do.`,
      tools: mcpTools,
      onEvent: (event) => {
        switch (event.type) {
          case "step":
            console.log(`\n[Step ${event.step}/${event.maxSteps}]`)
            break
          case "message_start":
            console.log("--- Assistant ---")
            break
          case "text":
            process.stdout.write(event.text)
            break
          case "tool_call":
            console.log(`\n[MCP Tool Call] ${event.name}`)
            console.log(`Arguments: ${JSON.stringify(event.args, null, 2)}`)
            break
          case "tool_result": {
            const preview = event.result.slice(0, 200)
            console.log(
              `[MCP Tool Result] ${event.name}: ${preview}${event.result.length > 200 ? "..." : ""}`,
            )
            break
          }
          case "message_end":
            console.log("\n-----------------")
            break
        }
      },
    })

    const session = createSession()

    // Test: List files in /private/tmp (on macOS, /tmp is a symlink to /private/tmp)
    console.log("\nUser: List the files in /private/tmp directory")
    await agent.run(session, "List the files in /private/tmp directory")

    // Clean up
    await mcpClient.disconnect()
    console.log("\nMCP client disconnected")
  } catch (_error) {
    console.log("\nNote: MCP filesystem server example requires the server to be installed.")
    console.log("Install it with: pnpm add -D @modelcontextprotocol/server-filesystem")
    console.log("\nFalling back to mock MCP example...\n")

    // Fallback: Demonstrate with mock MCP tools
    await runMockMCPExample()
  }
}

// Mock MCP example for when the real server isn't available
async function runMockMCPExample() {
  console.log("=== Mock MCP Example ===\n")

  // Simulate MCP tools (what you'd get from a real MCP server)
  const mockMCPTools: Tool[] = [
    {
      name: "read_file",
      description: "Read the contents of a file at the specified path",
      parameters: {
        type: "object",
        properties: {
          path: {
            type: "string",
            description: "Path to the file to read",
          },
        },
        required: ["path"],
      },
      execute: async (args) => {
        const { path } = args as { path: string }

        // Simulated file contents
        const mockFiles: Record<string, string> = {
          "/tmp/example.txt": "Hello, this is an example file!",
          "/tmp/config.json": '{"name": "myapp", "version": "1.0.0"}',
          "/tmp/readme.md": "# My Project\n\nThis is a readme file.",
        }

        const content = mockFiles[path]
        if (content) {
          return { output: content }
        }
        return {
          output: `File not found: ${path}`,
          error: "File not found",
        }
      },
    },
    {
      name: "list_directory",
      description: "List files and directories at the specified path",
      parameters: {
        type: "object",
        properties: {
          path: {
            type: "string",
            description: "Path to the directory to list",
          },
        },
        required: ["path"],
      },
      execute: async (args) => {
        const { path } = args as { path: string }

        // Simulated directory listing
        if (path === "/tmp" || path === "/tmp/") {
          return {
            output: JSON.stringify({
              path,
              entries: [
                { name: "example.txt", type: "file", size: 32 },
                { name: "config.json", type: "file", size: 45 },
                { name: "readme.md", type: "file", size: 48 },
                { name: "logs", type: "directory" },
              ],
            }),
          }
        }
        return {
          output: JSON.stringify({ path, entries: [] }),
        }
      },
    },
    {
      name: "write_file",
      description: "Write content to a file at the specified path",
      parameters: {
        type: "object",
        properties: {
          path: {
            type: "string",
            description: "Path where to write the file",
          },
          content: {
            type: "string",
            description: "Content to write to the file",
          },
        },
        required: ["path", "content"],
      },
      execute: async (args) => {
        const { path, content } = args as { path: string; content: string }
        // Simulated write
        return {
          output: JSON.stringify({
            success: true,
            path,
            bytesWritten: content.length,
          }),
        }
      },
    },
  ]

  const agent = createAgent({
    model: process.env.DEFAULT_MODEL || "gpt-4o-mini",
    systemPrompt: `You are a helpful assistant with access to file system tools.
Available tools:
- read_file: Read file contents
- list_directory: List directory contents
- write_file: Write content to a file

Use these tools to help users with file operations.`,
    tools: mockMCPTools,
    onEvent: (event) => {
      switch (event.type) {
        case "step":
          console.log(`\n[Step ${event.step}/${event.maxSteps}]`)
          break
        case "message_start":
          console.log("--- Assistant ---")
          break
        case "text":
          process.stdout.write(event.text)
          break
        case "tool_call":
          console.log(`\n[Tool Call] ${event.name}`)
          console.log(`Arguments: ${JSON.stringify(event.args, null, 2)}`)
          break
        case "tool_result":
          console.log(`[Tool Result] ${event.name}:`)
          console.log(event.result)
          break
        case "message_end":
          console.log("\n-----------------")
          break
      }
    },
  })

  const session = createSession()

  // Test 1: List directory
  console.log("User: List all files in /tmp directory")
  await agent.run(session, "List all files in /tmp directory")

  // Test 2: Read a file
  console.log("\nUser: Read the contents of /tmp/config.json")
  await agent.run(session, "Read the contents of /tmp/config.json")

  // Test 3: Complex task
  console.log("\nUser: Read the readme file and summarize its content")
  await agent.run(session, "Read the readme file in /tmp and summarize its content")
}

main().catch(console.error)
