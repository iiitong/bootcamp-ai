"""Database utility functions."""

from urllib.parse import urlparse


def detect_db_type(url: str) -> str:
    """Detect database type from connection URL.

    Args:
        url: Database connection URL (e.g., 'postgresql://...', 'mysql://...')

    Returns:
        Database type string: 'postgresql' or 'mysql'

    Raises:
        ValueError: If the URL scheme is not supported
    """
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme in ("postgresql", "postgres"):
        return "postgresql"
    elif scheme in ("mysql", "mysql+aiomysql"):
        return "mysql"
    else:
        raise ValueError(f"Unsupported database type: {scheme}")
