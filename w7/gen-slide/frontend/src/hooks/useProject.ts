// hooks/useProject.ts

import { useEffect } from 'react';
import { useProjectStore } from '@/stores/projectStore';
import { useUIStore } from '@/stores/uiStore';

export function useProject(slug: string) {
  const { project, isLoading, error, loadProject } = useProjectStore();
  const { openStyleModal } = useUIStore();

  useEffect(() => {
    loadProject(slug);
  }, [slug, loadProject]);

  // Open style modal if project has no style
  useEffect(() => {
    if (project && !project.style && !isLoading) {
      openStyleModal();
    }
  }, [project, isLoading, openStyleModal]);

  return {
    project,
    isLoading,
    error,
    reload: () => loadProject(slug),
  };
}
