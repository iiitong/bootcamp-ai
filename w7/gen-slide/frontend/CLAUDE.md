# GenSlides Frontend Development Guidelines

IMPORTANT: Always use latest dependencies.follow design tokens and global.css in ./src/styles/design-tokens.css and ./src/styles/global.css

## Tech Stack

- **Language**: TypeScript 5.7+
- **Framework**: React 19
- **State Management**: Zustand 5
- **Styling**: Tailwind CSS 4
- **Build Tool**: Vite 6
- **Package Manager**: pnpm
- **Drag & Drop**: @dnd-kit

## Best Practices

### React Best Practices

- Use functional components with hooks, not class components
- Follow Rules of Hooks: only call at top level, only in React functions
- Use `useMemo` for expensive computations, `useCallback` for stable references
- Avoid inline object/array literals in JSX props (causes re-renders)
- Use `key` prop correctly: stable, unique identifiers, not array indices
- Lift state up only when necessary, prefer local state
- Use React.lazy() and Suspense for code splitting
- Prefer controlled components over uncontrolled for forms

### TypeScript Best Practices

- Enable `strict` mode in tsconfig.json
- Use `interface` for object shapes, `type` for unions/intersections
- Avoid `any`, use `unknown` for truly unknown types
- Use type guards for runtime type checking
- Prefer `as const` for literal types
- Use discriminated unions for state machines
- Export types alongside their implementations
- Use `satisfies` operator for type checking without widening

### Zustand Best Practices

- Keep stores small and focused (one per domain)
- Use selectors to minimize re-renders: `useStore(state => state.field)`
- Avoid storing derived state, compute it in selectors
- Use `immer` middleware for complex nested updates
- Split actions from state for better organization
- Use `subscribeWithSelector` for side effects outside React

### Performance Best Practices

- Debounce/throttle expensive operations (search, resize)
- Use `React.memo()` for pure components with stable props
- Virtualize long lists with `react-window` or similar
- Lazy load images and heavy components
- Avoid layout thrashing: batch DOM reads/writes
- Profile with React DevTools before optimizing

## Architecture Principles

### SOLID Principles

- **Single Responsibility**: Each component does one thing well
  - `api/` - HTTP communication only
  - `stores/` - State management only
  - `components/` - UI rendering only
  - `hooks/` - Reusable logic only
- **Open/Closed**: Extend components via composition, not modification
- **Liskov Substitution**: Components accept consistent prop interfaces
- **Interface Segregation**: Small, focused TypeScript interfaces
- **Dependency Inversion**: Components depend on stores, not API directly

### YAGNI (You Aren't Gonna Need It)

- Build only features specified in the design doc
- No premature optimization
- Add complexity when actually needed

### KISS (Keep It Simple, Stupid)

- Prefer functional components over class components
- Use built-in React features before external libraries
- Avoid over-engineering state management

### DRY (Don't Repeat Yourself)

- Extract common UI patterns into reusable components
- Share types via `types/index.ts`
- Centralize API calls in `api/` directory

## Project Structure

```
frontend/
├── src/
│   ├── main.tsx              # App entry point
│   ├── App.tsx               # Root component
│   │
│   ├── api/                  # API Layer
│   │   ├── client.ts         # HTTP client (fetch wrapper)
│   │   ├── projects.ts       # Project API calls
│   │   ├── slides.ts         # Slide API calls
│   │   └── images.ts         # Image API calls
│   │
│   ├── stores/               # State Layer
│   │   ├── projectStore.ts   # Project state
│   │   ├── slideStore.ts     # Slide state
│   │   └── uiStore.ts        # UI state
│   │
│   ├── components/           # UI Layer
│   │   ├── layout/           # Layout components
│   │   ├── slides/           # Slide components
│   │   ├── images/           # Image components
│   │   ├── player/           # Playback components
│   │   └── modals/           # Modal components
│   │
│   ├── hooks/                # Custom Hooks
│   │   ├── useProject.ts
│   │   ├── useSlides.ts
│   │   └── useDragAndDrop.ts
│   │
│   └── types/                # TypeScript Types
│       └── index.ts
│
└── public/
```

## Data Flow

```
User Action → Component → Store Action → API Call → Store Update → Re-render
```

- Components dispatch actions to stores
- Stores call API and update state
- React re-renders on state changes

## Commands

