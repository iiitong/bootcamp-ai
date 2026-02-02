// hooks/useSlides.ts

import { useCallback } from 'react';
import { useProjectStore } from '@/stores/projectStore';
import { useSlideStore } from '@/stores/slideStore';

export function useSlides() {
  const { project } = useProjectStore();
  const {
    selectedSid,
    selectedImageHash,
    editingSid,
    generatingTasks,
    selectSlide,
    selectImage,
    startEditing,
    stopEditing,
    createSlide,
    updateSlide,
    deleteSlide,
    reorderSlides,
    generateImage,
  } = useSlideStore();

  const slug = project?.slug ?? '';
  const slides = project?.slides ?? [];

  const currentSlide = slides.find((s) => s.sid === selectedSid) ?? null;

  const handleCreateSlide = useCallback(
    async (content: string, afterSid?: string) => {
      if (!slug) return;
      await createSlide(slug, content, afterSid);
    },
    [slug, createSlide]
  );

  const handleUpdateSlide = useCallback(
    async (sid: string, content: string) => {
      if (!slug) return;
      await updateSlide(slug, sid, content);
    },
    [slug, updateSlide]
  );

  const handleDeleteSlide = useCallback(
    async (sid: string) => {
      if (!slug) return;
      await deleteSlide(slug, sid);
    },
    [slug, deleteSlide]
  );

  const handleReorderSlides = useCallback(
    async (order: string[]) => {
      if (!slug) return;
      await reorderSlides(slug, order);
    },
    [slug, reorderSlides]
  );

  const handleGenerateImage = useCallback(
    async (sid: string) => {
      if (!slug) return;
      await generateImage(slug, sid);
    },
    [slug, generateImage]
  );

  const isGenerating = useCallback(
    (sid: string) => {
      const task = generatingTasks.get(sid);
      return task?.status === 'pending' || task?.status === 'processing';
    },
    [generatingTasks]
  );

  const getGeneratingError = useCallback(
    (sid: string) => {
      const task = generatingTasks.get(sid);
      return task?.status === 'failed' ? task.error : null;
    },
    [generatingTasks]
  );

  return {
    slides,
    currentSlide,
    selectedSid,
    selectedImageHash,
    editingSid,
    selectSlide,
    selectImage,
    startEditing,
    stopEditing,
    createSlide: handleCreateSlide,
    updateSlide: handleUpdateSlide,
    deleteSlide: handleDeleteSlide,
    reorderSlides: handleReorderSlides,
    generateImage: handleGenerateImage,
    isGenerating,
    getGeneratingError,
  };
}
