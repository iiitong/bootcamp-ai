import { memo, useCallback } from "react";
import Editor from "@monaco-editor/react";
import type { editor } from "monaco-editor";

interface SqlEditorProps {
  value: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
  height?: string;
  placeholder?: string;
}

const editorOptions: editor.IStandaloneEditorConstructionOptions = {
  lineNumbers: "on",
  minimap: { enabled: false },
  fontSize: 14,
  fontFamily: "'Fira Code', 'Monaco', 'Menlo', monospace",
  wordWrap: "on",
  scrollBeyondLastLine: false,
  automaticLayout: true,
  formatOnPaste: false,
  formatOnType: false,
  renderLineHighlight: "gutter",
  folding: true,
  tabSize: 2,
  padding: { top: 8, bottom: 8 },
};

export const SqlEditor = memo<SqlEditorProps>(function SqlEditor({
  value,
  onChange,
  readOnly = false,
  height = "200px",
}) {
  const handleChange = useCallback(
    (newValue: string | undefined) => {
      if (newValue !== undefined) {
        onChange(newValue);
      }
    },
    [onChange]
  );

  return (
    <div className="border border-gray-300 rounded overflow-hidden">
      <Editor
        height={height}
        language="sql"
        value={value}
        onChange={handleChange}
        theme="vs-dark"
        options={{ ...editorOptions, readOnly }}
        loading={
          <div className="flex items-center justify-center h-full bg-gray-800 text-gray-400">
            Loading editor...
          </div>
        }
      />
    </div>
  );
});
