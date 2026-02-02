# GenSlides Backend Development Guidelines

IMPORTANT: Always use latest dependencies.

## Tech Stack

- **Language**: Python 3.12+
- **Framework**: FastAPI
- **Package Manager**: uv
- **AI SDK**: OpenAI SDK (via OpenRouter)

## Best Practices

### Python Best Practices

- Use `pathlib.Path` instead of `os.path` for file operations
- Use context managers (`with`) for resource management
- Prefer `dataclass` for simple data containers, `Pydantic` for validation
- Use `Enum` for fixed sets of values
- Avoid mutable default arguments (`def f(items=None)` not `def f(items=[])`)
- Use `typing.TypeAlias` for complex type definitions
- Prefer `list[str]` over `List[str]` (Python 3.9+)
- Use `|` for union types: `str | None` instead of `Optional[str]`

### FastAPI Best Practices

- Use dependency injection for services: `Depends(get_service)`
- Define response models explicitly: `response_model=ProjectResponse`
- Use `status_code` parameter for non-200 responses
- Group related routes with `APIRouter`
- Use `BackgroundTasks` for simple async work, `asyncio.create_task` for complex tasks
- Validate path parameters with `Path(...)` and query params with `Query(...)`
- Use `HTTPException` for error responses, not bare `raise`
- Enable CORS only for specific origins in production

### Async Best Practices

- Never mix sync and async I/O in the same function
- Use `asyncio.gather()` for concurrent operations
- Always `await` coroutines, never leave them dangling
- Use `async for` with async iterators
- Handle `asyncio.CancelledError` gracefully
- Set timeouts for external API calls: `asyncio.wait_for(coro, timeout=30)`

## Architecture Principles

### SOLID Principles

- **Single Responsibility**: Each module has one clear purpose
  - `api/` - HTTP routing and request validation only
  - `services/` - Business logic only
  - `storage/` - Data persistence only
  - `models/` - Domain entities only
- **Open/Closed**: Extend via new services, not modifying existing ones
- **Liskov Substitution**: Use abstract base classes for storage backends
- **Interface Segregation**: Small, focused Pydantic schemas
- **Dependency Inversion**: Services depend on abstractions, not concrete implementations

### YAGNI (You Aren't Gonna Need It)

- Implement only what the current API specification requires
- No premature abstractions or generic frameworks
- Add features when they are actually needed

### KISS (Keep It Simple, Stupid)

- Prefer simple, readable code over clever solutions
- Use standard library when sufficient
- Avoid deep inheritance hierarchies

### DRY (Don't Repeat Yourself)

- Extract common logic into utility functions
- Use Pydantic models for validation reuse
- Centralize configuration in `config.py`

## Project Structure

```
backend/
├── src/genslide/
│   ├── __init__.py
│   ├── main.py           # FastAPI app entry point
│   ├── config.py         # Pydantic settings
│   │
│   ├── api/              # API Layer
│   │   ├── router.py     # Route registration
│   │   ├── projects.py   # Project endpoints
│   │   ├── slides.py     # Slide endpoints
│   │   ├── images.py     # Image endpoints
│   │   └── schemas.py    # Request/response models
│   │
│   ├── services/         # Business Layer
│   │   ├── project_service.py
│   │   ├── slide_service.py
│   │   ├── image_service.py
│   │   ├── gemini_client.py
│   │   └── cost_service.py
│   │
│   ├── storage/          # Storage Layer
│   │   ├── file_storage.py
│   │   └── outline_store.py
│   │
│   ├── models/           # Domain Models
│   │   ├── project.py
│   │   ├── slide.py
│   │   └── image.py
│   │
│   └── utils/            # Utilities
│       └── hash.py       # blake3 hashing
│
└── tests/
```

## Layer Dependencies

```
API Layer → Service Layer → Storage Layer
              ↓
           Models
```

- API layer ONLY calls services
- Services handle all business logic
- Storage handles only file I/O
- No circular dependencies

## Commands

```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --extra dev

# Run development server
uv run uvicorn genslide.main:app --reload --port 3003

# Run tests
uv run pytest

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Add dependency
uv add <package>

# Add dev dependency
uv add --dev <package>
```

## Code Style

### Naming Conventions

```python
# Variables and functions: snake_case
user_name = "john"
def get_user_by_id(user_id: int) -> User: ...

# Classes: PascalCase
class ProjectService: ...
class CreateSlideRequest(BaseModel): ...

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3
DEFAULT_IMAGE_SIZE = "2K"

# Private: leading underscore
def _internal_helper(): ...
self._tasks: dict[str, dict] = {}

# Module-level "constants": UPPER_SNAKE_CASE
API_VERSION = "v1"
```

### Import Order

