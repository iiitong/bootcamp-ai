// components/images/ImageThumbnails.tsx

import type { SlideImage } from '@/types';

interface ImageThumbnailsProps {
  images: SlideImage[];
  selectedHash: string | null;
  currentHash: string;
  onSelect: (hash: string) => void;
}

export function ImageThumbnails({
  images,
  selectedHash,
  currentHash,
  onSelect,
}: ImageThumbnailsProps) {
  if (images.length === 0) {
    return (
      <div className="text-[var(--md-slate)] text-sm text-center py-4">
        No images generated yet
      </div>
    );
  }

  return (
    <div className="flex gap-2 overflow-x-auto pb-2">
      {images.map((image) => {
        const isSelected = image.hash === selectedHash;
        const isMatchingCurrent = image.hash === currentHash;

        return (
          <button
            key={image.hash}
            onClick={() => onSelect(image.hash)}
            className={`
              relative flex-shrink-0 w-20 h-12 overflow-hidden
              transition-all border-2
              ${isSelected ? 'border-[var(--md-sky-strong)]' : 'border-[var(--md-graphite)] hover:border-[var(--md-sky)]'}
            `}
          >
            <img
              src={image.url}
              alt={`Image ${image.hash.slice(0, 8)}`}
              className="w-full h-full object-cover"
            />
            {isMatchingCurrent && (
              <div
                className="absolute bottom-0.5 right-0.5 w-2 h-2 rounded-full bg-[var(--md-sky-strong)]"
                title="Matches current content"
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
