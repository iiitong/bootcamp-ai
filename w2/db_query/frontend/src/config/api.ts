/**
 * API configuration
 * Centralized API URL configuration to avoid hardcoding across components
 */

// API URL from environment variable, with fallback for development
export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
