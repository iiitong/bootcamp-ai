import { z } from "zod"
import type { JSONSchema, Tool, ToolResult, ZodTool } from "../types.js"

function zodToJsonSchema(schema: z.ZodType): JSONSchema {
  if (schema instanceof z.ZodString) {
    const jsonSchema: JSONSchema = { type: "string" }
    if (schema.description) {
      jsonSchema.description = schema.description
    }
    return jsonSchema
  }

  if (schema instanceof z.ZodNumber) {
    const jsonSchema: JSONSchema = { type: "number" }
    if (schema.description) {
      jsonSchema.description = schema.description
    }
    return jsonSchema
  }

  if (schema instanceof z.ZodBoolean) {
    const jsonSchema: JSONSchema = { type: "boolean" }
    if (schema.description) {
      jsonSchema.description = schema.description
    }
    return jsonSchema
  }

  if (schema instanceof z.ZodArray) {
    const jsonSchema: JSONSchema = {
      type: "array",
      items: zodToJsonSchema(schema.element as unknown as z.ZodType),
    }
    if (schema.description) {
      jsonSchema.description = schema.description
    }
    return jsonSchema
  }

  if (schema instanceof z.ZodObject) {
    const shape = schema.shape as Record<string, z.ZodType>
    const properties: Record<string, JSONSchema> = {}
    const required: string[] = []

    for (const [key, value] of Object.entries(shape)) {
      properties[key] = zodToJsonSchema(value)

      // Check if field is required (not optional)
      if (!(value instanceof z.ZodOptional)) {
        required.push(key)
      }
    }

    const jsonSchema: JSONSchema = {
      type: "object",
      properties,
    }

    if (required.length > 0) {
      jsonSchema.required = required
    }

    if (schema.description) {
      jsonSchema.description = schema.description
    }

    return jsonSchema
  }

  if (schema instanceof z.ZodOptional) {
    return zodToJsonSchema(schema.unwrap() as unknown as z.ZodType)
  }

  if (schema instanceof z.ZodNullable) {
    return zodToJsonSchema(schema.unwrap() as unknown as z.ZodType)
  }

  if (schema instanceof z.ZodEnum) {
    const jsonSchema: JSONSchema = {
      type: "string",
      enum: schema.options,
    }
    if (schema.description) {
      jsonSchema.description = schema.description
    }
    return jsonSchema
  }

  if (schema instanceof z.ZodLiteral) {
    const value = schema.value
    const jsonSchema: JSONSchema = {
      type: typeof value as string,
      enum: [value],
    }
    return jsonSchema
  }

  if (schema instanceof z.ZodUnion) {
    // Simplified: just return the first option's schema
    const options = schema.options as z.ZodType[]
    if (options[0]) {
      return zodToJsonSchema(options[0])
    }
  }

  if (schema instanceof z.ZodDefault) {
    return zodToJsonSchema(schema.removeDefault() as unknown as z.ZodType)
  }

  // Fallback
  return { type: "object" }
}

export function defineTool<TSchema extends z.ZodType>(
  config: ZodTool<TSchema>,
): Tool<z.infer<TSchema>> {
  return {
    name: config.name,
    description: config.description,
    parameters: zodToJsonSchema(config.schema),
    execute: async (args: unknown): Promise<ToolResult> => {
      const parsed = config.schema.safeParse(args)

      if (!parsed.success) {
        return {
          output: `Validation error: ${parsed.error.message}`,
          error: parsed.error.message,
        }
      }

      return config.execute(parsed.data)
    },
  }
}

export { zodToJsonSchema }
