import { useEffect, useState } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { useDebounce } from '@/hooks/useDebounce';
import { ticketApi } from '@/api/tickets';
import { tagApi } from '@/api/tags';
import { TicketCard } from '@/components/TicketCard';
import { TicketForm } from '@/components/TicketForm';
import { SearchBar } from '@/components/SearchBar';
import { FilterPanel } from '@/components/FilterPanel';
import { Button } from '@/components/ui/Button';
import { Plus } from 'lucide-react';

function App() {
  const [showForm, setShowForm] = useState(false);

  const {
    tickets,
    ticketsLoading,
    tags,
    filters,
    pagination,
    setTickets,
    setTicketsLoading,
    setTags,
    setFilter,
    resetFilters,
    setPagination,
  } = useAppStore();

  // Debounce search query for better performance
  const debouncedSearchQuery = useDebounce(filters.searchQuery, 300);

  // Load tags on mount
  useEffect(() => {
    loadTags();
  }, []);

  // Load tickets when filters change
  useEffect(() => {
    loadTickets();
  }, [
    debouncedSearchQuery,
    filters.status,
    filters.selectedTags,
    filters.tagFilterMode,
    filters.sortBy,
    filters.sortOrder,
    pagination.page,
  ]);

  const loadTags = async () => {
    try {
      const response = await tagApi.getAll(true);
      setTags(response.data.data);
    } catch (error) {
      console.error('Failed to load tags:', error);
    }
  };

  const loadTickets = async () => {
    setTicketsLoading(true);
    try {
      const response = await ticketApi.getAll({
        status: filters.status,
        tags: filters.selectedTags.length > 0 ? filters.selectedTags.join(',') : undefined,
        tag_filter_mode: filters.tagFilterMode,
        search: debouncedSearchQuery || undefined,
        sort_by: filters.sortBy,
        sort_order: filters.sortOrder,
        page: pagination.page,
        page_size: pagination.pageSize,
      });

      setTickets(response.data.data);
      setPagination({
        total: response.data.total,
        totalPages: response.data.total_pages,
      });
    } catch (error) {
      console.error('Failed to load tickets:', error);
    } finally {
      setTicketsLoading(false);
    }
  };

  const handleCreateTicket = async (data: any) => {
    try {
      await ticketApi.create(data);
      setShowForm(false);
      loadTickets();
      loadTags(); // Reload tags to update counts
    } catch (error) {
      console.error('Failed to create ticket:', error);
    }
  };

  const handleToggleStatus = async (id: number) => {
    const ticket = tickets.find((t) => t.id === id);
    if (!ticket) return;

    try {
      await ticketApi.updateStatus(id, {
        status: ticket.status === 'pending' ? 'completed' : 'pending',
      });
      loadTickets();
    } catch (error) {
      console.error('Failed to update ticket status:', error);
    }
  };

  const handleDeleteTicket = async (id: number) => {
    if (!window.confirm('确定要删除这个 Ticket 吗？')) return;

    try {
      await ticketApi.delete(id);
      loadTickets();
      loadTags();
    } catch (error) {
      console.error('Failed to delete ticket:', error);
    }
  };

  const handleRemoveTag = async (ticketId: number, tagId: number) => {
    try {
      await ticketApi.removeTag(ticketId, tagId);
      loadTickets();
      loadTags();
    } catch (error) {
      console.error('Failed to remove tag:', error);
    }
  };

  const handleAddTag = async (ticketId: number, tagId: number) => {
    try {
      await ticketApi.addTag(ticketId, { tag_id: tagId });
      loadTickets();
      loadTags();
    } catch (error) {
      console.error('Failed to add tag:', error);
    }
  };

  const handleTagToggle = (tagId: number) => {
    const newSelectedTags = filters.selectedTags.includes(tagId)
      ? filters.selectedTags.filter((id) => id !== tagId)
      : [...filters.selectedTags, tagId];
    setFilter('selectedTags', newSelectedTags);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">Project Alpha</h1>
            <div className="flex items-center gap-4">
              <SearchBar
                value={filters.searchQuery}
                onChange={(value) => setFilter('searchQuery', value)}
              />
              <Button onClick={() => setShowForm(true)}>
                <Plus className="h-4 w-4 mr-2" />
                新建
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Sidebar */}
          <aside className="lg:col-span-1">
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <FilterPanel
                tags={tags}
                selectedStatus={filters.status}
                selectedTagIds={filters.selectedTags}
                onStatusChange={(status) => setFilter('status', status)}
                onTagToggle={handleTagToggle}
                onResetFilters={resetFilters}
              />
            </div>
          </aside>

          {/* Ticket List */}
          <main className="lg:col-span-3">
            {showForm && (
              <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
                <h2 className="text-lg font-semibold mb-4">新建 Ticket</h2>
                <TicketForm
                  tags={tags}
                  onSubmit={handleCreateTicket}
                  onCancel={() => setShowForm(false)}
                  onTagCreated={loadTags}
                />
              </div>
            )}

            {ticketsLoading ? (
              <div className="text-center py-12">
                <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
                <p className="mt-2 text-sm text-gray-500">加载中...</p>
              </div>
            ) : tickets.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-500">暂无 Tickets</p>
              </div>
            ) : (
              <div className="space-y-4">
                {tickets.map((ticket) => (
                  <TicketCard
                    key={ticket.id}
                    ticket={ticket}
                    availableTags={tags}
                    onToggleStatus={handleToggleStatus}
                    onDelete={handleDeleteTicket}
                    onRemoveTag={handleRemoveTag}
                    onAddTag={handleAddTag}
                  />
                ))}
              </div>
            )}

            {/* Pagination */}
            {pagination.totalPages > 1 && (
              <div className="mt-6 flex justify-center gap-2">
                <Button
                  variant="secondary"
                  disabled={pagination.page === 1}
                  onClick={() => setPagination({ page: pagination.page - 1 })}
                >
                  上一页
                </Button>
                <span className="px-4 py-2 text-sm text-gray-700">
                  第 {pagination.page} / {pagination.totalPages} 页
                </span>
                <Button
                  variant="secondary"
                  disabled={pagination.page === pagination.totalPages}
                  onClick={() => setPagination({ page: pagination.page + 1 })}
                >
                  下一页
                </Button>
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}

export default App;
