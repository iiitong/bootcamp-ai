// components/images/ImageViewer.tsx

interface ImageViewerProps {
  imageUrl?: string;
  isGenerating: boolean;
  error?: string | null;
}

export function ImageViewer({ imageUrl, isGenerating, error }: ImageViewerProps) {
  if (isGenerating) {
    return (
      <div className="w-full max-w-4xl aspect-video md-card flex flex-col items-center justify-center">
        <div className="w-12 h-12 border-4 border-[var(--md-sky)] border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-[var(--md-ink)]">Generating image...</p>
        <p className="text-[var(--md-slate)] text-sm mt-1">This may take a few seconds</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full max-w-4xl aspect-video md-card flex flex-col items-center justify-center">
        <svg
          className="w-12 h-12 text-[var(--md-watermelon)] mb-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <p className="text-[var(--md-watermelon)]">Generation failed</p>
        <p className="text-[var(--md-slate)] text-sm mt-1">{error}</p>
      </div>
    );
  }

  if (!imageUrl) {
    return (
      <div className="w-full max-w-4xl aspect-video md-card flex flex-col items-center justify-center">
        <svg
          className="w-16 h-16 text-[var(--md-slate)] mb-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
        <p className="text-[var(--md-ink)]">No image yet</p>
        <p className="text-[var(--md-slate)] text-sm mt-1">
          Click "Generate" to create an image
        </p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-4xl">
      <img
        src={imageUrl}
        alt="Slide image"
        className="w-full border-2 border-[var(--md-graphite)]"
      />
    </div>
  );
}
