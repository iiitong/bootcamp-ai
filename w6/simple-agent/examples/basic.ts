/**
 * Basic Example: Simple conversation with the agent
 *
 * This example demonstrates:
 * - Creating an agent
 * - Running a simple conversation
 * - Handling events
 */

import "dotenv/config"
import { createAgent, createSession } from "../src/index.js"

async function main() {
  // Create an agent with basic configuration
  const model = process.env.DEFAULT_MODEL || "gpt-4o-mini"
  console.log(`Using model: ${model}`)

  const agent = createAgent({
    model,
    systemPrompt: "You are a helpful assistant. Be concise in your responses.",
    onEvent: (event) => {
      switch (event.type) {
        case "message_start":
          console.log("\n--- Assistant ---")
          break
        case "text":
          process.stdout.write(event.text)
          break
        case "message_end":
          console.log("\n-----------------")
          break
        case "error":
          console.error("Error:", event.error.message)
          break
      }
    },
  })

  // Create a session
  const session = createSession({
    systemPrompt: "You are a helpful assistant. Answer questions concisely.",
  })

  // Run the agent with a user message
  console.log("User: What is the capital of France?")
  await agent.run(session, "What is the capital of France?")

  // Continue the conversation
  console.log("\nUser: And what is its population?")
  await agent.run(session, "And what is its population?")

  // Show final message count
  console.log(`\nTotal messages in session: ${session.messages.length}`)
}

main().catch(console.error)
