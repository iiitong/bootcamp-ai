import { apiClient } from './client';
import {
  Ticket,
  CreateTicketDto,
  UpdateTicketDto,
  UpdateTicketStatusDto,
  AddTagToTicketDto,
  PaginatedResponse,
  GetTicketsParams,
} from '@/types/ticket';

export const ticketApi = {
  getAll: (params?: GetTicketsParams) =>
    apiClient.get<PaginatedResponse<Ticket>>('/tickets', { params }),

  getById: (id: number) =>
    apiClient.get<Ticket>(`/tickets/${id}`),

  create: (data: CreateTicketDto) =>
    apiClient.post<Ticket>('/tickets', data),

  update: (id: number, data: UpdateTicketDto) =>
    apiClient.put<Ticket>(`/tickets/${id}`, data),

  updateStatus: (id: number, data: UpdateTicketStatusDto) =>
    apiClient.patch<Ticket>(`/tickets/${id}/status`, data),

  delete: (id: number) =>
    apiClient.delete(`/tickets/${id}`),

  addTag: (ticketId: number, data: AddTagToTicketDto) =>
    apiClient.post<Ticket>(`/tickets/${ticketId}/tags`, data),

  removeTag: (ticketId: number, tagId: number) =>
    apiClient.delete<Ticket>(`/tickets/${ticketId}/tags/${tagId}`),
};
