import { Tag } from '@/types/tag';
import { getColorForTag } from '@/lib/colors';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';

interface TagBadgeProps {
  tag: Tag;
  onRemove?: () => void;
  clickable?: boolean;
  onClick?: () => void;
  className?: string;
}

export function TagBadge({ tag, onRemove, clickable, onClick, className }: TagBadgeProps) {
  const colorClass = getColorForTag(tag.name);

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium',
        colorClass,
        clickable && 'cursor-pointer hover:opacity-80',
        className
      )}
      onClick={onClick}
    >
      {tag.name}
      {tag.ticket_count !== undefined && tag.ticket_count !== null && ` (${tag.ticket_count})`}
      {onRemove && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="ml-0.5 hover:bg-black/10 rounded-full p-0.5"
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </span>
  );
}