```bash
# Install dependencies
pnpm install

# Run development server
pnpm dev

# Build for production
pnpm build

# Type checking
pnpm typecheck

# Lint
pnpm lint
```

## Code Style

### Naming Conventions

```typescript
// Components: PascalCase
const SlideCard: React.FC<Props> = () => { ... }
// File: SlideCard.tsx

// Hooks: camelCase with 'use' prefix
const useSlides = () => { ... }
// File: useSlides.ts

// Stores: camelCase with 'Store' suffix
export const useSlideStore = create<SlideState>(() => ({ ... }))
// File: slideStore.ts

// Types/Interfaces: PascalCase
interface Slide { ... }
type SlideStatus = 'pending' | 'completed';

// Constants: UPPER_SNAKE_CASE
const MAX_SLIDES = 100;
const API_BASE_URL = '/api';

// Event handlers: handle + Event
const handleClick = () => { ... }
const handleSubmit = (e: FormEvent) => { ... }

// Boolean variables: is/has/should prefix
const isLoading = true;
const hasError = false;
const shouldAutoPlay = true;
```

### Import Order

```typescript
// 1. React and framework imports
import { useState, useEffect, useCallback } from 'react';

// 2. Third-party libraries
import { create } from 'zustand';
import { useSortable } from '@dnd-kit/sortable';

// 3. Local components
import { SlideCard } from '../components/slides/SlideCard';
import { Header } from '../components/layout/Header';

// 4. Hooks and stores
import { useSlideStore } from '../stores/slideStore';
import { useProject } from '../hooks/useProject';

// 5. Types
import type { Slide, Project } from '../types';

// 6. Styles and assets
import './styles.css';
```

### TypeScript

Always use strict typing:

```typescript
// Interface for props
interface SlideProps {
  slide: Slide;
  onSelect: (sid: string) => void;
  isSelected: boolean;
}

// Explicit return types for functions
const formatDate = (date: Date): string => {
  return date.toISOString();
};

// Use 'type' for unions and intersections
type SlideStatus = 'pending' | 'processing' | 'completed' | 'failed';
type ExtendedSlide = Slide & { metadata: Record<string, unknown> };

// Avoid 'any', use 'unknown' when needed
const parseResponse = (data: unknown): Slide => {
  // validate and cast
};
```

### Component Structure

```typescript
// 1. Imports (ordered as above)
import { useState, useCallback } from 'react';
import { useSlideStore } from '../stores/slideStore';
import type { Slide } from '../types';

// 2. Types (component-specific)
interface Props {
  slide: Slide;
  onSelect: (sid: string) => void;
  isSelected?: boolean;
}

// 3. Component
export const SlideCard: React.FC<Props> = ({
  slide,
  onSelect,
  isSelected = false,
}) => {
  // 3a. Store hooks (external state)
  const { updateSlide } = useSlideStore();

  // 3b. Local state
  const [isHovered, setIsHovered] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  // 3c. Derived values
  const displayTitle = slide.content.slice(0, 50);

  // 3d. Callbacks (memoized if passed to children)
  const handleClick = useCallback(() => {
    onSelect(slide.sid);
  }, [onSelect, slide.sid]);

  // 3e. Effects
  useEffect(() => {
    // side effects
  }, [dependency]);

  // 3f. Early returns (loading, error states)
  if (!slide) return null;

  // 3g. Render
  return (
    <div
      className="slide-card"
      onClick={handleClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* content */}
    </div>
  );
};
```

### JSX Formatting

```tsx
// Self-closing tags for empty elements
<Input />
<SlideCard slide={slide} />

// Multi-line props: one per line, sorted alphabetically
<SlideCard
  isSelected={isSelected}
  onDelete={handleDelete}
  onSelect={handleSelect}
  slide={slide}
/>

// Conditional rendering
{isLoading && <Spinner />}
{error ? <ErrorMessage error={error} /> : <Content />}
{slides.length > 0 && <SlideList slides={slides} />}

// Avoid inline functions in render (except simple cases)
// Bad: onClick={() => handleSelect(slide.sid)}
// Good: onClick={handleClick} (with useCallback)

// Fragment shorthand
<>
  <Header />
  <MainContent />
</>
```

### CSS / Tailwind Conventions

