/**
 * Extract a human-readable error message from an API error response.
 * Handles various error formats returned by the backend.
 */
export function getErrorMessage(error: unknown): string {
  if (typeof error === "string") {
    return error;
  }

  if (error instanceof Error) {
    return error.message;
  }

  if (error && typeof error === "object") {
    // Handle FastAPI validation errors
    if ("detail" in error) {
      const detail = (error as { detail: unknown }).detail;

      if (typeof detail === "string") {
        return detail;
      }

      // FastAPI validation error format: { detail: [{ loc: [...], msg: "...", type: "..." }] }
      if (Array.isArray(detail)) {
        return detail
          .map((item) => {
            if (typeof item === "object" && item !== null && "msg" in item) {
              const loc = "loc" in item ? (item.loc as string[]).join(".") : "";
              return loc ? `${loc}: ${item.msg}` : item.msg;
            }
            return String(item);
          })
          .join("; ");
      }

      // Nested object
      if (typeof detail === "object" && detail !== null) {
        return JSON.stringify(detail);
      }
    }

    // Generic error object with message
    if ("message" in error && typeof error.message === "string") {
      return error.message;
    }

    // Last resort: stringify the object
    return JSON.stringify(error);
  }

  return "Unknown error";
}

/**
 * Parse an API error response and throw an Error with a proper message.
 */
export async function handleApiError(response: Response, fallbackMessage: string): Promise<never> {
  let errorMessage = fallbackMessage;

  try {
    const errorData = await response.json();
    errorMessage = getErrorMessage(errorData) || fallbackMessage;
  } catch {
    // If JSON parsing fails, use status text
    errorMessage = response.statusText || fallbackMessage;
  }

  throw new Error(errorMessage);
}
