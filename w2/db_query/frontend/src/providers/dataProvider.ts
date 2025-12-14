/**
 * Custom Data Provider for Refine
 * Connects to the FastAPI backend at http://localhost:8000
 */

import type { DataProvider } from "@refinedev/core";

const API_URL = "http://localhost:8000/api/v1";

export const dataProvider: DataProvider = {
  getList: async ({ resource }) => {
    const response = await fetch(`${API_URL}/${resource}`);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to fetch list");
    }
    const data = await response.json();
    return {
      data,
      total: data.length,
    };
  },

  getOne: async ({ resource, id }) => {
    const response = await fetch(`${API_URL}/${resource}/${id}`);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to fetch item");
    }
    const data = await response.json();
    return { data };
  },

  create: async ({ resource, variables }) => {
    // Our API uses PUT for create/update (upsert)
    const name = (variables as { name?: string }).name;
    const url = name ? `${API_URL}/${resource}/${name}` : `${API_URL}/${resource}`;

    const response = await fetch(url, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(variables),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to create");
    }
    const data = await response.json();
    return { data };
  },

  update: async ({ resource, id, variables }) => {
    const response = await fetch(`${API_URL}/${resource}/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(variables),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to update");
    }
    const data = await response.json();
    return { data };
  },

  deleteOne: async ({ resource, id }) => {
    const response = await fetch(`${API_URL}/${resource}/${id}`, {
      method: "DELETE",
    });
    if (!response.ok && response.status !== 204) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to delete");
    }
    return { data: { id } as never };
  },

  getApiUrl: () => API_URL,

  // Custom method for executing SQL queries
  custom: async ({ url, method, payload }) => {
    const response = await fetch(`${API_URL}${url}`, {
      method: method?.toUpperCase() || "GET",
      headers: payload ? { "Content-Type": "application/json" } : undefined,
      body: payload ? JSON.stringify(payload) : undefined,
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Request failed");
    }
    const data = await response.json();
    return { data };
  },
};
