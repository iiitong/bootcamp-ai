/**
 * Advanced Example: Building a task automation agent
 *
 * This example demonstrates:
 * - Complex multi-step tasks
 * - Tool composition
 * - Session management
 * - Error handling
 */

import "dotenv/config"
import { z } from "zod"
import {
  createAgent,
  createSession,
  defineTool,
  getLastAssistantMessage,
  type Tool,
} from "../src/index.js"

// Simulated task management system
interface Task {
  id: string
  title: string
  description: string
  status: "pending" | "in_progress" | "completed"
  priority: "low" | "medium" | "high"
  createdAt: Date
}

const taskStore: Map<string, Task> = new Map()
let taskIdCounter = 1

// Task management tools
const createTaskTool = defineTool({
  name: "create_task",
  description: "Create a new task in the task management system",
  schema: z.object({
    title: z.string().describe("Title of the task"),
    description: z.string().describe("Detailed description of the task"),
    priority: z.enum(["low", "medium", "high"]).default("medium").describe("Task priority"),
  }),
  execute: async (args) => {
    const id = `task-${taskIdCounter++}`
    const task: Task = {
      id,
      title: args.title,
      description: args.description,
      status: "pending",
      priority: args.priority,
      createdAt: new Date(),
    }
    taskStore.set(id, task)
    return {
      output: JSON.stringify({ success: true, task }),
    }
  },
})

const listTasksTool = defineTool({
  name: "list_tasks",
  description: "List all tasks, optionally filtered by status or priority",
  schema: z.object({
    status: z.enum(["pending", "in_progress", "completed"]).optional().describe("Filter by status"),
    priority: z.enum(["low", "medium", "high"]).optional().describe("Filter by priority"),
  }),
  execute: async (args) => {
    let tasks = Array.from(taskStore.values())

    if (args.status) {
      tasks = tasks.filter((t) => t.status === args.status)
    }
    if (args.priority) {
      tasks = tasks.filter((t) => t.priority === args.priority)
    }

    return {
      output: JSON.stringify({
        count: tasks.length,
        tasks: tasks.map((t) => ({
          id: t.id,
          title: t.title,
          status: t.status,
          priority: t.priority,
        })),
      }),
    }
  },
})

const updateTaskTool = defineTool({
  name: "update_task",
  description: "Update an existing task's status or priority",
  schema: z.object({
    id: z.string().describe("Task ID"),
    status: z.enum(["pending", "in_progress", "completed"]).optional().describe("New status"),
    priority: z.enum(["low", "medium", "high"]).optional().describe("New priority"),
  }),
  execute: async (args) => {
    const task = taskStore.get(args.id)
    if (!task) {
      return { output: `Task not found: ${args.id}`, error: "Task not found" }
    }

    if (args.status) task.status = args.status
    if (args.priority) task.priority = args.priority

    return {
      output: JSON.stringify({ success: true, task }),
    }
  },
})

const deleteTaskTool = defineTool({
  name: "delete_task",
  description: "Delete a task by ID",
  schema: z.object({
    id: z.string().describe("Task ID to delete"),
  }),
  execute: async (args) => {
    const deleted = taskStore.delete(args.id)
    return {
      output: JSON.stringify({ success: deleted, id: args.id }),
    }
  },
})

// Email simulation tool
const sendEmailTool = defineTool({
  name: "send_email",
  description: "Send an email (simulated)",
  schema: z.object({
    to: z.string().email().describe("Recipient email address"),
    subject: z.string().describe("Email subject"),
    body: z.string().describe("Email body content"),
  }),
  execute: async (args) => {
    // Simulated email sending
    console.log("\n📧 [Simulated Email]")
    console.log(`   To: ${args.to}`)
    console.log(`   Subject: ${args.subject}`)
    console.log(`   Body: ${args.body.slice(0, 100)}...`)

    return {
      output: JSON.stringify({
        success: true,
        messageId: `msg-${Date.now()}`,
        to: args.to,
        subject: args.subject,
      }),
    }
  },
})

