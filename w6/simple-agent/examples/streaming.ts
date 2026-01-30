/**
 * Streaming Example: Real-time streaming with the agent
 *
 * This example demonstrates:
 * - Using the streaming API for real-time responses
 * - Processing streaming events
 * - Building interactive applications
 */

import "dotenv/config"
import { z } from "zod"
import { createAgent, createSession, defineTool } from "../src/index.js"

// Define some tools for demonstration
const timeTool = defineTool({
  name: "get_current_time",
  description: "Get the current time in a specified timezone",
  schema: z.object({
    timezone: z.string().optional().describe("Timezone (e.g., 'America/New_York', 'Asia/Tokyo')"),
  }),
  execute: async (args) => {
    const { timezone } = args
    const now = new Date()

    try {
      const formatter = new Intl.DateTimeFormat("en-US", {
        timeZone: timezone ?? "UTC",
        dateStyle: "full",
        timeStyle: "long",
      })
      return {
        output: JSON.stringify({
          timezone: timezone ?? "UTC",
          formatted: formatter.format(now),
          iso: now.toISOString(),
        }),
      }
    } catch {
      return {
        output: JSON.stringify({
          timezone: "UTC",
          formatted: now.toUTCString(),
          iso: now.toISOString(),
          note: `Invalid timezone "${timezone}", using UTC`,
        }),
      }
    }
  },
})

const factTool = defineTool({
  name: "get_random_fact",
  description: "Get a random interesting fact about a topic",
  schema: z.object({
    topic: z.enum(["science", "history", "nature", "technology"]).describe("Topic for the fact"),
  }),
  execute: async (args) => {
    const { topic } = args

    const facts: Record<string, string[]> = {
      science: [
        "A day on Venus is longer than its year.",
        "Honey never spoils - archaeologists found 3000-year-old honey in Egyptian tombs.",
        "Octopuses have three hearts and blue blood.",
      ],
      history: [
        "The Great Wall of China is not visible from space with the naked eye.",
        "Cleopatra lived closer in time to the Moon landing than to the construction of the pyramids.",
        "The shortest war in history lasted 38 minutes (Anglo-Zanzibar War, 1896).",
      ],
      nature: [
        "A group of flamingos is called a 'flamboyance'.",
        "Bamboo can grow up to 35 inches in a single day.",
        "Sea otters hold hands while sleeping to keep from drifting apart.",
      ],
      technology: [
        "The first computer bug was an actual bug - a moth found in Harvard's Mark II computer.",
        "The QWERTY keyboard was designed to slow down typing to prevent typewriter jams.",
        "The first 1GB hard drive weighed about 550 pounds and cost $40,000 in 1980.",
      ],
    }

    const topicFacts = facts[topic]
    if (!topicFacts || topicFacts.length === 0) {
      return { output: "No facts available for this topic.", error: "No facts found" }
    }
    const randomFact = topicFacts[Math.floor(Math.random() * topicFacts.length)]
    return {
      output: JSON.stringify({ topic, fact: randomFact }),
    }
  },
})

async function main() {
  console.log("=== Streaming Agent Example ===\n")

  const agent = createAgent({
    model: process.env.DEFAULT_MODEL || "gpt-4o-mini",
    systemPrompt: `You are a helpful assistant with access to time and fact tools.
- get_current_time: Get current time in any timezone
- get_random_fact: Get random facts about science, history, nature, or technology

Be informative and engaging in your responses.`,
    tools: [timeTool, factTool],
  })

  const session = createSession()

  // Example 1: Simple streaming
  console.log("User: What time is it in Tokyo and New York?")
  console.log("\n--- Streaming Response ---")

  let _fullText = ""
  for await (const event of agent.stream(session, "What time is it in Tokyo and New York?")) {
    switch (event.type) {
      case "step":
        console.log(`\n[Step ${event.step}]`)
        break
      case "text":
        process.stdout.write(event.text)
        _fullText += event.text
        break
      case "tool_call":
        console.log(`\n  [Calling ${event.name}...]`)
        break
      case "tool_result":
        console.log(`  [${event.name} returned: ${event.result.slice(0, 80)}...]`)
        break
      case "message_end":
        console.log("\n--- End of Response ---")
        break
      case "error":
        console.error(`\n[Error: ${event.error.message}]`)
        break
    }
  }

  // Example 2: Streaming with multiple tool calls
  console.log("\n\nUser: Tell me an interesting science fact and a history fact")
  console.log("\n--- Streaming Response ---")

  _fullText = ""
  for await (const event of agent.stream(
    session,
    "Tell me an interesting science fact and a history fact",
  )) {
    switch (event.type) {
      case "step":
        console.log(`\n[Step ${event.step}]`)
        break
      case "text":
        process.stdout.write(event.text)
        _fullText += event.text
        break
      case "tool_call":
        console.log(`\n  [Calling ${event.name} with ${JSON.stringify(event.args)}...]`)
        break
      case "tool_result":
        console.log(`  [${event.name} result: ${event.result.slice(0, 100)}...]`)
        break
      case "message_end":
        console.log("\n--- End of Response ---")
        break
    }
  }

  // Example 3: Interactive streaming simulation
  console.log("\n\n=== Simulating Interactive Chat ===")

  const questions = [
    "What's one fascinating thing about technology?",
    "What time is it in London right now?",
  ]

  for (const question of questions) {
    console.log(`\nUser: ${question}`)
    console.log("Assistant: ", { end: "" })

    for await (const event of agent.stream(session, question)) {
      if (event.type === "text") {
        process.stdout.write(event.text)
      } else if (event.type === "tool_call") {
        process.stdout.write(`[using ${event.name}...]`)
      }
    }
    console.log()
  }

  console.log(`\n\nTotal messages in session: ${session.messages.length}`)
}

main().catch(console.error)
