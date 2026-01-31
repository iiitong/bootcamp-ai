/**
 * Basic example of using the Code Review Agent
 *
 * Run with: pnpm example
 * Or: pnpm tsx examples/basic.ts
 */

import "dotenv/config"
import {
  createCodeReviewAgent,
  createSession,
  type AgentEvent,
} from "../src/index.js"

// Create a code review agent with event streaming
const agent = createCodeReviewAgent({
  model: process.env.DEFAULT_MODEL ?? "gpt-4o",
  onEvent: (event: AgentEvent) => {
    switch (event.type) {
      case "step":
        console.log(`\n--- Step ${event.step}/${event.maxSteps} ---`)
        break
      case "message_start":
        console.log("\n[Assistant]")
        break
      case "text":
        process.stdout.write(event.text)
        break
      case "tool_call":
        console.log(`\n[调用工具: ${event.name}]`)
        if (event.name === "git_command" || event.name === "gh_command") {
          const args = event.args as { command: string }
          console.log(`  命令: ${args.command}`)
        } else if (event.name === "read_file") {
          const args = event.args as { path: string }
          console.log(`  文件: ${args.path}`)
        } else if (event.name === "write_file") {
          const args = event.args as { path: string }
          console.log(`  写入: ${args.path}`)
        }
        break
      case "tool_result":
        if (event.isError) {
          console.log(`[工具错误: ${event.result}]`)
        } else {
          // Truncate long output for display
          const output = event.result.length > 200
            ? event.result.substring(0, 200) + "..."
            : event.result
          console.log(`[工具结果: ${output}]`)
        }
        break
      case "message_end":
        console.log(`\n[完成: ${event.finishReason}]`)
        break
      case "error":
        console.error(`\n[错误: ${event.error.message}]`)
        break
    }
  },
})

// Create a session for the conversation
const session = createSession()

// Get the user's request from command line or use default
const userMessage =
  process.argv[2] ?? "帮我 review 当前 branch 新代码，简洁说明问题就行"

console.log("=".repeat(60))
console.log("Code Review Agent")
console.log("=".repeat(60))
console.log(`\n[用户]: ${userMessage}\n`)

try {
  // Run the agent - it will autonomously:
  // 1. Understand the user's intent
  // 2. Choose appropriate tools to call
  // 3. Analyze the code changes
  // 4. Generate a structured review
  await agent.run(session, userMessage)

  console.log("\n" + "=".repeat(60))
  console.log("审查完成")
  console.log("=".repeat(60))
} catch (error) {
  console.error("Agent execution failed:", error)
  process.exit(1)
}
