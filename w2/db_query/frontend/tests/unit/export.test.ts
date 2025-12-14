import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  exportToCSV,
  exportToJSON,
  escapeCSVField,
  generateFilename,
} from "../../src/utils/export";

describe("escapeCSVField", () => {
  it("should return empty string for null", () => {
    expect(escapeCSVField(null)).toBe("");
  });

  it("should return empty string for undefined", () => {
    expect(escapeCSVField(undefined)).toBe("");
  });

  it("should return string as-is when no special characters", () => {
    expect(escapeCSVField("hello")).toBe("hello");
    expect(escapeCSVField(123)).toBe("123");
    expect(escapeCSVField(true)).toBe("true");
  });

  it("should wrap in quotes and escape when contains comma", () => {
    expect(escapeCSVField("hello,world")).toBe('"hello,world"');
  });

  it("should wrap in quotes and escape when contains newline", () => {
    expect(escapeCSVField("hello\nworld")).toBe('"hello\nworld"');
  });

  it("should wrap in quotes and double internal quotes", () => {
    expect(escapeCSVField('say "hello"')).toBe('"say ""hello"""');
  });

  it("should handle multiple special characters", () => {
    expect(escapeCSVField('a,b\n"c"')).toBe('"a,b\n""c"""');
  });

  it("should handle Chinese characters", () => {
    expect(escapeCSVField("你好")).toBe("你好");
    expect(escapeCSVField("你好,世界")).toBe('"你好,世界"');
  });
});

describe("generateFilename", () => {
  it("should generate filename with correct format", () => {
    const filename = generateFilename("csv");
    expect(filename).toMatch(/^query_result_\d{8}_\d{6}\.csv$/);
  });

  it("should generate json filename with correct format", () => {
    const filename = generateFilename("json");
    expect(filename).toMatch(/^query_result_\d{8}_\d{6}\.json$/);
  });
});

