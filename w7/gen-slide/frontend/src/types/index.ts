// types/index.ts

export interface Project {
  slug: string;
  title: string;
  style: StyleConfig | null;
  slides: Slide[];
  totalCost: number;
}

export interface StyleConfig {
  prompt: string;
  image: string; // URL
}

export interface Slide {
  sid: string;
  content: string;
  images: SlideImage[];
  currentHash: string; // Current content's blake3 hash
  hasMatchingImage: boolean; // Whether there's an image matching current hash
}

export interface SlideImage {
  hash: string;
  url: string;
  createdAt: string;
}

export interface GenerateTask {
  taskId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result?: {
    hash: string;
    url: string;
    cost: number;
  };
  error?: string;
}

export interface StyleCandidate {
  id: string;
  url: string;
}

export interface CostBreakdown {
  totalCost: number;
  breakdown: {
    styleGeneration: number;
    slideImages: number;
  };
  imageCount: number;
}

// API Response Types (snake_case from backend)
export interface ProjectResponse {
  slug: string;
  title: string;
  style: { prompt: string; image: string } | null;
  slides: SlideResponse[];
  total_cost: number;
}

export interface SlideResponse {
  sid: string;
  content: string;
  images: { hash: string; url: string; created_at: string }[];
  current_hash: string;
  has_matching_image: boolean;
}

export interface TaskResponse {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result?: {
    hash: string;
    url: string;
    cost: number;
  };
  error?: string;
}

export interface StyleTaskResponse {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result?: {
    candidates: { id: string; url: string }[];
    cost: number;
  };
  error?: string;
}

// Transform functions
export function transformProjectResponse(response: ProjectResponse): Project {
  return {
    slug: response.slug,
    title: response.title,
    style: response.style,
    slides: response.slides.map(transformSlideResponse),
    totalCost: response.total_cost,
  };
}

export function transformSlideResponse(response: SlideResponse): Slide {
  return {
    sid: response.sid,
    content: response.content,
    images: response.images.map((img) => ({
      hash: img.hash,
      url: img.url,
      createdAt: img.created_at,
    })),
    currentHash: response.current_hash,
    hasMatchingImage: response.has_matching_image,
  };
}

export function transformTaskResponse(response: TaskResponse): GenerateTask {
  return {
    taskId: response.task_id,
    status: response.status,
    result: response.result,
    error: response.error,
  };
}
