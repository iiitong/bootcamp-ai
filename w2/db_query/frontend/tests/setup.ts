import "@testing-library/jest-dom/vitest";

// Mock URL.createObjectURL and URL.revokeObjectURL for tests
global.URL.createObjectURL = vi.fn(() => "blob:mock-url");
global.URL.revokeObjectURL = vi.fn();