```tsx
// Use design tokens from global.css
<div className="bg-surface text-primary">

// Logical grouping: layout → spacing → appearance → state
<button className="
  flex items-center justify-center
  px-4 py-2 gap-2
  bg-primary text-white rounded-lg
  hover:bg-primary-dark focus:ring-2
  disabled:opacity-50
">

// Extract repeated patterns to components, not utility classes
// Bad: repeating same 10 classes everywhere
// Good: create <Button variant="primary"> component
```

## State Management

### Zustand Store Pattern

```typescript
import { create } from 'zustand';

interface SlideState {
  selectedSid: string | null;
  selectSlide: (sid: string) => void;
}

export const useSlideStore = create<SlideState>((set) => ({
  selectedSid: null,
  selectSlide: (sid) => set({ selectedSid: sid }),
}));
```

### Store Responsibilities

- `projectStore`: Project data, loading state
- `slideStore`: Slide selection, editing, generation tasks
- `uiStore`: Modals, playback, UI-only state

### When to Use Local State vs Store

- **Local state**: UI-only, single component (hover, focus)
- **Store**: Shared across components, persists navigation

## Concurrency

### Async Operations

Use async/await with proper error handling:

```typescript
const loadProject = async (slug: string) => {
  set({ isLoading: true, error: null });
  try {
    const project = await projectApi.get(slug);
    set({ project, isLoading: false });
  } catch (e) {
    set({ error: (e as Error).message, isLoading: false });
  }
};
```

### Task Polling

For long-running operations (image generation):

```typescript
const pollTask = async (taskId: string): Promise<TaskResult> => {
  while (true) {
    const task = await taskApi.get(taskId);
    if (task.status === 'completed') return task.result;
    if (task.status === 'failed') throw new Error(task.error);
    await new Promise(r => setTimeout(r, config.taskPollInterval));
  }
};
```

### Concurrent Updates

- Optimistic updates for better UX
- Rollback on API failure
- Use `AbortController` for cancellable requests

## Error Handling

### API Error Handling

```typescript
// api/client.ts
export const apiClient = {
  async get<T>(url: string): Promise<T> {
    const response = await fetch(`/api${url}`);
    if (!response.ok) {
      const error = await response.json();
      throw new ApiError(error.message, error.error);
    }
    return response.json();
  }
};
```

### Component Error Boundaries

```typescript
import { ErrorBoundary } from 'react-error-boundary';

<ErrorBoundary fallback={<ErrorFallback />}>
  <SlideEditor />
</ErrorBoundary>
```

### User Feedback

- Show loading spinners during async operations
- Display error messages in toast/alert
- Provide retry options for failed operations

## Logging

### Development Logging

```typescript
if (import.meta.env.DEV) {
  console.log('[SlideStore] Selecting slide:', sid);
}
```

### Store Middleware (Optional)

```typescript
import { devtools } from 'zustand/middleware';

export const useSlideStore = create<SlideState>()(
  devtools((set) => ({
    // ...
  }))
);
```

### What to Log

- Store state changes (dev only)
- API errors
- User actions for debugging

## Testing

### Component Testing

```typescript
import { render, screen } from '@testing-library/react';
import { SlideCard } from './SlideCard';

test('renders slide content', () => {
  const slide = { sid: '1', content: 'Test slide', ... };
  render(<SlideCard slide={slide} />);
  expect(screen.getByText('Test slide')).toBeInTheDocument();
});
```

### Store Testing

```typescript
import { useSlideStore } from './slideStore';

test('selectSlide updates selectedSid', () => {
  const { selectSlide } = useSlideStore.getState();
  selectSlide('slide-001');
  expect(useSlideStore.getState().selectedSid).toBe('slide-001');
});
```

## Configuration

```typescript
// config.ts
export const config = {
  apiBaseUrl: '/api',
  taskPollInterval: 1000,   // ms
  taskTimeout: 60000,       // ms
  playbackInterval: 5000,   // ms
};
```

## Styling Guidelines

### Tailwind CSS Usage

- Use utility classes for most styling
- Extract repeated patterns to components
- Use CSS variables for theme values

```tsx
<div className="flex items-center gap-2 p-4 bg-white rounded-lg shadow">
  {/* ... */}
</div>
```

### Responsive Design

- Mobile-first approach
- Use Tailwind breakpoints: `sm:`, `md:`, `lg:`
- Test on multiple screen sizes

### Accessibility

- Use semantic HTML elements
- Add `aria-*` attributes where needed
- Ensure keyboard navigation works
