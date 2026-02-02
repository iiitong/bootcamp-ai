// hooks/useDragAndDrop.ts

import { useState, useCallback } from 'react';
import {
  DragEndEvent,
  DragStartEvent,
  UniqueIdentifier,
} from '@dnd-kit/core';
import { arrayMove } from '@dnd-kit/sortable';

interface UseDragAndDropOptions<T> {
  items: T[];
  getId: (item: T) => string;
  onReorder: (newOrder: string[]) => Promise<void>;
}

export function useDragAndDrop<T>({
  items,
  getId,
  onReorder,
}: UseDragAndDropOptions<T>) {
  const [activeId, setActiveId] = useState<UniqueIdentifier | null>(null);
  const [isReordering, setIsReordering] = useState(false);

  const itemIds = items.map(getId);

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id);
  }, []);

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      const { active, over } = event;
      setActiveId(null);

      if (!over || active.id === over.id) {
        return;
      }

      const oldIndex = itemIds.indexOf(active.id as string);
      const newIndex = itemIds.indexOf(over.id as string);

      if (oldIndex === -1 || newIndex === -1) {
        return;
      }

      const newOrder = arrayMove(itemIds, oldIndex, newIndex);

      setIsReordering(true);
      try {
        await onReorder(newOrder);
      } catch (error) {
        console.error('Failed to reorder:', error);
      } finally {
        setIsReordering(false);
      }
    },
    [itemIds, onReorder]
  );

  const handleDragCancel = useCallback(() => {
    setActiveId(null);
  }, []);

  const activeItem = activeId
    ? items.find((item) => getId(item) === activeId)
    : null;

  return {
    activeId,
    activeItem,
    isReordering,
    itemIds,
    handleDragStart,
    handleDragEnd,
    handleDragCancel,
  };
}
