"""InkFlow v3 — Render API"""
import io, base64, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import APIRouter, HTTPException
from models import RenderSettings, RenderResult
from profiles.manager import load_profile
from engine.handwriting import render_text_to_pages
from engine import session_cache
from PIL import Image

router = APIRouter()

@router.post("/", response_model=RenderResult)
async def render(s: RenderSettings):
    try: profile = load_profile(s.profile_id)
    except FileNotFoundError: raise HTTPException(404, "Profile not found")
    if not profile.characters: raise HTTPException(400, "No trained characters")
    if not s.text.strip():     raise HTTPException(400, "Empty text")
    try: pages = render_text_to_pages(profile, s)
    except Exception as e: raise HTTPException(500, str(e))
    rid = session_cache.store(pages)
    previews = []
    for page in pages:
        w, h = page.size
        ratio = 900 / w
        thumb = page.resize((900, int(h*ratio)), Image.LANCZOS)
        buf = io.BytesIO(); thumb.save(buf, "PNG", optimize=True)
        previews.append("data:image/png;base64," + base64.b64encode(buf.getvalue()).decode())
    return RenderResult(render_id=rid, page_count=len(pages),
        preview_urls=previews, width=pages[0].width, height=pages[0].height)
