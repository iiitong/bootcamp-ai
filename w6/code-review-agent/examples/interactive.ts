/**
 * Interactive example - multi-turn conversation with the Code Review Agent
 *
 * Run with: pnpm tsx examples/interactive.ts
 */

import "dotenv/config"
import * as readline from "node:readline"
import {
  createCodeReviewAgent,
  createSession,
  type AgentEvent,
} from "../src/index.js"

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
})

function prompt(question: string): Promise<string> {
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      resolve(answer)
    })
  })
}

async function main() {
  console.log("=".repeat(60))
  console.log("Code Review Agent - Interactive Mode")
  console.log("=".repeat(60))
  console.log("\n输入你的问题，输入 'exit' 或 'quit' 退出\n")
  console.log("示例命令：")
  console.log("  - 帮我 review 当前代码")
  console.log("  - 帮我 review 当前 branch 新代码")
  console.log("  - 帮我 review commit abc123")
  console.log("  - 帮我 review PR #42")
  console.log("  - 详细解释第 1 个问题")
  console.log("  - 把审查结果保存到 REVIEW.md")
  console.log("")

  const agent = createCodeReviewAgent({
    model: process.env.DEFAULT_MODEL ?? "gpt-4o",
    onEvent: (event: AgentEvent) => {
      switch (event.type) {
        case "text":
          process.stdout.write(event.text)
          break
        case "tool_call":
          console.log(`\n[调用: ${event.name}]`)
          break
        case "tool_result":
          if (event.isError) {
            console.log(`[错误: ${event.result.substring(0, 100)}]`)
          }
          break
        case "error":
          console.error(`\n[错误: ${event.error.message}]`)
          break
      }
    },
  })

  // Create a persistent session for multi-turn conversation
  const session = createSession()

  while (true) {
    const userInput = await prompt("\n[你]: ")

    if (!userInput.trim()) {
      continue
    }

    if (userInput.toLowerCase() === "exit" || userInput.toLowerCase() === "quit") {
      console.log("\n再见！")
      break
    }

    if (userInput.toLowerCase() === "clear") {
      // Start a new session
      session.messages = []
      console.log("\n会话已清空。")
      continue
    }

    console.log("\n[助手]:")
    try {
      await agent.run(session, userInput)
    } catch (error) {
      console.error("\n执行出错:", error instanceof Error ? error.message : error)
    }
  }

  rl.close()
}

main().catch(console.error)
