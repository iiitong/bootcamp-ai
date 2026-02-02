"""OpenRouter image generation client using OpenAI-compatible API."""

import base64
import io
import logging
from collections import Counter
from pathlib import Path

import httpx
from PIL import Image

from ..config import settings

logger = logging.getLogger(__name__)


def extract_color_palette(image: Image.Image, num_colors: int = 5) -> list[str]:
    """
    Extract dominant colors from an image.

    Args:
        image: PIL Image to analyze.
        num_colors: Number of dominant colors to extract.

    Returns:
        List of hex color strings (e.g., ["#F5C6A5", "#8BA4B7"]).
    """
    # Resize for faster processing
    small = image.copy()
    small.thumbnail((100, 100))

    # Convert to RGB if needed
    if small.mode != "RGB":
        small = small.convert("RGB")

    # Quantize to reduce colors
    quantized = small.quantize(colors=num_colors, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette()

    # Get color counts
    color_counts = Counter(quantized.getdata())
    most_common = color_counts.most_common(num_colors)

    # Convert palette indices to hex colors
    hex_colors = []
    for idx, _count in most_common:
        if palette:
            r = palette[idx * 3]
            g = palette[idx * 3 + 1]
            b = palette[idx * 3 + 2]
            hex_colors.append(f"#{r:02X}{g:02X}{b:02X}")

    return hex_colors


def describe_color(hex_color: str) -> str:
    """Convert hex color to a human-readable description."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)

    # Determine basic color name based on RGB values
    max_val = max(r, g, b)
    min_val = min(r, g, b)

    # Check for grayscale
    if max_val - min_val < 30:
        if max_val > 200:
            return f"off-white ({hex_color})"
        elif max_val > 150:
            return f"light gray ({hex_color})"
        elif max_val > 80:
            return f"gray ({hex_color})"
        else:
            return f"dark gray ({hex_color})"

    # Determine dominant hue
    if r >= g and r >= b:
        if g > b + 30:
            return f"warm orange/peach ({hex_color})"
        elif b > g + 30:
            return f"pink/magenta ({hex_color})"
        else:
            return f"red/coral ({hex_color})"
    elif g >= r and g >= b:
        if r > b + 30:
            return f"yellow-green ({hex_color})"
        elif b > r + 30:
            return f"teal/cyan ({hex_color})"
        else:
            return f"green ({hex_color})"
    else:  # b is dominant
        if r > g + 30:
            return f"purple/violet ({hex_color})"
        elif g > r + 30:
            return f"sky blue/cyan ({hex_color})"
        else:
            return f"blue ({hex_color})"


class ImageGenerationClient:
    """OpenRouter image generation client using direct HTTP requests."""

    def __init__(
        self,
        api_key: str,
        model: str = "google/gemini-2.5-flash-image-preview:free",
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        """
        Initialize the OpenRouter client.

        Args:
            api_key: OpenRouter API key.
            model: Model name to use for image generation.
            base_url: API base URL (default: OpenRouter).
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def generate_image(
        self,
        prompt: str,
        output_path: Path,
        aspect_ratio: str = "16:9",
        style_image: Image.Image | None = None,
    ) -> Path:
        """
        Generate an image and save it to the specified path.

        Args:
            prompt: Text description of the image to generate.
            output_path: Path where the image will be saved.
            aspect_ratio: Aspect ratio (e.g., "16:9", "1:1", "9:16").
            style_image: Optional style reference image.

        Returns:
            Path to the saved image.

        Raises:
            RuntimeError: If the API response doesn't contain image data.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build messages
        messages = []

        # Add style reference if provided
        if style_image is not None:
            # Extract color palette from style image instead of sending the full image
            # This prevents the model from copying specific visual elements
            colors = extract_color_palette(style_image, num_colors=5)
            color_descriptions = [describe_color(c) for c in colors]
            color_list = "\n".join(f"  - {desc}" for desc in color_descriptions)

            # Build prompt with color palette description only
            style_prompt = (
                f"Create an illustration for a presentation slide about:\n"
                f"{prompt}\n\n"
                f"COLOR PALETTE to use (extracted from brand style):\n"
                f"{color_list}\n\n"
                f"STYLE GUIDELINES:\n"
                f"- Use ONLY the colors listed above (or close variations)\n"
                f"- Create a clean, modern infographic style\n"
                f"- Use flat design with minimal gradients\n"
                f"- Include relevant icons or symbols for the topic\n"
                f"- Add a clear title text at the top\n\n"
                f"Generate the image now."
            )

            logger.info(f"Style prompt with colors: {style_prompt[:200]}...")

            messages.append({
                "role": "user",
                "content": style_prompt,
            })
        else:
            messages.append({
                "role": "user",
                "content": f"Generate an image that illustrates: {prompt}",
            })

        # Build request payload
        payload = {
            "model": self.model,
            "messages": messages,
            "modalities": ["text", "image"],
            "image_config": {
                "aspect_ratio": aspect_ratio,
            },
        }

        # Make direct HTTP request to get raw JSON response
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        logger.debug(f"Raw API response keys: {data.keys()}")

        # Extract image from response
        if "choices" in data and data["choices"]:
            message = data["choices"][0].get("message", {})
            logger.debug(f"Message keys: {message.keys()}")

            # Check for images field (OpenRouter extension)
            images = message.get("images", [])
            if images:
                logger.debug(f"Found {len(images)} images")
                image_bytes = self._extract_image_bytes(images[0])
                if image_bytes:
                    image = Image.open(io.BytesIO(image_bytes))
                    image.save(str(output_path))
                    logger.info(f"Image saved to {output_path}")
                    return output_path

            # Check content for image parts
            content = message.get("content")
            if isinstance(content, list):
                for part in content:
                    image_bytes = self._extract_image_from_part(part)
                    if image_bytes:
                        image = Image.open(io.BytesIO(image_bytes))
                        image.save(str(output_path))
                        logger.info(f"Image saved to {output_path}")
                        return output_path

            # Log for debugging
            logger.error(f"No image found in response. Message: {message}")

        raise RuntimeError("API response did not contain image data")

    def _extract_image_bytes(self, image_data) -> bytes | None:
        """Extract image bytes from various formats."""
        logger.debug(f"Extracting from: type={type(image_data)}, value={str(image_data)[:200]}")

        # String format: data URL or raw base64
        if isinstance(image_data, str):
            if image_data.startswith("data:"):
                _, b64_data = image_data.split(",", 1)
                return base64.b64decode(b64_data)
            # Try raw base64
            try:
                return base64.b64decode(image_data)
            except Exception:
                pass

        # Dict format
        if isinstance(image_data, dict):
            # OpenRouter format: {"type": "image_url", "image_url": {"url": "data:..."}}
            if image_data.get("type") == "image_url":
                url = image_data.get("image_url", {}).get("url", "")
                if url.startswith("data:"):
                    _, b64_data = url.split(",", 1)
                    return base64.b64decode(b64_data)

            # Direct url field
            url = image_data.get("url")
            if url and isinstance(url, str) and url.startswith("data:"):
                _, b64_data = url.split(",", 1)
                return base64.b64decode(b64_data)

            # b64_json field (OpenAI format)
            b64 = image_data.get("b64_json") or image_data.get("data")
            if b64 and isinstance(b64, str):
                return base64.b64decode(b64)

        return None

    def _extract_image_from_part(self, part) -> bytes | None:
        """Extract image bytes from a content part."""
        if isinstance(part, dict):
            if part.get("type") in ("image_url", "image"):
                return self._extract_image_bytes(part.get("image_url", part))
            return self._extract_image_bytes(part)
        return None

    async def generate_style_candidates(
        self,
        prompt: str,
        output_dir: Path,
        count: int = 2,
    ) -> list[Path]:
        """
        Generate multiple style candidate images.

        Args:
            prompt: Style description text.
            output_dir: Output directory for images.
            count: Number of images to generate.

        Returns:
            List of paths to generated images.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        paths = []

        for i in range(count):
            output_path = output_dir / f"style-candidate-{i + 1}.jpg"
            varied_prompt = f"{prompt} (variation {i + 1})"
            await self.generate_image(varied_prompt, output_path)
            paths.append(output_path)

        return paths


# Alias for backward compatibility
GeminiImageClient = ImageGenerationClient
