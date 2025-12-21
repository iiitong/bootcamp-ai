/**
 * HTTP API client for DB Query Tool
 *
 * Provides a typed interface for making API requests with proper
 * error handling and response parsing.
 */

import { API_URL } from "../config/api";
import type { ErrorResponse } from "../types";

/**
 * Custom error class for API errors with structured error information.
 */
export class ApiError extends Error {
  constructor(
    public response: ErrorResponse,
    public status: number
  ) {
    super(response.detail);
    this.name = "ApiError";
  }

  get code(): string {
    return this.response.code;
  }
}

/**
 * Make a typed API request.
 *
 * @param path - API path (will be appended to API_URL)
 * @param options - Fetch options
 * @returns Parsed JSON response
 * @throws ApiError on non-2xx responses
 */
export async function apiRequest<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_URL}${path}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  // Handle empty responses (e.g., 204 No Content)
  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json();

  if (!response.ok) {
    throw new ApiError(data as ErrorResponse, response.status);
  }

  return data as T;
}

/**
 * Make a GET request.
 */
export function get<T>(path: string): Promise<T> {
  return apiRequest<T>(path, { method: "GET" });
}

/**
 * Make a POST request with JSON body.
 */
export function post<T>(path: string, body: unknown): Promise<T> {
  return apiRequest<T>(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/**
 * Make a PUT request with JSON body.
 */
export function put<T>(path: string, body: unknown): Promise<T> {
  return apiRequest<T>(path, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

/**
 * Make a DELETE request.
 */
export function del<T = void>(path: string): Promise<T> {
  return apiRequest<T>(path, { method: "DELETE" });
}