// Calendar simulation tool
const scheduleEventTool = defineTool({
  name: "schedule_event",
  description: "Schedule a calendar event (simulated)",
  schema: z.object({
    title: z.string().describe("Event title"),
    date: z.string().describe("Event date (YYYY-MM-DD format)"),
    time: z.string().describe("Event time (HH:MM format)"),
    duration: z.number().describe("Duration in minutes"),
    attendees: z.array(z.string()).optional().describe("List of attendee emails"),
  }),
  execute: async (args) => {
    console.log("\n📅 [Simulated Calendar Event]")
    console.log(`   Title: ${args.title}`)
    console.log(`   Date: ${args.date} at ${args.time}`)
    console.log(`   Duration: ${args.duration} minutes`)
    if (args.attendees?.length) {
      console.log(`   Attendees: ${args.attendees.join(", ")}`)
    }

    return {
      output: JSON.stringify({
        success: true,
        eventId: `evt-${Date.now()}`,
        ...args,
      }),
    }
  },
})

async function main() {
  console.log("=== Advanced Agent Example: Task Automation ===\n")

  const tools: Tool[] = [
    createTaskTool,
    listTasksTool,
    updateTaskTool,
    deleteTaskTool,
    sendEmailTool,
    scheduleEventTool,
  ]

  const agent = createAgent({
    model: process.env.DEFAULT_MODEL || "gpt-4o-mini",
    systemPrompt: `You are a productivity assistant that helps users manage their tasks, schedule events, and send communications.

Available tools:
- create_task: Create a new task
- list_tasks: List tasks (can filter by status/priority)
- update_task: Update task status or priority
- delete_task: Delete a task
- send_email: Send an email notification
- schedule_event: Schedule a calendar event

When managing tasks, be proactive about suggesting related actions like:
- Sending email reminders for high-priority tasks
- Scheduling review meetings for completed tasks
- Organizing tasks by priority

Always confirm what actions you've taken.`,
    tools,
    maxSteps: 15,
    onEvent: (event) => {
      switch (event.type) {
        case "step":
          console.log(`\n[Step ${event.step}/${event.maxSteps}]`)
          break
        case "text":
          process.stdout.write(event.text)
          break
        case "tool_call":
          console.log(`\n  🔧 ${event.name}(${JSON.stringify(event.args)})`)
          break
        case "tool_result":
          if (!event.isError) {
            console.log(`  ✓ ${event.name}: Success`)
          } else {
            console.log(`  ✗ ${event.name}: ${event.result}`)
          }
          break
        case "message_end":
          console.log("\n")
          break
        case "error":
          console.error(`\n❌ Error: ${event.error.message}`)
          break
      }
    },
  })

  const session = createSession()

  // Scenario 1: Create multiple tasks
  console.log(
    "User: Create 3 tasks for my project launch: prepare presentation (high priority), send invitations (medium), and book venue (high priority)",
  )
  await agent.run(
    session,
    "Create 3 tasks for my project launch: prepare presentation (high priority), send invitations (medium), and book venue (high priority)",
  )

  // Scenario 2: List and organize tasks
  console.log("\nUser: Show me all high priority tasks")
  await agent.run(session, "Show me all high priority tasks")

  // Scenario 3: Complex workflow
  console.log(
    "\nUser: Mark 'prepare presentation' as completed and send an email to team@company.com about the completion",
  )
  await agent.run(
    session,
    "Mark 'prepare presentation' as completed and send an email to team@company.com about the completion. The email should congratulate the team.",
  )

  // Scenario 4: Schedule follow-up
  console.log("\nUser: Schedule a project review meeting for 2024-02-15 at 14:00 for 60 minutes")
  await agent.run(
    session,
    "Schedule a project review meeting for 2024-02-15 at 14:00 for 60 minutes with attendees: team@company.com and manager@company.com",
  )

  // Scenario 5: Summary
  console.log("\nUser: Give me a summary of all current tasks and their status")
  await agent.run(session, "Give me a summary of all current tasks and their status")

  // Show session stats
  console.log("\n=== Session Statistics ===")
  console.log(`Total messages: ${session.messages.length}`)
  console.log(`Tasks created: ${taskStore.size}`)

  const lastMessage = getLastAssistantMessage(session)
  if (lastMessage) {
    console.log(`\nLast assistant response preview: ${lastMessage.slice(0, 150)}...`)
  }
}

main().catch(console.error)
