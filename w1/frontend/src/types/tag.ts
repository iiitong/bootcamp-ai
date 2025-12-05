export interface Tag {
  id: number;
  name: string;
  created_at?: string;
  ticket_count?: number;
}

export interface CreateTagDto {
  name: string;
}

export interface TagListResponse {
  data: Tag[];
  total: number;
}
