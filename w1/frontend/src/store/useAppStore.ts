import { create } from 'zustand';
import { Ticket } from '@/types/ticket';
import { Tag } from '@/types/tag';

interface FilterState {
  status: 'all' | 'pending' | 'completed';
  selectedTags: number[];
  tagFilterMode: 'and' | 'or';
  searchQuery: string;
  sortBy: 'created_at' | 'updated_at' | 'title';
  sortOrder: 'asc' | 'desc';
}

interface PaginationState {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

interface AppState {
  // Tickets
  tickets: Ticket[];
  ticketsLoading: boolean;
  ticketsError: string | null;

  // Tags
  tags: Tag[];
  tagsLoading: boolean;

  // Filters
  filters: FilterState;

  // Pagination
  pagination: PaginationState;

  // Actions
  setTickets: (tickets: Ticket[]) => void;
  setTicketsLoading: (loading: boolean) => void;
  setTicketsError: (error: string | null) => void;

  setTags: (tags: Tag[]) => void;
  setTagsLoading: (loading: boolean) => void;

  setFilter: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
  resetFilters: () => void;

  setPagination: (pagination: Partial<PaginationState>) => void;
}

const initialFilters: FilterState = {
  status: 'all',
  selectedTags: [],
  tagFilterMode: 'and',
  searchQuery: '',
  sortBy: 'created_at',
  sortOrder: 'desc',
};

const initialPagination: PaginationState = {
  page: 1,
  pageSize: 20,
  total: 0,
  totalPages: 0,
};

export const useAppStore = create<AppState>((set) => ({
  // Initial state
  tickets: [],
  ticketsLoading: false,
  ticketsError: null,

  tags: [],
  tagsLoading: false,

  filters: initialFilters,
  pagination: initialPagination,

  // Actions
  setTickets: (tickets) => set({ tickets }),
  setTicketsLoading: (loading) => set({ ticketsLoading: loading }),
  setTicketsError: (error) => set({ ticketsError: error }),

  setTags: (tags) => set({ tags }),
  setTagsLoading: (loading) => set({ tagsLoading: loading }),

  setFilter: (key, value) =>
    set((state) => ({
      filters: { ...state.filters, [key]: value },
    })),

  resetFilters: () => set({ filters: initialFilters }),

  setPagination: (pagination) =>
    set((state) => ({
      pagination: { ...state.pagination, ...pagination },
    })),
}));
