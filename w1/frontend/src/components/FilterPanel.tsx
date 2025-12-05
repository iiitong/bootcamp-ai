import { Tag } from '@/types/tag';
import { TagBadge } from '@/components/TagBadge';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

interface FilterPanelProps {
  tags: Tag[];
  selectedStatus: 'all' | 'pending' | 'completed';
  selectedTagIds: number[];
  onStatusChange: (status: 'all' | 'pending' | 'completed') => void;
  onTagToggle: (tagId: number) => void;
  onResetFilters: () => void;
}

export function FilterPanel({
  tags,
  selectedStatus,
  selectedTagIds,
  onStatusChange,
  onTagToggle,
  onResetFilters,
}: FilterPanelProps) {
  const hasActiveFilters = selectedStatus !== 'all' || selectedTagIds.length > 0;

  return (
    <div className="space-y-6">
      {/* Status Filter */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">状态</h3>
        <div className="space-y-2">
          {(['all', 'pending', 'completed'] as const).map((status) => (
            <label key={status} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="status"
                checked={selectedStatus === status}
                onChange={() => onStatusChange(status)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-600"
              />
              <span className="text-sm text-gray-700">
                {status === 'all' && '全部'}
                {status === 'pending' && '待办'}
                {status === 'completed' && '已完成'}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Tag Filter */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">标签</h3>
        <div className="flex flex-wrap gap-2">
          {tags.map((tag) => (
            <TagBadge
              key={tag.id}
              tag={tag}
              clickable
              onClick={() => onTagToggle(tag.id)}
              className={cn(selectedTagIds.includes(tag.id) && 'ring-2 ring-blue-600')}
            />
          ))}
        </div>
      </div>

      {/* Reset Button */}
      {hasActiveFilters && (
        <Button
          variant="secondary"
          size="sm"
          onClick={onResetFilters}
          className="w-full"
        >
          重置筛选
        </Button>
      )}
    </div>
  );
}
