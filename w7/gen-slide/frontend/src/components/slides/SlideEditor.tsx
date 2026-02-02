// components/slides/SlideEditor.tsx

import { useState, useEffect, useCallback, useRef } from 'react';
import type { Slide } from '@/types';

interface SlideEditorProps {
  slide: Slide;
  isEditing: boolean;
  onStartEdit: () => void;
  onStopEdit: () => void;
  onSave: (content: string) => Promise<void>;
  onDelete: () => Promise<void>;
}

export function SlideEditor({
  slide,
  isEditing,
  onStartEdit,
  onStopEdit,
  onSave,
  onDelete,
}: SlideEditorProps) {
  const [content, setContent] = useState(slide.content);
  const [isSaving, setIsSaving] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Sync content when slide changes
  useEffect(() => {
    setContent(slide.content);
  }, [slide.content]);

  // Focus textarea when editing starts
  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.select();
    }
  }, [isEditing]);

  const handleSave = useCallback(async () => {
    if (content.trim() === slide.content) {
      onStopEdit();
      return;
    }

    if (!content.trim()) {
      setContent(slide.content);
      onStopEdit();
      return;
    }

    setIsSaving(true);
    try {
      await onSave(content.trim());
      onStopEdit();
    } catch (error) {
      console.error('Failed to save:', error);
    } finally {
      setIsSaving(false);
    }
  }, [content, slide.content, onSave, onStopEdit]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSave();
      } else if (e.key === 'Escape') {
        setContent(slide.content);
        onStopEdit();
      }
    },
    [handleSave, slide.content, onStopEdit]
  );

  const handleDelete = useCallback(async () => {
    if (window.confirm('Are you sure you want to delete this slide?')) {
      await onDelete();
    }
  }, [onDelete]);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-[var(--md-slate)] text-xs uppercase tracking-wider font-bold">Content</label>
        <button
          onClick={handleDelete}
          className="text-[var(--md-watermelon)] hover:opacity-70 text-xs uppercase tracking-wider font-bold"
        >
          Delete
        </button>
      </div>

      {isEditing ? (
        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onBlur={handleSave}
          onKeyDown={handleKeyDown}
          disabled={isSaving}
          rows={3}
          className="md-input resize-none disabled:opacity-50"
          placeholder="Describe your slide content..."
        />
      ) : (
        <div
          onClick={onStartEdit}
          onDoubleClick={onStartEdit}
          className="w-full bg-[var(--md-fog)] text-[var(--md-ink)] px-4 py-3 border-2 border-[var(--md-graphite)] cursor-text min-h-[72px] hover:bg-[var(--md-cloud)] transition-colors"
        >
          {slide.content || (
            <span className="text-[var(--md-slate)] italic">Click to add content...</span>
          )}
        </div>
      )}

      <div className="flex items-center gap-2 text-xs text-[var(--md-slate)]">
        <span>Hash: {slide.currentHash}</span>
        {slide.hasMatchingImage && (
          <span className="text-[var(--md-sky-strong)]">Image matches</span>
        )}
      </div>
    </div>
  );
}
