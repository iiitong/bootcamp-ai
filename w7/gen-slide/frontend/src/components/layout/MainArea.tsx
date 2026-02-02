// components/layout/MainArea.tsx

import { SlideEditor } from '@/components/slides/SlideEditor';
import { ImageViewer } from '@/components/images/ImageViewer';
import { ImageThumbnails } from '@/components/images/ImageThumbnails';
import { GenerateButton } from '@/components/images/GenerateButton';
import { useSlides } from '@/hooks/useSlides';
import { useProjectStore } from '@/stores/projectStore';

export function MainArea() {
  const {
    currentSlide,
    selectedImageHash,
    editingSid,
    selectImage,
    startEditing,
    stopEditing,
    updateSlide,
    deleteSlide,
    generateImage,
    isGenerating,
    getGeneratingError,
  } = useSlides();
  const { project } = useProjectStore();

  if (!currentSlide) {
    return (
      <main className="flex-1 bg-[var(--md-cream)] flex items-center justify-center">
        <div className="text-center text-[var(--md-slate)]">
          <svg
            className="w-16 h-16 mx-auto mb-4 opacity-50"
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
          <p>Select a slide to view</p>
          <p className="text-sm mt-2">
            Or add a new slide using the + button in the sidebar
          </p>
        </div>
      </main>
    );
  }

  const selectedImage = currentSlide.images.find(
    (img) => img.hash === selectedImageHash
  );
  const isCurrentlyGenerating = isGenerating(currentSlide.sid);
  // Only show error if there's no image to display
  const generatingError = selectedImage ? null : getGeneratingError(currentSlide.sid);

  return (
    <main className="flex-1 bg-[var(--md-cream)] flex flex-col overflow-hidden">
      {/* Image viewer */}
      <div className="flex-1 flex items-center justify-center p-4 min-h-0">
        <ImageViewer
          imageUrl={selectedImage?.url}
          isGenerating={isCurrentlyGenerating}
          error={generatingError}
        />
      </div>

      {/* Bottom panel */}
      <div className="border-t-2 border-[var(--md-graphite)] bg-[var(--md-cloud)] p-4">
        <div className="flex gap-4">
          {/* Slide editor */}
          <div className="flex-1 min-w-0">
            <SlideEditor
              slide={currentSlide}
              isEditing={editingSid === currentSlide.sid}
              onStartEdit={() => startEditing(currentSlide.sid)}
              onStopEdit={stopEditing}
              onSave={(content) => updateSlide(currentSlide.sid, content)}
              onDelete={() => deleteSlide(currentSlide.sid)}
            />
          </div>

          {/* Thumbnails and generate button */}
          <div className="w-80 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-[var(--md-slate)] text-xs uppercase tracking-wider">
                Images ({currentSlide.images.length})
              </span>
              <GenerateButton
                onClick={() => generateImage(currentSlide.sid)}
                isGenerating={isCurrentlyGenerating}
                hasStyle={!!project?.style}
              />
            </div>
            <ImageThumbnails
              images={currentSlide.images}
              selectedHash={selectedImageHash}
              currentHash={currentSlide.currentHash}
              onSelect={selectImage}
            />
            {!currentSlide.hasMatchingImage && currentSlide.images.length > 0 && (
              <p className="text-[var(--md-watermelon)] text-xs">
                Content has changed. Generate a new image to match.
              </p>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
