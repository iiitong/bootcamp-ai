"""Blake3 hashing utilities."""

import blake3


def compute_content_hash(content: str) -> str:
    """
    Compute the blake3 hash of content.

    Args:
        content: The string content to hash.

    Returns:
        A 16-character hexadecimal hash string.
    """
    h = blake3.blake3(content.encode("utf-8"))
    return h.hexdigest()[:16]  # First 16 characters is enough for uniqueness
