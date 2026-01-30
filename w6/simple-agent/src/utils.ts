import { nanoid } from "nanoid"

export function generateId(): string {
  return nanoid()
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function isRetryableError(error: unknown, retryableErrors: string[]): boolean {
  if (error instanceof Error) {
    return retryableErrors.some(
      (e) =>
        error.message.includes(e) || error.name.includes(e) || error.constructor.name.includes(e),
    )
  }
  return false
}

export async function withRetry<T>(
  fn: () => Promise<T>,
  config: { maxRetries: number; baseDelay: number; maxDelay: number; retryableErrors: string[] },
): Promise<T> {
  let lastError: Error | undefined

  for (let i = 0; i <= config.maxRetries; i++) {
    try {
      return await fn()
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error))

      if (!isRetryableError(error, config.retryableErrors)) {
        throw error
      }

      if (i < config.maxRetries) {
        const delay = Math.min(config.baseDelay * 2 ** i, config.maxDelay)
        const jitter = Math.random() * delay * 0.1
        await sleep(delay + jitter)
      }
    }
  }

  throw lastError ?? new Error("Retry failed")
}
