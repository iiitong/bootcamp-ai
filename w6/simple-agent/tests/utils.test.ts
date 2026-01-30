import { describe, expect, it } from "vitest"
import { generateId, sleep, withRetry } from "../src/utils.js"

describe("generateId", () => {
  it("should generate a string ID", () => {
    const id = generateId()
    expect(typeof id).toBe("string")
    expect(id.length).toBeGreaterThan(0)
  })

  it("should generate unique IDs", () => {
    const ids = new Set<string>()
    for (let i = 0; i < 100; i++) {
      ids.add(generateId())
    }
    expect(ids.size).toBe(100)
  })
})

describe("sleep", () => {
  it("should wait for specified milliseconds", async () => {
    const start = Date.now()
    await sleep(50)
    const elapsed = Date.now() - start
    expect(elapsed).toBeGreaterThanOrEqual(45)
    expect(elapsed).toBeLessThan(100)
  })
})

describe("withRetry", () => {
  const defaultConfig = {
    maxRetries: 3,
    baseDelay: 10,
    maxDelay: 100,
    retryableErrors: ["fail", "retry"],
  }

  it("should return result on success", async () => {
    const result = await withRetry(() => Promise.resolve("success"), defaultConfig)
    expect(result).toBe("success")
  })

  it("should retry on failure and eventually succeed", async () => {
    let attempts = 0
    const result = await withRetry(() => {
      attempts++
      if (attempts < 3) {
        throw new Error("fail")
      }
      return Promise.resolve("success")
    }, defaultConfig)
    expect(result).toBe("success")
    expect(attempts).toBe(3)
  })

  it("should throw after max retries", async () => {
    let attempts = 0
    await expect(
      withRetry(
        () => {
          attempts++
          throw new Error("always fail")
        },
        { ...defaultConfig, maxRetries: 2 },
      ),
    ).rejects.toThrow("always fail")
    expect(attempts).toBe(3) // initial + 2 retries
  })

  it("should throw immediately for non-retryable errors", async () => {
    let attempts = 0
    await expect(
      withRetry(() => {
        attempts++
        throw new Error("unknown error")
      }, defaultConfig),
    ).rejects.toThrow("unknown error")
    expect(attempts).toBe(1) // no retries
  })
})
