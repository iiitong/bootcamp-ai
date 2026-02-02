// components/modals/StylePickerModal.tsx

import { useState, useCallback } from 'react';
import { useUIStore } from '@/stores/uiStore';
import { useProjectStore } from '@/stores/projectStore';
import * as imagesApi from '@/api/images';
import type { StyleCandidate } from '@/types';

const POLL_INTERVAL = 1000;
const POLL_TIMEOUT = 60000;

export function StylePickerModal() {
  const { isStyleModalOpen, closeStyleModal } = useUIStore();
  const { project, setStyle } = useProjectStore();

  const [step, setStep] = useState<'input' | 'generating' | 'select'>('input');
  const [prompt, setPrompt] = useState('');
  const [candidates, setCandidates] = useState<StyleCandidate[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleGenerate = useCallback(async () => {
    if (!prompt.trim() || !project) return;

    setStep('generating');
    setError(null);

    try {
      const { task_id } = await imagesApi.generateStyleCandidates(
        project.slug,
        prompt.trim()
      );

      // Poll for completion
      const startTime = Date.now();
      const poll = async () => {
        if (Date.now() - startTime > POLL_TIMEOUT) {
          setError('Generation timed out');
          setStep('input');
          return;
        }

        try {
          const status = await imagesApi.getStyleTaskStatus(task_id);

          if (status.status === 'completed' && status.result) {
            setCandidates(status.result.candidates);
            setSelectedCandidateId(status.result.candidates[0]?.id ?? null);
            setStep('select');
          } else if (status.status === 'failed') {
            setError(status.error ?? 'Generation failed');
            setStep('input');
          } else {
            setTimeout(poll, POLL_INTERVAL);
          }
        } catch (err) {
          console.error('Poll error:', err);
          setTimeout(poll, POLL_INTERVAL);
        }
      };

      poll();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start generation');
      setStep('input');
    }
  }, [prompt, project]);

  const handleSelect = useCallback(async () => {
    if (!selectedCandidateId || !project) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const result = await imagesApi.selectStyle(
        project.slug,
        selectedCandidateId,
        prompt.trim()
      );
      setStyle(result.style);
      closeStyleModal();
      resetState();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to select style');
    } finally {
      setIsSubmitting(false);
    }
  }, [selectedCandidateId, project, prompt, setStyle, closeStyleModal]);

  const handleClose = useCallback(() => {
    if (project?.style) {
      closeStyleModal();
      resetState();
    }
  }, [project?.style, closeStyleModal]);

  const resetState = () => {
    setStep('input');
    setPrompt('');
    setCandidates([]);
    setSelectedCandidateId(null);
    setError(null);
  };

  if (!isStyleModalOpen) return null;

  const canClose = !!project?.style;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="md-card max-w-2xl w-full mx-4 max-h-[90vh] overflow-auto !p-0">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b-2 border-[var(--md-graphite)]">
          <h3>{project?.style ? 'Change Style' : 'Choose a Style'}</h3>
          {canClose && (
            <button
              onClick={handleClose}
              className="text-[var(--md-slate)] hover:text-[var(--md-ink)]"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          )}
        </div>

        {/* Content */}
        <div className="p-4">
          {error && (
            <div className="mb-4 p-3 bg-[var(--md-watermelon)]/10 border-2 border-[var(--md-watermelon)] text-[var(--md-watermelon)] text-sm">
              {error}
            </div>
          )}

          {step === 'input' && (
            <div className="space-y-4">
              <div>
                <label className="block text-[var(--md-ink)] text-sm mb-2 uppercase tracking-wider font-bold">
                  Describe the visual style for your slides
                </label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="e.g., Cyberpunk style with neon lights and futuristic cityscape"
                  rows={3}
                  className="md-input resize-none"
                />
              </div>

              {project?.style && (
                <div className="p-3 bg-[var(--md-fog)] border-2 border-[var(--md-graphite)]">
                  <p className="text-[var(--md-slate)] text-xs uppercase tracking-wider mb-2">Current style:</p>
                  <div className="flex items-center gap-3">
                    <img
                      src={project.style.image}
                      alt="Current style"
                      className="w-16 h-10 object-cover border-2 border-[var(--md-graphite)]"
                    />
                    <p className="text-[var(--md-ink)] text-sm flex-1">
                      {project.style.prompt}
                    </p>
                  </div>
                </div>
              )}

              <button
                onClick={handleGenerate}
                disabled={!prompt.trim()}
                className="md-btn w-full"
              >
                Generate Style Options
              </button>
            </div>
          )}

          {step === 'generating' && (
            <div className="py-12 text-center">
              <div className="w-12 h-12 border-4 border-[var(--md-sky)] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-[var(--md-ink)]">Generating style options...</p>
              <p className="text-[var(--md-slate)] text-sm mt-1">
                This may take a few seconds
              </p>
            </div>
          )}

          {step === 'select' && (
            <div className="space-y-4">
              <p className="text-[var(--md-ink)] text-sm">
                Choose the style that best fits your vision:
              </p>

              <div className="grid grid-cols-2 gap-4">
                {candidates.map((candidate) => (
                  <button
                    key={candidate.id}
                    onClick={() => setSelectedCandidateId(candidate.id)}
                    className={`
                      relative overflow-hidden transition-all border-2
                      ${
                        selectedCandidateId === candidate.id
                          ? 'border-[var(--md-sky-strong)]'
                          : 'border-[var(--md-graphite)] hover:border-[var(--md-sky)]'
                      }
                    `}
                  >
                    <img
                      src={candidate.url}
                      alt={`Style option ${candidate.id}`}
                      className="w-full aspect-video object-cover"
                    />
                    {selectedCandidateId === candidate.id && (
                      <div className="absolute top-2 right-2 w-6 h-6 bg-[var(--md-sky)] border-2 border-[var(--md-graphite)] rounded-full flex items-center justify-center">
                        <svg
                          className="w-4 h-4 text-[var(--md-ink)]"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M5 13l4 4L19 7"
                          />
                        </svg>
                      </div>
                    )}
                  </button>
                ))}
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setStep('input')}
                  className="md-btn-secondary flex-1"
                >
                  Try Different Prompt
                </button>
                <button
                  onClick={handleSelect}
                  disabled={!selectedCandidateId || isSubmitting}
                  className="md-btn flex-1"
                >
                  {isSubmitting ? 'Saving...' : 'Use This Style'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
