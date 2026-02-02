// api/projects.ts

import { get, post, patch } from './client';
import type { ProjectResponse, CostBreakdown } from '@/types';

export async function getProject(slug: string): Promise<ProjectResponse> {
  return get<ProjectResponse>(`/projects/${slug}`);
}

export async function createProject(
  slug: string,
  title: string
): Promise<ProjectResponse> {
  return post<ProjectResponse>(`/projects/${slug}`, { title });
}

export async function updateProject(
  slug: string,
  title: string
): Promise<{ slug: string; title: string }> {
  return patch<{ slug: string; title: string }>(`/projects/${slug}`, { title });
}

export async function getProjectCost(slug: string): Promise<CostBreakdown> {
  return get<CostBreakdown>(`/projects/${slug}/cost`);
}
