"""InkFlow v3 — Profiles API"""
import io, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
import numpy as np, cv2
from PIL import Image

from models import HandwritingProfile, ProfileSummary
from profiles.manager import (list_profiles, load_profile, create_profile,
    delete_profile, save_character_variant, get_character_variants)
from engine.handwriting import segment_single_char

router = APIRouter()

@router.get("/", response_model=list[ProfileSummary])
async def get_profiles(): return list_profiles()

@router.post("/create", response_model=HandwritingProfile)
async def new_profile(name: str = Form(...)):
    return create_profile(name)

@router.get("/{pid}", response_model=HandwritingProfile)
async def get_profile(pid: str):
    try: return load_profile(pid)
    except FileNotFoundError: raise HTTPException(404, "Not found")

@router.delete("/{pid}")
async def del_profile(pid: str):
    delete_profile(pid); return {"deleted": pid}

@router.put("/{pid}/settings", response_model=HandwritingProfile)
async def update_settings(pid: str, updates: dict):
    try: p = load_profile(pid)
    except FileNotFoundError: raise HTTPException(404, "Not found")
    for k,v in updates.items():
        if hasattr(p, k): setattr(p, k, v)
    from profiles.manager import save_profile
    save_profile(p); return p

@router.post("/{pid}/upload-character")
async def upload_char(pid: str, character: str = Form(...), file: UploadFile = File(...)):
    try: load_profile(pid)
    except FileNotFoundError: raise HTTPException(404, "Not found")
    raw = await file.read()
    arr = np.frombuffer(raw, np.uint8)
    img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img_bgr is None: raise HTTPException(400, "Invalid image")
    cleaned = segment_single_char(img_bgr)
    if cleaned is None: raise HTTPException(400, "No stroke detected")
    pil = Image.fromarray(cv2.cvtColor(cleaned, cv2.COLOR_BGRA2RGBA))
    buf = io.BytesIO(); pil.save(buf, "PNG")
    v = save_character_variant(pid, character, buf.getvalue(), pil.width, pil.height)
    return {"character": character, "variant": v}

@router.get("/{pid}/char-preview/{char_hex}")
async def char_preview(pid: str, char_hex: str):
    char = bytes.fromhex(char_hex).decode("utf-8")
    variants = get_character_variants(pid, char)
    if not variants: raise HTTPException(404, "No variants")
    return FileResponse(variants[0].image_path, media_type="image/png")
