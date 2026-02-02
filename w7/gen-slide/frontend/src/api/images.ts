// api/images.ts

import { get, post } from './client';
import type { TaskResponse, StyleTaskResponse } from '@/types';

export async function generateSlideImage(
  slug: string,
  sid: string,
  content?: string
): Promise<{ task_id: string; status: string }> {
  return post<{ task_id: string; status: string }>(
    `/projects/${slug}/slides/${sid}/generate`,
    content ? { content } : undefined
  );
}

export async function getTaskStatus(taskId: string): Promise<TaskResponse> {
  return get<TaskResponse>(`/tasks/${taskId}`);
}

export async function generateStyleCandidates(
  slug: string,
  prompt: string
): Promise<{ task_id: string; status: string }> {
  return post<{ task_id: string; status: string }>(
    `/projects/${slug}/style/generate`,
    { prompt }
  );
}

export async function getStyleTaskStatus(
  taskId: string
): Promise<StyleTaskResponse> {
  return get<StyleTaskResponse>(`/tasks/style/${taskId}`);
}

export async function selectStyle(
  slug: string,
  candidateId: string,
  prompt: string
): Promise<{ style: { prompt: string; image: string } }> {
  return post<{ style: { prompt: string; image: string } }>(
    `/projects/${slug}/style/select`,
    { candidate_id: candidateId, prompt }
  );
}
