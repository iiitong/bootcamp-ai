# GenSlide Backend

AI-powered slide image generator backend built with FastAPI.

## Setup

```bash
# Install dependencies
uv sync

# Run development server
uv run uvicorn genslide.main:app --reload --port 3003
```

## Configuration

Copy `.env.example` to `.env` and configure your OpenRouter API key:

```bash
cp .env.example .env
```

Get your API key at: https://openrouter.ai/keys

```env
# Required
OPENROUTER_API_KEY=sk-or-v1-your-api-key-here

# Optional - use free tier model (default)
IMAGE_MODEL=google/gemini-2.5-flash-image-preview:free
```

## API Endpoints

- `GET /health` - Health check
- `GET /api/projects/{slug}` - Get project details
- `POST /api/projects/{slug}` - Create project
- `PATCH /api/projects/{slug}` - Update project
- `POST /api/projects/{slug}/slides` - Create slide
- `PATCH /api/projects/{slug}/slides/{sid}` - Update slide
- `DELETE /api/projects/{slug}/slides/{sid}` - Delete slide
- `PUT /api/projects/{slug}/slides/order` - Reorder slides
- `POST /api/projects/{slug}/slides/{sid}/generate` - Generate slide image
- `POST /api/projects/{slug}/style/generate` - Generate style candidates
- `POST /api/projects/{slug}/style/select` - Select style
- `GET /api/tasks/{task_id}` - Get task status
- `GET /api/images/{path}` - Get image
- `GET /api/projects/{slug}/cost` - Get cost breakdown
