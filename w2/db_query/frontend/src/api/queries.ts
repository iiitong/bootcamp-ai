/**
 * Query execution API
 *
 * Typed API methods for SQL query execution and natural language queries.
 */

import { post } from "./client";
import type {
  NaturalLanguageQueryRequest,
  NaturalLanguageQueryResult,
  QueryRequest,
  QueryResult,
} from "../types";

/**
 * Query execution API client.
 */
export const queriesApi = {
  /**
   * Execute a SQL query against a database.
   *
   * @param databaseName - Name of the database connection
   * @param request - SQL query request
   */
  execute(databaseName: string, request: QueryRequest): Promise<QueryResult> {
    return post<QueryResult>(
      `/dbs/${encodeURIComponent(databaseName)}/query`,
      request
    );
  },

  /**
   * Execute SQL directly (convenience method).
   *
   * @param databaseName - Name of the database connection
   * @param sql - SQL query string
   */
  executeSql(databaseName: string, sql: string): Promise<QueryResult> {
    return this.execute(databaseName, { sql });
  },

  /**
   * Generate SQL from natural language description.
   *
   * @param databaseName - Name of the database connection
   * @param request - Natural language query request
   */
  generateFromNaturalLanguage(
    databaseName: string,
    request: NaturalLanguageQueryRequest
  ): Promise<NaturalLanguageQueryResult> {
    return post<NaturalLanguageQueryResult>(
      `/dbs/${encodeURIComponent(databaseName)}/query/natural`,
      request
    );
  },

  /**
   * Generate SQL from prompt (convenience method).
   *
   * @param databaseName - Name of the database connection
   * @param prompt - Natural language description
   */
  generateSql(
    databaseName: string,
    prompt: string
  ): Promise<NaturalLanguageQueryResult> {
    return this.generateFromNaturalLanguage(databaseName, { prompt });
  },
};
