"""Schema loader with disk cache fallback to URL fetch.

Mirrors the entity_helpers pattern — rules import load_schema() from here
instead of calling urllib directly, so the disk cache at models/ is always
tried first and network fetches only happen when a schema is not cached locally.
"""

import json
import os
import urllib.request
from pathlib import Path


def _models_dir() -> Path:
    """Resolve the models/ directory relative to this file's location.

    In the cached logic package this file lives at:
        <logic_root>/schema_helpers/schema_loader.py
    so models/ is one level up:
        <logic_root>/models/
    """
    return Path(__file__).parent.parent / "models"


def load_schema(schema_url: str) -> dict:
    """Load a JSON schema, trying the local disk cache before fetching from URL.

    For https:// URLs the filename (last path segment of the URL) is looked up
    in the models/ directory that sits alongside this package in the logic root.
    If found the cached copy is returned without any network call. If not found
    the schema is fetched from the URL directly.

    file:// URLs (used in tests) are resolved to an absolute path and read
    from disk; no cache lookup is performed.

    Args:
        schema_url: Schema URL — https://, http://, or file://.

    Returns:
        Parsed schema dict.

    Raises:
        RuntimeError: If the schema cannot be loaded from disk or URL.
    """
    # --- file:// handling (test / local-dev paths) ---
    if schema_url.startswith("file://"):
        if not schema_url.startswith("file:///"):
            # Relative file:// URL — resolve relative to cwd
            relative_path = schema_url[7:]  # strip 'file://'
            absolute_path = os.path.abspath(os.path.join(os.getcwd(), relative_path))
            schema_url = f"file://{absolute_path}"
        try:
            with urllib.request.urlopen(schema_url, timeout=10) as response:
                return json.loads(response.read())
        except Exception as e:
            raise RuntimeError(f"Failed to load schema from {schema_url}: {e}")

    # --- https:// / http:// handling — disk cache first ---
    filename = schema_url.rstrip("/").split("/")[-1]
    cached_path = _models_dir() / filename

    if cached_path.exists():
        try:
            return json.loads(cached_path.read_text())
        except Exception:
            pass  # Corrupt cache file — fall through to network fetch

    try:
        with urllib.request.urlopen(schema_url, timeout=10) as response:
            return json.loads(response.read())
    except Exception as e:
        raise RuntimeError(f"Failed to load schema from {schema_url}: {e}")
