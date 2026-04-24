"""
Simple caching mechanism for GitHub API responses to avoid rate limiting.
"""

import json
import time
from pathlib import Path
import pulsar_env

CACHE_DIR = Path(pulsar_env.PULSAR_CACHE_DIR) / 'github_api'
CACHE_DURATION = 3600  # 1 hour in seconds


def get_cached_response(url: str) -> dict | None:
    """Get cached API response if it exists and is not expired."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Create a safe filename from the URL
    cache_file = CACHE_DIR / f"{hash(url)}.json"

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, 'r') as f:
            cached_data = json.load(f)

        # Check if cache is still valid
        if time.time() - cached_data['cached_at'] < CACHE_DURATION:
            return cached_data['response']
        else:
            # Cache expired, remove it
            cache_file.unlink()
            return None
    except Exception:
        return None


def cache_response(url: str, response_data: dict):
    """Cache an API response."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cache_file = CACHE_DIR / f"{hash(url)}.json"

    cached_data = {
        'url': url,
        'cached_at': time.time(),
        'response': response_data
    }

    try:
        with open(cache_file, 'w') as f:
            json.dump(cached_data, f)
    except Exception:
        pass  # Fail silently if caching doesn't work


def clear_cache():
    """Clear all cached API responses."""
    if CACHE_DIR.exists():
        import shutil
        shutil.rmtree(CACHE_DIR)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
