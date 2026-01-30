/**
 * Custom Tools Example: Adding custom tools to the agent
 *
 * This example demonstrates:
 * - Defining custom tools with JSON Schema
 * - Using defineTool with Zod schemas
 * - Tool execution and results
 */

import "dotenv/config"
import { z } from "zod"
import type { Tool, ToolResult } from "../src/index.js"
import { createAgent, createSession, defineTool } from "../src/index.js"

// Method 1: Define a tool with raw JSON Schema
const weatherTool: Tool = {
  name: "get_weather",
  description: "Get the current weather for a given location",
  parameters: {
    type: "object",
    properties: {
      location: {
        type: "string",
        description: "The city and country, e.g., 'Tokyo, Japan'",
      },
      unit: {
        type: "string",
        enum: ["celsius", "fahrenheit"],
        description: "Temperature unit",
      },
    },
    required: ["location"],
  },
  execute: async (args): Promise<ToolResult> => {
    const { location, unit = "celsius" } = args as {
      location: string
      unit?: "celsius" | "fahrenheit"
    }

    // Simulated weather data
    const weatherData: Record<string, { temp: number; condition: string }> = {
      "Tokyo, Japan": { temp: 22, condition: "sunny" },
      "London, UK": { temp: 15, condition: "cloudy" },
      "New York, USA": { temp: 18, condition: "partly cloudy" },
      Paris: { temp: 20, condition: "clear" },
    }

    const data = weatherData[location]

    if (!data) {
      return {
        output: JSON.stringify({
          location,
          temp: Math.floor(Math.random() * 30) + 5,
          unit,
          condition: "unknown",
        }),
      }
    }

    const temp = unit === "fahrenheit" ? (data.temp * 9) / 5 + 32 : data.temp

    return {
      output: JSON.stringify({
        location,
        temp,
        unit,
        condition: data.condition,
      }),
    }
  },
}

// Method 2: Define a tool using Zod schema (type-safe!)
const calculatorTool = defineTool({
  name: "calculator",
  description: "Perform basic arithmetic calculations",
  schema: z.object({
    operation: z
      .enum(["add", "subtract", "multiply", "divide"])
      .describe("The operation to perform"),
    a: z.number().describe("First number"),
    b: z.number().describe("Second number"),
  }),
  execute: async (args) => {
    const { operation, a, b } = args

    let result: number
    switch (operation) {
      case "add":
        result = a + b
        break
      case "subtract":
        result = a - b
        break
      case "multiply":
        result = a * b
        break
      case "divide":
        if (b === 0) {
          return { output: "Error: Division by zero", error: "Division by zero" }
        }
        result = a / b
        break
    }

    return {
      output: JSON.stringify({ operation, a, b, result }),
    }
  },
})

// Method 3: Define a more complex tool with Zod
const searchTool = defineTool({
  name: "search_database",
  description: "Search for items in a mock database",
  schema: z.object({
    query: z.string().describe("Search query"),
    limit: z.number().optional().default(5).describe("Maximum number of results"),
    category: z.enum(["products", "users", "orders"]).optional().describe("Category to search in"),
  }),
  execute: async (args) => {
    const { query, limit, category } = args

    // Mock database search
    const mockResults = [
      { id: 1, name: "Widget A", category: "products", relevance: 0.95 },
      { id: 2, name: "Widget B", category: "products", relevance: 0.85 },
      { id: 3, name: "John Doe", category: "users", relevance: 0.75 },
      { id: 4, name: "Order #1234", category: "orders", relevance: 0.65 },
    ]

    let results = mockResults.filter((item) =>
      item.name.toLowerCase().includes(query.toLowerCase()),
    )

    if (category) {
      results = results.filter((item) => item.category === category)
    }

    results = results.slice(0, limit)

    return {
      output: JSON.stringify({
        query,
        category: category ?? "all",
        count: results.length,
        results,
      }),
    }
  },
})

async function main() {
  // Create an agent with custom tools
  const agent = createAgent({
    model: process.env.DEFAULT_MODEL || "gpt-4o-mini",
    systemPrompt: `You are a helpful assistant with access to several tools:
- get_weather: Get current weather information
- calculator: Perform arithmetic calculations
- search_database: Search a mock database

Use these tools when appropriate to answer user questions.`,
    tools: [weatherTool, calculatorTool, searchTool],
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
          console.log(`\n[Tool Call] ${event.name}(${JSON.stringify(event.args)})`)
          break
        case "tool_result":
          console.log(`[Tool Result] ${event.name}: ${event.result}`)
          break
        case "message_end":
          console.log("\n-----------------")
          break
      }
    },
  })

  const session = createSession()

  // Test weather tool
  console.log("User: What's the weather like in Tokyo?")
  await agent.run(session, "What's the weather like in Tokyo?")

  // Test calculator tool
  console.log("\nUser: What is 125 * 8.5?")
  await agent.run(session, "What is 125 * 8.5?")

  // Test multiple tools
  console.log("\nUser: What's the weather in Paris and calculate 20°C to Fahrenheit")
  await agent.run(session, "What's the weather in Paris and calculate 20°C to Fahrenheit")

  // Test search tool
  console.log("\nUser: Search for widgets in the database")
  await agent.run(session, "Search for widgets in the database")
}

main().catch(console.error)