```python
# 1. Standard library
import asyncio
from pathlib import Path
from uuid import uuid4

# 2. Third-party packages
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

# 3. Local imports
from .services import ProjectService
from ..models import Project
```

### Type Hints

Always use type hints for function signatures:

```python
async def get_project(slug: str) -> Project:
    ...

def compute_hash(content: str) -> str:
    ...

# Use | for unions (Python 3.10+)
def find_slide(sid: str) -> Slide | None:
    ...

# Use generics for collections
def get_all_slides() -> list[Slide]:
    ...
```

### Docstrings

Use Google-style docstrings for public functions:

```python
async def generate_image(
    self,
    prompt: str,
    output_path: Path,
    style_image: Image | None = None,
) -> Path:
    """Generate an image from a text prompt.

    Args:
        prompt: Text description of the image to generate.
        output_path: Where to save the generated image.
        style_image: Optional reference image for style transfer.

    Returns:
        Path to the saved image file.

    Raises:
        RuntimeError: If the API response contains no image data.
    """
```

### String Formatting

```python
# Prefer f-strings for readability
logger.info(f"Creating project: {slug}")
url = f"/api/images/{sid}/{content_hash}.jpg"

# Use .format() for reusable templates
TEMPLATE = "Project {name} created at {time}"
message = TEMPLATE.format(name=slug, time=now)
```

### Pydantic Models

Use Pydantic for all request/response schemas:

```python
class CreateSlideRequest(BaseModel):
    content: str
    after_sid: str | None = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
        str_min_length=1,
    )
```

### Async/Await

Use async for all I/O operations:

```python
async def generate_image(self, prompt: str) -> Path:
    response = await self.client.generate(...)
    ...

# Concurrent operations
results = await asyncio.gather(
    self.load_project(slug),
    self.load_images(slug),
)
```

### Line Length and Formatting

- Max line length: 100 characters (configured in ruff)
- Use trailing commas in multi-line structures
- Break long function calls appropriately:

```python
# Good: clear parameter alignment
response = await self.client.models.generate_content(
    model=self.model,
    contents=contents,
    config=types.GenerateContentConfig(
        image_config=types.ImageConfig(
            aspect_ratio=aspect_ratio,
            image_size=image_size,
        )
    ),
)
```

## Concurrency

### Async Task Management

- Use `asyncio.create_task()` for background image generation
- Store task status in memory (dict) for MVP
- Future: Consider Redis for distributed task state

### Request Handling

- FastAPI handles concurrent requests automatically
- Each request runs in its own coroutine
- File I/O should use `aiofiles` for non-blocking access

### Task Pattern

```python
async def generate_slide_image(self, ...) -> str:
    task_id = str(uuid4())
    self._tasks[task_id] = {"status": "pending"}
    asyncio.create_task(self._do_generate(task_id, ...))
    return task_id
```

## Error Handling

### HTTP Exceptions

Use FastAPI's HTTPException with consistent error format:

```python
from fastapi import HTTPException

raise HTTPException(
    status_code=404,
    detail={"error": "project_not_found", "message": "项目不存在"}
)
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| project_not_found | 404 | Project does not exist |
| slide_not_found | 404 | Slide does not exist |
| image_not_found | 404 | Image does not exist |
| validation_error | 400 | Request validation failed |
| generation_failed | 503 | AI service error |

### Exception Handling in Services

```python
async def _do_generate(self, task_id: str, ...):
    try:
        self._tasks[task_id]["status"] = "processing"
        # ... generation logic
        self._tasks[task_id]["status"] = "completed"
    except Exception as e:
        self._tasks[task_id] = {
            "status": "failed",
            "error": str(e)
        }
```

## Logging

### Configuration

Use Python's standard logging with structured output:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
```

### Log Levels

- **ERROR**: Failed operations, exceptions
- **WARNING**: Recoverable issues, deprecations
- **INFO**: Important state changes, API requests
- **DEBUG**: Detailed debugging information

### What to Log

```python
# API requests
logger.info(f"Creating project: {slug}")

# Service operations
logger.info(f"Generating image for slide {sid}")

# Errors
logger.error(f"Generation failed: {e}", exc_info=True)
```

## Testing

### Test Structure

```python
import pytest
from httpx import AsyncClient
from genslide.main import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_project(client):
    response = await client.post("/api/projects/test", json={"title": "Test"})
    assert response.status_code == 201
```

### Test Categories

- Unit tests: Individual functions and methods
- Integration tests: API endpoints with mocked services
- E2E tests: Full flow with real file system

## Configuration

Environment variables via `.env`:

```bash
GOOGLE_API_KEY=your-key
DATA_DIR=./data
IMAGE_MODEL=gemini-3-pro-image-preview
```

Access via Pydantic settings:

```python
from genslide.config import settings

api_key = settings.google_api_key
```
