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


def parse_mysql_url(url: str) -> dict:
    """Parse MySQL connection URL into connection parameters.

    Args:
        url: MySQL connection URL (e.g., 'mysql://user:pass@host:port/database')

    Returns:
        Dictionary with connection parameters for aiomysql:
        - host: Database host (default: localhost)
        - port: Database port (default: 3306)
        - user: Database user (default: root)
        - password: Database password (default: empty string)
        - db: Database name (default: None)
    """
    parsed = urlparse(url)

    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": parsed.username or "root",
        "password": parsed.password or "",
        "db": parsed.path.lstrip("/") if parsed.path else None,
    }


def mask_password(url: str) -> str:
    """Mask password in connection URL for display.

    Args:
        url: Database connection URL with potential password

    Returns:
        URL with password replaced by '***'

    Examples:
        >>> mask_password("postgresql://user:secret@localhost:5432/db")
        'postgresql://user:***@localhost:5432/db'
        >>> mask_password("postgresql://localhost:5432/db")
        'postgresql://localhost:5432/db'
    """
    if "@" in url and ":" in url:
        try:
            prefix_end = url.index("://") + 3
            at_pos = url.index("@")
            user_pass = url[prefix_end:at_pos]
            if ":" in user_pass:
                user, _ = user_pass.split(":", 1)
                return url[:prefix_end] + user + ":***" + url[at_pos:]
        except (ValueError, IndexError):
            pass
    return url


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase.

    Args:
        string: Snake case string (e.g., 'my_variable_name')

    Returns:
        Camel case string (e.g., 'myVariableName')

    Examples:
        >>> to_camel("hello_world")
        'helloWorld'
        >>> to_camel("single")
        'single'
    """
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])
