import { Tag } from './tag';

export type TicketStatus = 'pending' | 'completed';

export interface Ticket {
  id: number;
  title: string;
  description: string | null;
  status: TicketStatus;
  tags: Tag[];
  created_at: string;
  updated_at: string;
}

export interface CreateTicketDto {
  title: string;
  description?: string;
  tag_ids?: number[];
}

export interface UpdateTicketDto {
  title?: string;
  description?: string;
}

export interface UpdateTicketStatusDto {
  status: TicketStatus;
}

export interface AddTagToTicketDto {
  tag_id?: number;
  tag_name?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface GetTicketsParams {
  status?: 'all' | 'pending' | 'completed';
  tags?: string;  // 逗号分隔的 tag IDs
  tag_filter_mode?: 'and' | 'or';
  search?: string;
  sort_by?: 'created_at' | 'updated_at' | 'title';
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}
