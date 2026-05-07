"""InkFlow v3 — Session Cache"""
import uuid, time
from PIL import Image

_cache: dict = {}
TTL = 1800

def store(pages: list) -> str:
    _evict()
    rid = str(uuid.uuid4())
    _cache[rid] = {"pages": pages, "ts": time.time()}
    return rid

def get(rid: str):
    s = _cache.get(rid)
    return s["pages"] if s else None

def _evict():
    now = time.time()
    for k in [k for k,v in _cache.items() if now-v["ts"] > TTL]:
        del _cache[k]
