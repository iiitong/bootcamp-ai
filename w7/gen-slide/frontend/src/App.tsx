// App.tsx

import { Header } from '@/components/layout/Header';
import { Sidebar } from '@/components/layout/Sidebar';
import { MainArea } from '@/components/layout/MainArea';
import { FullscreenPlayer } from '@/components/player/FullscreenPlayer';
import { StylePickerModal } from '@/components/modals/StylePickerModal';
import { useProject } from '@/hooks/useProject';

// Get slug from URL path (e.g., /project/my-slides -> my-slides)
function getSlugFromUrl(): string {
  const path = window.location.pathname;
  const match = path.match(/^\/project\/([^/]+)/);
  if (match) {
    return match[1];
  }
  // Default slug if no path
  return 'demo';
}

function App() {
  const slug = getSlugFromUrl();
  const { project, isLoading, error } = useProject(slug);

  if (isLoading) {
    return (
      <div className="md-shell flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-[var(--md-sky)] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-[var(--md-slate)]">Loading project...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="md-shell flex items-center justify-center">
        <div className="text-center">
          <svg
            className="w-16 h-16 text-[var(--md-watermelon)] mx-auto mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="text-[var(--md-watermelon)] text-lg">Failed to load project</p>
          <p className="text-[var(--md-slate)] mt-2">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="md-btn mt-4"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!project) {
    return null;
  }

  return (
    <div className="md-shell flex flex-col">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <MainArea />
      </div>
      <FullscreenPlayer />
      <StylePickerModal />
    </div>
  );
}

export default App;
