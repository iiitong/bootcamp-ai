// stores/projectStore.ts

import { create } from 'zustand';
import type { Project, StyleConfig } from '@/types';
import { transformProjectResponse } from '@/types';
import * as projectsApi from '@/api/projects';

interface ProjectState {
  project: Project | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  loadProject: (slug: string) => Promise<void>;
  updateTitle: (title: string) => Promise<void>;
  setStyle: (style: StyleConfig) => void;
  updateSlides: (updater: (slides: Project['slides']) => Project['slides']) => void;
  updateTotalCost: (cost: number) => void;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  project: null,
  isLoading: false,
  error: null,

  loadProject: async (slug: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await projectsApi.getProject(slug);
      const project = transformProjectResponse(response);
      set({ project, isLoading: false });
    } catch (error) {
      // If project doesn't exist (404), create it
      if (error instanceof Error && error.message.includes('404')) {
        try {
          const response = await projectsApi.createProject(slug, 'New Presentation');
          const project = transformProjectResponse(response);
          set({ project, isLoading: false });
        } catch (createError) {
          set({
            error: createError instanceof Error ? createError.message : 'Failed to create project',
            isLoading: false,
          });
        }
      } else {
        set({
          error: error instanceof Error ? error.message : 'Failed to load project',
          isLoading: false,
        });
      }
    }
  },

  updateTitle: async (title: string) => {
    const { project } = get();
    if (!project) return;

    try {
      await projectsApi.updateProject(project.slug, title);
      set({
        project: { ...project, title },
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update title',
      });
    }
  },

  setStyle: (style: StyleConfig) => {
    const { project } = get();
    if (!project) return;

    set({
      project: { ...project, style },
    });
  },

  updateSlides: (updater) => {
    const { project } = get();
    if (!project) return;

    set({
      project: { ...project, slides: updater(project.slides) },
    });
  },

  updateTotalCost: (cost: number) => {
    const { project } = get();
    if (!project) return;

    set({
      project: { ...project, totalCost: cost },
    });
  },
}));
