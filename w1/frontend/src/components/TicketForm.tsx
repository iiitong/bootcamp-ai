import { useState, FormEvent, KeyboardEvent } from 'react';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Tag } from '@/types/tag';
import { TagBadge } from '@/components/TagBadge';
import { cn } from '@/lib/utils';
import { tagApi } from '@/api/tags';
import { Plus } from 'lucide-react';

interface TicketFormProps {
  tags: Tag[];
  onSubmit: (data: { title: string; description: string; tag_ids: number[] }) => void;
  onCancel: () => void;
  onTagCreated?: () => void;
}

export function TicketForm({ tags, onSubmit, onCancel, onTagCreated }: TicketFormProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
  const [newTagName, setNewTagName] = useState('');
  const [isCreatingTag, setIsCreatingTag] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    onSubmit({
      title: title.trim(),
      description: description.trim(),
      tag_ids: selectedTagIds,
    });

    // Reset form
    setTitle('');
    setDescription('');
    setSelectedTagIds([]);
  };

  const toggleTag = (tagId: number) => {
    setSelectedTagIds((prev) =>
      prev.includes(tagId)
        ? prev.filter((id) => id !== tagId)
        : [...prev, tagId]
    );
  };

  const handleCreateTag = async () => {
    const trimmedName = newTagName.trim();
    if (!trimmedName) return;

    // Check if tag already exists
    if (tags.some(tag => tag.name.toLowerCase() === trimmedName.toLowerCase())) {
      alert('该标签已存在');
      return;
    }

    setIsCreatingTag(true);
    try {
      const response = await tagApi.create({ name: trimmedName });
      const newTag = response.data;

      // Auto-select the newly created tag
      setSelectedTagIds((prev) => [...prev, newTag.id]);
      setNewTagName('');

      // Notify parent to reload tags
      onTagCreated?.();
    } catch (error) {
      console.error('Failed to create tag:', error);
      alert('创建标签失败');
    } finally {
      setIsCreatingTag(false);
    }
  };

  const handleTagInputKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleCreateTag();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">
          标题 *
        </label>
        <Input
          id="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="输入 Ticket 标题"
          maxLength={200}
          required
        />
      </div>

      <div>
        <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
          描述
        </label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="输入 Ticket 描述（可选）"
          className="flex min-h-[100px] w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
          rows={4}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          标签（可选）
        </label>

        {/* New tag input */}
        <div className="flex gap-2 mb-3">
          <Input
            value={newTagName}
            onChange={(e) => setNewTagName(e.target.value)}
            onKeyDown={handleTagInputKeyDown}
            placeholder="输入新标签名称..."
            className="flex-1"
            maxLength={50}
          />
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={handleCreateTag}
            disabled={!newTagName.trim() || isCreatingTag}
          >
            <Plus className="h-4 w-4 mr-1" />
            {isCreatingTag ? '创建中...' : '添加'}
          </Button>
        </div>

        {/* Existing tags */}
        <div className="flex flex-wrap gap-2">
          {tags.map((tag) => (
            <TagBadge
              key={tag.id}
              tag={tag}
              clickable
              onClick={() => toggleTag(tag.id)}
              className={cn(selectedTagIds.includes(tag.id) && 'ring-2 ring-blue-600')}
            />
          ))}
        </div>
      </div>

      <div className="flex justify-end gap-2 pt-4">
        <Button type="button" variant="secondary" onClick={onCancel}>
          取消
        </Button>
        <Button type="submit" variant="primary">
          创建
        </Button>
      </div>
    </form>
  );
}
