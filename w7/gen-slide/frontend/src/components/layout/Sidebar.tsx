// components/layout/Sidebar.tsx

import { SlideList } from '@/components/slides/SlideList';
import { useSlides } from '@/hooks/useSlides';

export function Sidebar() {
  const { slides, selectedSid, selectSlide, createSlide, reorderSlides } =
    useSlides();

  const handleAddSlide = async () => {
    await createSlide('New slide content', selectedSid ?? undefined);
  };

  return (
    <aside className="w-64 bg-[var(--md-cloud)] border-r-2 border-[var(--md-graphite)] flex flex-col">
      <div className="p-3 border-b-2 border-[var(--md-graphite)] flex justify-between items-center">
        <span className="text-[var(--md-ink)] text-xs font-bold uppercase tracking-wider">Slides</span>
        <button
          onClick={handleAddSlide}
          className="md-btn !p-1 !text-xs"
          title="Add slide"
        >
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
              d="M12 4v16m8-8H4"
            />
          </svg>
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 bg-[var(--md-fog)]">
        <SlideList
          slides={slides}
          selectedSid={selectedSid}
          onSelect={selectSlide}
          onReorder={reorderSlides}
        />
      </div>
    </aside>
  );
}
