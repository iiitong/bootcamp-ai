// api/slides.ts

import { get, post, patch, put, del } from './client';
import type { SlideResponse } from '@/types';

export async function getSlide(slug: string, sid: string): Promise<SlideResponse> {
  return get<SlideResponse>(`/projects/${slug}/slides/${sid}`);
}

export async function createSlide(
  slug: string,
  content: string,
  afterSid?: string
): Promise<SlideResponse> {
  return post<SlideResponse>(`/projects/${slug}/slides`, {
    content,
    after_sid: afterSid,
  });
}

export async function updateSlide(
  slug: string,
  sid: string,
  content: string
): Promise<SlideResponse> {
  return patch<SlideResponse>(`/projects/${slug}/slides/${sid}`, { content });
}

export async function deleteSlide(slug: string, sid: string): Promise<void> {
  return del<void>(`/projects/${slug}/slides/${sid}`);
}

export async function reorderSlides(
  slug: string,
  order: string[]
): Promise<{ order: string[] }> {
  return put<{ order: string[] }>(`/projects/${slug}/slides/order`, { order });
}
