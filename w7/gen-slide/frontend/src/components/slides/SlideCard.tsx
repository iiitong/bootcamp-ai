// components/slides/SlideCard.tsx

import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import type { Slide } from '@/types';

interface SlideCardProps {
  slide: Slide;
  index: number;
  isSelected: boolean;
  isDragging: boolean;
  isDragOverlay?: boolean;
  onClick?: () => void;
}

export function SlideCard({
  slide,
  index,
  isSelected,
  isDragging,
  isDragOverlay,
  onClick,
}: SlideCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: slide.sid });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  // Get thumbnail image URL
  const thumbnailUrl = slide.hasMatchingImage
    ? slide.images.find((img) => img.hash === slide.currentHash)?.url
    : slide.images[0]?.url;

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={onClick}
      className={`
        slide-card
        ${isSelected ? 'selected' : ''}
        ${isDragging && !isDragOverlay ? 'dragging' : ''}
        ${isDragOverlay ? 'shadow-xl scale-105' : ''}
      `}
    >
      {/* Slide number badge */}
      <div className="absolute top-1 left-1 z-10 md-badge !py-0 !px-1 !text-[10px]">
        {index + 1}
      </div>

      {/* Status indicator */}
      {!slide.hasMatchingImage && slide.images.length > 0 && (
        <div
          className="absolute top-1 right-1 z-10 w-2 h-2 rounded-full bg-[var(--md-watermelon)]"
          title="Image doesn't match current content"
        />
      )}

      {/* Thumbnail */}
      <div className="aspect-video bg-[var(--md-fog)] border-b-2 border-[var(--md-graphite)]">
        {thumbnailUrl ? (
          <img
            src={thumbnailUrl}
            alt={`Slide ${index + 1}`}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-[var(--md-slate)]">
            <svg
              className="w-8 h-8"
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
          </div>
        )}
      </div>

      {/* Content preview */}
      <div className="px-2 py-1.5">
        <p className="text-[var(--md-ink)] text-xs line-clamp-2">{slide.content}</p>
      </div>
    </div>
  );
}