describe("exportToCSV", () => {
  let mockClick: ReturnType<typeof vi.fn>;
  let mockAppendChild: ReturnType<typeof vi.fn>;
  let mockRemoveChild: ReturnType<typeof vi.fn>;
  let capturedContent: string = "";

  beforeEach(() => {
    mockClick = vi.fn();
    mockAppendChild = vi.fn();
    mockRemoveChild = vi.fn();

    // Mock document.createElement
    vi.spyOn(document, "createElement").mockImplementation(() => {
      return {
        href: "",
        download: "",
        style: { display: "" },
        click: mockClick,
      } as unknown as HTMLAnchorElement;
    });

    // Mock document.body
    vi.spyOn(document.body, "appendChild").mockImplementation(mockAppendChild);
    vi.spyOn(document.body, "removeChild").mockImplementation(mockRemoveChild);

    // Capture content from Blob constructor
    const OriginalBlob = Blob;
    vi.spyOn(global, "Blob").mockImplementation((parts, options) => {
      capturedContent = parts?.[0] as string || "";
      return new OriginalBlob(parts, options);
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    capturedContent = "";
  });

  it("should include UTF-8 BOM at the start", async () => {
    const columns = ["name"];
    const rows = [{ name: "test" }];

    exportToCSV(columns, rows);

    // Check for BOM (U+FEFF)
    expect(capturedContent.charCodeAt(0)).toBe(0xfeff);
  });

  it("should generate correct CSV content", () => {
    const columns = ["id", "name", "email"];
    const rows = [
      { id: 1, name: "张三", email: "zhang@test.com" },
      { id: 2, name: "李四", email: "li@test.com" },
    ];

    exportToCSV(columns, rows);

    // Remove BOM for easier comparison
    const contentWithoutBOM = capturedContent.slice(1);

    expect(contentWithoutBOM).toBe(
      "id,name,email\n1,张三,zhang@test.com\n2,李四,li@test.com"
    );
  });

  it("should escape special characters in CSV", () => {
    const columns = ["value"];
    const rows = [{ value: 'has,comma and "quotes"' }];

    exportToCSV(columns, rows);

    const contentWithoutBOM = capturedContent.slice(1);

    expect(contentWithoutBOM).toBe('value\n"has,comma and ""quotes"""');
  });

  it("should trigger download", () => {
    exportToCSV(["col"], [{ col: "val" }]);

    expect(mockClick).toHaveBeenCalled();
    expect(mockAppendChild).toHaveBeenCalled();
    expect(mockRemoveChild).toHaveBeenCalled();
  });

  it("should use custom filename when provided", () => {
    const createElement = vi.spyOn(document, "createElement");

    exportToCSV(["col"], [{ col: "val" }], "custom_export");

    const linkElement = createElement.mock.results[0].value;
    expect(linkElement.download).toBe("custom_export.csv");
  });
});

describe("exportToJSON", () => {
  let mockClick: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockClick = vi.fn();

    vi.spyOn(document, "createElement").mockImplementation(() => {
      return {
        href: "",
        download: "",
        style: { display: "" },
        click: mockClick,
      } as unknown as HTMLAnchorElement;
    });

    vi.spyOn(document.body, "appendChild").mockImplementation(() => null as unknown as HTMLElement);
    vi.spyOn(document.body, "removeChild").mockImplementation(() => null as unknown as HTMLElement);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should generate valid JSON array format", () => {
    const rows = [
      { id: 1, name: "张三" },
      { id: 2, name: "李四" },
    ];

    vi.spyOn(global, "Blob").mockImplementation(() => ({
      type: "application/json",
    } as Blob));

    exportToJSON(rows);

    const blobCall = vi.mocked(global.Blob).mock.calls[0];
    const content = blobCall[0][0] as string;

    // Should be valid JSON
    const parsed = JSON.parse(content);
    expect(parsed).toEqual(rows);
  });

  it("should format JSON with 2-space indentation", () => {
    const rows = [{ id: 1 }];

    vi.spyOn(global, "Blob").mockImplementation(() => ({
      type: "application/json",
    } as Blob));

    exportToJSON(rows);

    const blobCall = vi.mocked(global.Blob).mock.calls[0];
    const content = blobCall[0][0] as string;

    // Check for 2-space indentation
    expect(content).toContain("  ");
    expect(content).toBe('[\n  {\n    "id": 1\n  }\n]');
  });

  it("should trigger download", () => {
    vi.spyOn(global, "Blob").mockImplementation(() => ({
      type: "application/json",
    } as Blob));

    exportToJSON([{ col: "val" }]);

    expect(mockClick).toHaveBeenCalled();
  });

  it("should use custom filename when provided", () => {
    const createElement = vi.spyOn(document, "createElement");

    vi.spyOn(global, "Blob").mockImplementation(() => ({
      type: "application/json",
    } as Blob));

    exportToJSON([{ col: "val" }], "my_data");

    const linkElement = createElement.mock.results[0].value;
    expect(linkElement.download).toBe("my_data.json");
  });
});

describe("Empty results handling", () => {
  it("should handle empty rows array for CSV", () => {
    vi.spyOn(global, "Blob").mockImplementation(() => ({
      type: "text/csv",
    } as Blob));
    vi.spyOn(document, "createElement").mockImplementation(() => ({
      href: "",
      download: "",
      style: { display: "" },
      click: vi.fn(),
    } as unknown as HTMLAnchorElement));
    vi.spyOn(document.body, "appendChild").mockImplementation(() => null as unknown as HTMLElement);
    vi.spyOn(document.body, "removeChild").mockImplementation(() => null as unknown as HTMLElement);

    // Should not throw
    expect(() => exportToCSV(["col1", "col2"], [])).not.toThrow();

    const blobCall = vi.mocked(global.Blob).mock.calls[0];
    const content = blobCall[0][0] as string;
    const contentWithoutBOM = content.slice(1);

    // Should only have header
    expect(contentWithoutBOM).toBe("col1,col2");
  });

  it("should handle empty rows array for JSON", () => {
    vi.spyOn(global, "Blob").mockImplementation(() => ({
      type: "application/json",
    } as Blob));
    vi.spyOn(document, "createElement").mockImplementation(() => ({
      href: "",
      download: "",
      style: { display: "" },
      click: vi.fn(),
    } as unknown as HTMLAnchorElement));
    vi.spyOn(document.body, "appendChild").mockImplementation(() => null as unknown as HTMLElement);
    vi.spyOn(document.body, "removeChild").mockImplementation(() => null as unknown as HTMLElement);

    // Should not throw
    expect(() => exportToJSON([])).not.toThrow();

    const blobCall = vi.mocked(global.Blob).mock.calls[0];
    const content = blobCall[0][0] as string;

    expect(content).toBe("[]");
  });
});
