import { describe, expect, it } from "vitest"
import { z } from "zod"
import { defineTool, zodToJsonSchema } from "../src/tool/zod-tool.js"

describe("zodToJsonSchema", () => {
  it("should convert string schema", () => {
    const schema = z.string()
    expect(zodToJsonSchema(schema)).toEqual({ type: "string" })
  })

  it("should convert number schema", () => {
    const schema = z.number()
    expect(zodToJsonSchema(schema)).toEqual({ type: "number" })
  })

  it("should convert boolean schema", () => {
    const schema = z.boolean()
    expect(zodToJsonSchema(schema)).toEqual({ type: "boolean" })
  })

  it("should convert array schema", () => {
    const schema = z.array(z.string())
    expect(zodToJsonSchema(schema)).toEqual({
      type: "array",
      items: { type: "string" },
    })
  })

  it("should convert object schema", () => {
    const schema = z.object({
      name: z.string(),
      age: z.number(),
    })
    const result = zodToJsonSchema(schema)
    expect(result.type).toBe("object")
    expect(result.properties).toEqual({
      name: { type: "string" },
      age: { type: "number" },
    })
    expect(result.required).toEqual(["name", "age"])
  })

  it("should handle optional fields", () => {
    const schema = z.object({
      name: z.string(),
      nickname: z.string().optional(),
    })
    const result = zodToJsonSchema(schema)
    expect(result.required).toEqual(["name"])
  })

  it("should convert enum schema", () => {
    const schema = z.enum(["a", "b", "c"])
    expect(zodToJsonSchema(schema)).toEqual({
      type: "string",
      enum: ["a", "b", "c"],
    })
  })

  it("should include descriptions", () => {
    const schema = z.string().describe("A name field")
    expect(zodToJsonSchema(schema)).toEqual({
      type: "string",
      description: "A name field",
    })
  })
})

describe("defineTool", () => {
  it("should create a tool from zod schema", async () => {
    const tool = defineTool({
      name: "add",
      description: "Add two numbers",
      schema: z.object({
        a: z.number(),
        b: z.number(),
      }),
      execute: async ({ a, b }) => ({ output: String(a + b) }),
    })

    expect(tool.name).toBe("add")
    expect(tool.description).toBe("Add two numbers")
    expect(tool.parameters.type).toBe("object")
    expect(tool.parameters.properties).toEqual({
      a: { type: "number" },
      b: { type: "number" },
    })

    const result = await tool.execute({ a: 2, b: 3 })
    expect(result.output).toBe("5")
  })

  it("should validate input against schema", async () => {
    const tool = defineTool({
      name: "greet",
      description: "Greet someone",
      schema: z.object({
        name: z.string(),
      }),
      execute: async ({ name }) => ({ output: `Hello, ${name}!` }),
    })

    // Valid input
    const result = await tool.execute({ name: "World" })
    expect(result.output).toBe("Hello, World!")
    expect(result.error).toBeUndefined()

    // Invalid input returns error result (doesn't throw)
    const errorResult = await tool.execute({ name: 123 })
    expect(errorResult.error).toBeDefined()
    expect(errorResult.output).toContain("Validation error")
  })
})
