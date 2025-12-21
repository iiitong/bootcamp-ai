/**
 * Database connections API
 *
 * Typed API methods for database connection management.
 */

import { del, get, put } from "./client";
import type {
  DatabaseCreateRequest,
  DatabaseInfo,
  DatabaseMetadata,
} from "../types";

/**
 * Database connections API client.
 */
export const databasesApi = {
  /**
   * List all database connections.
   */
  list(): Promise<DatabaseInfo[]> {
    return get<DatabaseInfo[]>("/dbs");
  },

  /**
   * Get metadata for a database connection.
   *
   * @param name - Connection name
   * @param refresh - Force refresh cached metadata
   */
  get(name: string, refresh = false): Promise<DatabaseMetadata> {
    const params = refresh ? "?refresh=true" : "";
    return get<DatabaseMetadata>(`/dbs/${encodeURIComponent(name)}${params}`);
  },

  /**
   * Create or update a database connection.
   *
   * @param name - Connection name
   * @param data - Connection configuration
   */
  create(name: string, data: DatabaseCreateRequest): Promise<DatabaseMetadata> {
    return put<DatabaseMetadata>(
      `/dbs/${encodeURIComponent(name)}`,
      data
    );
  },

  /**
   * Update a database connection (alias for create).
   *
   * @param name - Connection name
   * @param data - Connection configuration
   */
  update(name: string, data: DatabaseCreateRequest): Promise<DatabaseMetadata> {
    return this.create(name, data);
  },

  /**
   * Delete a database connection.
   *
   * @param name - Connection name
   */
  delete(name: string): Promise<void> {
    return del(`/dbs/${encodeURIComponent(name)}`);
  },
};
