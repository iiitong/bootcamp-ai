// components/player/FullscreenPlayer.tsx

import { useState, useEffect, useCallback } from 'react';
import { useUIStore } from '@/stores/uiStore';
import { useProjectStore } from '@/stores/projectStore';

const PLAYBACK_INTERVAL = 5000; // 5 seconds per slide

export function FullscreenPlayer() {
  const { isFullscreenPlaying, playStartSid, stopPlayback } = useUIStore();
  const { project } = useProjectStore();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

  const slides = project?.slides ?? [];

  // Find starting index
  useEffect(() => {
    if (playStartSid && slides.length > 0) {
      const index = slides.findIndex((s) => s.sid === playStartSid);
      setCurrentIndex(index >= 0 ? index : 0);
    }
  }, [playStartSid, slides]);

  // Auto-advance slides
  useEffect(() => {
    if (!isFullscreenPlaying || isPaused || slides.length === 0) return;

    const timer = setInterval(() => {
      setCurrentIndex((prev) => {
        const next = prev + 1;
        if (next >= slides.length) {
          return 0; // Loop back to start
        }
        return next;
      });
    }, PLAYBACK_INTERVAL);

    return () => clearInterval(timer);
  }, [isFullscreenPlaying, isPaused, slides.length]);

  // Keyboard navigation
  useEffect(() => {
    if (!isFullscreenPlaying) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'Escape':
          stopPlayback();
          break;
        case 'ArrowLeft':
          setCurrentIndex((prev) => Math.max(0, prev - 1));
          break;
        case 'ArrowRight':
          setCurrentIndex((prev) => Math.min(slides.length - 1, prev + 1));
          break;
        case ' ':
          e.preventDefault();
          setIsPaused((prev) => !prev);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFullscreenPlaying, slides.length, stopPlayback]);

  const handlePrevious = useCallback(() => {
    setCurrentIndex((prev) => Math.max(0, prev - 1));
  }, []);

  const handleNext = useCallback(() => {
    setCurrentIndex((prev) => Math.min(slides.length - 1, prev + 1));
  }, [slides.length]);

  if (!isFullscreenPlaying) return null;

  const currentSlide = slides[currentIndex];
  if (!currentSlide) return null;

  // Get the best image for this slide
  const imageUrl = currentSlide.hasMatchingImage
    ? currentSlide.images.find((img) => img.hash === currentSlide.currentHash)
        ?.url
    : currentSlide.images[0]?.url;

  return (
    <div className="fixed inset-0 z-50 bg-black flex flex-col">
      {/* Image display */}
      <div className="flex-1 flex items-center justify-center p-4">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={`Slide ${currentIndex + 1}`}
            className="max-w-full max-h-full object-contain"
          />
        ) : (
          <div className="text-[var(--md-slate)]">No image available</div>
        )}
      </div>

      {/* Controls overlay */}
      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-6">
        <div className="max-w-4xl mx-auto">
          {/* Progress bar */}
          <div className="flex gap-1 mb-4">
            {slides.map((_, index) => (
              <button
                key={index}
                onClick={() => setCurrentIndex(index)}
                className={`
                  h-1 flex-1 rounded-full transition-colors
                  ${index === currentIndex ? 'bg-[var(--md-sunbeam)]' : 'bg-white/30 hover:bg-white/50'}
                `}
              />
            ))}
          </div>

          {/* Controls */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={handlePrevious}
                disabled={currentIndex === 0}
                className="text-white/80 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <svg
                  className="w-8 h-8"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 19l-7-7 7-7"
                  />
                </svg>
              </button>

              <button
                onClick={() => setIsPaused((prev) => !prev)}
                className="text-white/80 hover:text-white"
              >
                {isPaused ? (
                  <svg
                    className="w-10 h-10"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M8 5v14l11-7z" />
                  </svg>
                ) : (
                  <svg
                    className="w-10 h-10"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M6 4h4v16H6zm8 0h4v16h-4z" />
                  </svg>
                )}
              </button>

              <button
                onClick={handleNext}
                disabled={currentIndex === slides.length - 1}
                className="text-white/80 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <svg
                  className="w-8 h-8"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </button>
            </div>

            <div className="text-white/60">
              {currentIndex + 1} / {slides.length}
            </div>

            <button
              onClick={stopPlayback}
              className="text-white/80 hover:text-white"
            >
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* Content preview */}
          <div className="mt-4 text-white/70 text-center text-sm line-clamp-2">
            {currentSlide.content}
          </div>
        </div>
      </div>
    </div>
  );
}
