import { apiClient } from './client';
import { Tag, CreateTagDto, TagListResponse } from '@/types/tag';

export const tagApi = {
  getAll: (includeCount = true) =>
    apiClient.get<TagListResponse>('/tags', {
      params: { include_count: includeCount },
    }),

  create: (data: CreateTagDto) =>
    apiClient.post<Tag>('/tags', data),

  delete: (id: number) =>
    apiClient.delete(`/tags/${id}`),
};
