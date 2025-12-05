import { useState, useRef, useEffect } from 'react';
import { Ticket } from '@/types/ticket';
import { Card, CardContent } from '@/components/ui/Card';
import { TagBadge } from '@/components/TagBadge';
import { formatDate } from '@/lib/date';
import { Checkbox } from '@/components/ui/Checkbox';
import { Trash2, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Tag } from '@/types/tag';

interface TicketCardProps {
  ticket: Ticket;
  availableTags: Tag[];
  onToggleStatus: (id: number) => void;
  onDelete: (id: number) => void;
  onRemoveTag: (ticketId: number, tagId: number) => void;
  onAddTag: (ticketId: number, tagId: number) => void;
}

export function TicketCard({
  ticket,
  availableTags,
  onToggleStatus,
  onDelete,
  onRemoveTag,
  onAddTag,
}: TicketCardProps) {
  const isCompleted = ticket.status === 'completed';
  const [showTagMenu, setShowTagMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Get tags that are not already added to this ticket
  const unaddedTags = availableTags.filter(
    (tag) => !ticket.tags.some((t) => t.id === tag.id)
  );

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowTagMenu(false);
      }
    };

    if (showTagMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showTagMenu]);

  return (
    <Card className={cn('transition-all', isCompleted && 'opacity-60')}>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {/* Checkbox */}
          <Checkbox
            checked={isCompleted}
            onCheckedChange={() => onToggleStatus(ticket.id)}
            className="mt-1"
          />

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Title */}
            <h3
              className={cn(
                'text-base font-medium mb-1',
                isCompleted && 'line-through text-gray-500'
              )}
            >
              {ticket.title}
            </h3>

            {/* Description */}
            {ticket.description && (
              <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                {ticket.description}
              </p>
            )}

            {/* Tags */}
            <div className="flex flex-wrap gap-1.5 mb-2 items-center">
              {ticket.tags.map((tag) => (
                <TagBadge
                  key={tag.id}
                  tag={tag}
                  onRemove={() => onRemoveTag(ticket.id, tag.id)}
                />
              ))}

              {/* Add Tag Button */}
              {unaddedTags.length > 0 && (
                <div className="relative" ref={menuRef}>
                  <button
                    type="button"
                    onClick={() => setShowTagMenu(!showTagMenu)}
                    className="inline-flex items-center justify-center h-6 w-6 rounded-full border-2 border-dashed border-gray-300 text-gray-400 hover:border-blue-500 hover:text-blue-500 transition-colors"
                    title="添加标签"
                  >
                    <Plus className="h-3.5 w-3.5" />
                  </button>

                  {/* Tag Dropdown Menu */}
                  {showTagMenu && (
                    <div className="absolute left-0 top-full mt-1 z-10 bg-white rounded-md shadow-lg border border-gray-200 py-1 min-w-[150px] max-h-[200px] overflow-y-auto">
                      {unaddedTags.map((tag) => (
                        <button
                          key={tag.id}
                          type="button"
                          onClick={() => {
                            onAddTag(ticket.id, tag.id);
                            setShowTagMenu(false);
                          }}
                          className="w-full px-3 py-1.5 text-left text-sm hover:bg-gray-100 transition-colors flex items-center gap-2"
                        >
                          <TagBadge tag={tag} />
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Meta */}
            <div className="flex items-center gap-3 text-xs text-gray-500">
              <span>创建: {formatDate(ticket.created_at)}</span>
              {ticket.updated_at !== ticket.created_at && (
                <span>更新: {formatDate(ticket.updated_at)}</span>
              )}
            </div>
          </div>

          {/* Delete Button */}
          <button
            onClick={() => onDelete(ticket.id)}
            className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
            title="删除"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </CardContent>
    </Card>
  );
}
