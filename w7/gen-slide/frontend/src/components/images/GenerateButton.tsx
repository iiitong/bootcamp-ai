// components/images/GenerateButton.tsx

interface GenerateButtonProps {
  onClick: () => void;
  isGenerating: boolean;
  hasStyle: boolean;
}

export function GenerateButton({
  onClick,
  isGenerating,
  hasStyle,
}: GenerateButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={isGenerating || !hasStyle}
      className="md-btn !py-1 !px-3 !text-xs"
      title={!hasStyle ? 'Set a style first to generate images' : undefined}
    >
      {isGenerating ? (
        <>
          <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
          Generating...
        </>
      ) : (
        <>
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 10V3L4 14h7v7l9-11h-7z"
            />
          </svg>
          Generate
        </>
      )}
    </button>
  );
}
