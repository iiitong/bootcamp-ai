/**
 * API client exports
 *
 * Centralized exports for the typed API client.
 *
 * @example
 * import { databasesApi, queriesApi, ApiError } from '../api';
 *
 * // List databases
 * const databases = await databasesApi.list();
 *
 * // Execute a query
 * const result = await queriesApi.executeSql('mydb', 'SELECT * FROM users');
 *
 * // Handle errors
 * try {
 *   await databasesApi.get('nonexistent');
 * } catch (error) {
 *   if (error instanceof ApiError) {
 *     console.log(error.code); // 'CONNECTION_NOT_FOUND'
 *   }
 * }
 */

export { ApiError, apiRequest, del, get, post, put } from "./client";
export { databasesApi } from "./databases";
export { queriesApi } from "./queries";
