// components/slides/SlideList.tsx

import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { SlideCard } from './SlideCard';
import { useDragAndDrop } from '@/hooks/useDragAndDrop';
import type { Slide } from '@/types';

interface SlideListProps {
  slides: Slide[];
  selectedSid: string | null;
  onSelect: (sid: string) => void;
  onReorder: (order: string[]) => Promise<void>;
}

export function SlideList({
  slides,
  selectedSid,
  onSelect,
  onReorder,
}: SlideListProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const {
    activeId,
    activeItem,
    itemIds,
    handleDragStart,
    handleDragEnd,
    handleDragCancel,
  } = useDragAndDrop({
    items: slides,
    getId: (slide) => slide.sid,
    onReorder,
  });

  if (slides.length === 0) {
    return (
      <div className="text-center text-[var(--md-slate)] py-8">
        <p className="text-sm">No slides yet</p>
        <p className="text-xs mt-1">Click + to add one</p>
      </div>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      <SortableContext items={itemIds} strategy={verticalListSortingStrategy}>
        <div className="space-y-2">
          {slides.map((slide, index) => (
            <SlideCard
              key={slide.sid}
              slide={slide}
              index={index}
              isSelected={slide.sid === selectedSid}
              isDragging={slide.sid === activeId}
              onClick={() => onSelect(slide.sid)}
            />
          ))}
        </div>
      </SortableContext>

      <DragOverlay>
        {activeItem && (
          <SlideCard
            slide={activeItem}
            index={slides.findIndex((s) => s.sid === activeItem.sid)}
            isSelected={false}
            isDragging
            isDragOverlay
          />
        )}
      </DragOverlay>
    </DndContext>
  );
}
