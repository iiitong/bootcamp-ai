// stores/slideStore.ts

import { create } from 'zustand';
import type { GenerateTask, Slide } from '@/types';
import { transformSlideResponse, transformTaskResponse } from '@/types';
import * as slidesApi from '@/api/slides';
import * as imagesApi from '@/api/images';
import { useProjectStore } from './projectStore';

const TASK_POLL_INTERVAL = 1000; // ms
const TASK_TIMEOUT = 60000; // ms

interface SlideState {
  selectedSid: string | null;
  selectedImageHash: string | null;
  editingSid: string | null;
  generatingTasks: Map<string, GenerateTask>;

  // Actions
  selectSlide: (sid: string) => void;
  selectImage: (hash: string) => void;
  startEditing: (sid: string) => void;
  stopEditing: () => void;
  createSlide: (slug: string, content: string, afterSid?: string) => Promise<void>;
  updateSlide: (slug: string, sid: string, content: string) => Promise<void>;
  deleteSlide: (slug: string, sid: string) => Promise<void>;
  reorderSlides: (slug: string, order: string[]) => Promise<void>;
  generateImage: (slug: string, sid: string) => Promise<void>;
  clearSelection: () => void;
}

export const useSlideStore = create<SlideState>((set, get) => ({
  selectedSid: null,
  selectedImageHash: null,
  editingSid: null,
  generatingTasks: new Map(),

  selectSlide: (sid: string) => {
    const { project } = useProjectStore.getState();
    const slide = project?.slides.find((s) => s.sid === sid);

    // Find the matching image hash or use the latest image
    let imageHash: string | null = null;
    if (slide && slide.images.length > 0) {
      if (slide.hasMatchingImage) {
        // Find the image that matches currentHash
        const matchingImage = slide.images.find((img) => img.hash === slide.currentHash);
        imageHash = matchingImage?.hash ?? slide.images[0].hash;
      } else {
        // Use the most recent image (first in array, sorted by created_at desc)
        imageHash = slide.images[0].hash;
      }
    }

    set({
      selectedSid: sid,
      selectedImageHash: imageHash,
    });
  },

  selectImage: (hash: string) => {
    set({ selectedImageHash: hash });
  },

  startEditing: (sid: string) => {
    set({ editingSid: sid });
  },

  stopEditing: () => {
    set({ editingSid: null });
  },

  createSlide: async (slug: string, content: string, afterSid?: string) => {
    try {
      const response = await slidesApi.createSlide(slug, content, afterSid);
      const newSlide = transformSlideResponse(response);

      useProjectStore.getState().updateSlides((slides) => {
        if (afterSid) {
          const index = slides.findIndex((s) => s.sid === afterSid);
          const newSlides = [...slides];
          newSlides.splice(index + 1, 0, newSlide);
          return newSlides;
        }
        return [...slides, newSlide];
      });

      set({ selectedSid: newSlide.sid });
    } catch (error) {
      console.error('Failed to create slide:', error);
      throw error;
    }
  },

  updateSlide: async (slug: string, sid: string, content: string) => {
    try {
      const response = await slidesApi.updateSlide(slug, sid, content);
      const updatedSlide = transformSlideResponse(response);

      useProjectStore.getState().updateSlides((slides) =>
        slides.map((s) => (s.sid === sid ? updatedSlide : s))
      );

      // Update selected image hash based on matching status
      if (get().selectedSid === sid) {
        let imageHash: string | null = null;
        if (updatedSlide.images.length > 0) {
          if (updatedSlide.hasMatchingImage) {
            const matchingImage = updatedSlide.images.find(
              (img) => img.hash === updatedSlide.currentHash
            );
            imageHash = matchingImage?.hash ?? updatedSlide.images[0].hash;
          } else {
            imageHash = updatedSlide.images[0].hash;
          }
        }
        set({ selectedImageHash: imageHash });
      }
    } catch (error) {
      console.error('Failed to update slide:', error);
      throw error;
    }
  },

  deleteSlide: async (slug: string, sid: string) => {
    try {
      await slidesApi.deleteSlide(slug, sid);

      const { project } = useProjectStore.getState();
      const currentIndex = project?.slides.findIndex((s) => s.sid === sid) ?? -1;

      useProjectStore.getState().updateSlides((slides) =>
        slides.filter((s) => s.sid !== sid)
      );

      // Select next or previous slide
      const remainingSlides = project?.slides.filter((s) => s.sid !== sid) ?? [];
      if (remainingSlides.length > 0) {
        const newIndex = Math.min(currentIndex, remainingSlides.length - 1);
        set({ selectedSid: remainingSlides[newIndex].sid });
      } else {
        set({ selectedSid: null, selectedImageHash: null });
      }
    } catch (error) {
      console.error('Failed to delete slide:', error);
      throw error;
    }
  },

  reorderSlides: async (slug: string, order: string[]) => {
    try {
      await slidesApi.reorderSlides(slug, order);

      useProjectStore.getState().updateSlides((slides) => {
        const slideMap = new Map(slides.map((s) => [s.sid, s]));
        return order.map((sid) => slideMap.get(sid)!).filter(Boolean);
      });
    } catch (error) {
      console.error('Failed to reorder slides:', error);
      throw error;
    }
  },

  generateImage: async (slug: string, sid: string) => {
    const { generatingTasks } = get();

    // Check if already generating for this slide
    const existingTask = generatingTasks.get(sid);
    if (existingTask && ['pending', 'processing'].includes(existingTask.status)) {
      return;
    }

    try {
      const { task_id } = await imagesApi.generateSlideImage(slug, sid);

      // Add task to map
      const newTasks = new Map(generatingTasks);
      newTasks.set(sid, {
        taskId: task_id,
        status: 'pending',
      });
      set({ generatingTasks: newTasks });

      // Start polling
      const startTime = Date.now();
      const poll = async () => {
        if (Date.now() - startTime > TASK_TIMEOUT) {
          const tasks = new Map(get().generatingTasks);
          tasks.set(sid, {
            taskId: task_id,
            status: 'failed',
            error: 'Task timeout',
          });
          set({ generatingTasks: tasks });
          return;
        }

        try {
          const response = await imagesApi.getTaskStatus(task_id);
          const task = transformTaskResponse(response);

          const tasks = new Map(get().generatingTasks);
          tasks.set(sid, task);
          set({ generatingTasks: tasks });

          if (task.status === 'completed' && task.result) {
            // Fetch fresh slide data from backend to ensure consistency
            try {
              const slideResponse = await slidesApi.getSlide(slug, sid);
              const freshSlide = transformSlideResponse(slideResponse);

              // Update the slide in the store with fresh data
              useProjectStore.getState().updateSlides((slides) =>
                slides.map((s) => (s.sid === sid ? freshSlide : s))
              );

              // Update selected image to the newly generated one
              if (get().selectedSid === sid) {
                set({ selectedImageHash: task.result.hash });
              }

              // Update total cost
              if (task.result.cost) {
                const { project } = useProjectStore.getState();
                const currentCost = project?.totalCost ?? 0;
                useProjectStore.getState().updateTotalCost(currentCost + task.result.cost);
              }
            } catch (refreshError) {
              console.error('Failed to refresh slide data:', refreshError);
              // Fall back to optimistic update if refresh fails
              const { project } = useProjectStore.getState();
              const slide = project?.slides.find((s) => s.sid === sid);
              if (slide) {
                const newImage = {
                  hash: task.result.hash,
                  url: task.result.url,
                  createdAt: new Date().toISOString(),
                };

                useProjectStore.getState().updateSlides((slides) =>
                  slides.map((s) => {
                    if (s.sid !== sid) return s;

                    // Check if image with this hash already exists
                    const existingIndex = s.images.findIndex(
                      (img) => img.hash === newImage.hash
                    );

                    let updatedImages: typeof s.images;
                    if (existingIndex >= 0) {
                      updatedImages = [...s.images];
                      updatedImages[existingIndex] = newImage;
                    } else {
                      updatedImages = [newImage, ...s.images];
                    }

                    return {
                      ...s,
                      images: updatedImages,
                      hasMatchingImage: task.result!.hash === s.currentHash,
                    };
                  })
                );

                if (get().selectedSid === sid) {
                  set({ selectedImageHash: task.result.hash });
                }
              }
            }
          } else if (task.status === 'pending' || task.status === 'processing') {
            setTimeout(poll, TASK_POLL_INTERVAL);
          }
        } catch (error) {
          console.error('Failed to poll task status:', error);
          setTimeout(poll, TASK_POLL_INTERVAL);
        }
      };

      poll();
    } catch (error) {
      console.error('Failed to start image generation:', error);
      throw error;
    }
  },

  clearSelection: () => {
    set({ selectedSid: null, selectedImageHash: null, editingSid: null });
  },
}));

// Helper function to get current slide
export function useCurrentSlide(): Slide | null {
  const { selectedSid } = useSlideStore();
  const { project } = useProjectStore();
  return project?.slides.find((s) => s.sid === selectedSid) ?? null;
}
