// components/layout/Header.tsx

import { useState, useCallback } from 'react';
import { useProjectStore } from '@/stores/projectStore';
import { useUIStore } from '@/stores/uiStore';

export function Header() {
  const { project, updateTitle } = useProjectStore();
  const { openStyleModal, startPlayback } = useUIStore();
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [titleValue, setTitleValue] = useState('');

  const handleStartEditTitle = useCallback(() => {
    setTitleValue(project?.title ?? '');
    setIsEditingTitle(true);
  }, [project?.title]);

  const handleSaveTitle = useCallback(async () => {
    if (titleValue.trim() && titleValue !== project?.title) {
      await updateTitle(titleValue.trim());
    }
    setIsEditingTitle(false);
  }, [titleValue, project?.title, updateTitle]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        handleSaveTitle();
      } else if (e.key === 'Escape') {
        setIsEditingTitle(false);
      }
    },
    [handleSaveTitle]
  );

  const handlePlayAll = useCallback(() => {
    const firstSlide = project?.slides[0];
    if (firstSlide) {
      startPlayback(firstSlide.sid);
    }
  }, [project?.slides, startPlayback]);

  return (
    <header className="md-eyebrow">
      <div className="flex items-center gap-4">
        <img src="/logo.svg" alt="GenSlides" className="w-8 h-8" />
        {isEditingTitle ? (
          <input
            type="text"
            value={titleValue}
            onChange={(e) => setTitleValue(e.target.value)}
            onBlur={handleSaveTitle}
            onKeyDown={handleKeyDown}
            autoFocus
            className="md-input !py-1 !px-2 !w-auto"
          />
        ) : (
          <h3
            className="cursor-pointer hover:opacity-70 transition-opacity"
            onDoubleClick={handleStartEditTitle}
          >
            {project?.title ?? 'Loading...'}
          </h3>
        )}
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={openStyleModal}
          className="md-btn-secondary !py-1 !px-3 !text-xs"
        >
          {project?.style ? 'Change Style' : 'Set Style'}
        </button>
        <button
          onClick={handlePlayAll}
          disabled={!project?.slides.length}
          className="md-btn !py-1 !px-3 !text-xs"
        >
          Play All
        </button>
        <span className="text-[var(--md-slate)] text-xs uppercase tracking-wider">
          Cost: ${project?.totalCost?.toFixed(2) ?? '0.00'}
        </span>
      </div>
    </header>
  );
}
