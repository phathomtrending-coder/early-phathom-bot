import json
import os
from typing import Dict, Optional

CACHE_PATH = "token_cache.json"

_cache: Dict[str, dict] = {}


def init_storage():
    global _cache
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r") as f:
                _cache = json.load(f)
        except Exception:
            _cache = {}
    else:
        _cache = {}


def save_cache():
    try:
        with open(CACHE_PATH, "w") as f:
            json.dump(_cache, f)
    except Exception:
        pass


def cache_token_result(token_data: dict):
    mint = token_data["mint"]
    _cache[mint] = token_data
    save_cache()


def get_cached_token(mint: str) -> Optional[dict]:
    return _cache.get(mint)
