"""InkFlow v3 — OneNote Writing API"""
import sys, os, uuid, threading, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models import WriteRequest, WriteStatus
from profiles.manager import load_profile
from utils.calibration_store import load_calibration
from engine.onenote_writer import create_job, get_job, write_text_to_screen, pen_injector, HAS_PEN_INJECTION

router = APIRouter()

class TestSquareRequest(BaseModel):
    x: int
    y: int
    size: int = 50
    scaling_factor: float = 1.0

@router.post("/start", response_model=WriteStatus)
async def start_write(req: WriteRequest):
    # Contract boundary for Frontend -> Backend -> Writer:
    # req.profile_id / req.calibration_id must match persisted objects and
    # req text/render params are forwarded unchanged into write_text_to_screen.
    try: profile = load_profile(req.profile_id)
    except FileNotFoundError: raise HTTPException(404, "Profile not found")
    try: calibration = load_calibration(req.calibration_id)
    except FileNotFoundError: raise HTTPException(404, "Calibration not found")
    if not profile.characters: raise HTTPException(400, "No trained characters")
    if not req.text.strip():   raise HTTPException(400, "Empty text")

    job_id = str(uuid.uuid4())[:8]
    job = create_job(job_id)

    def run():
        write_text_to_screen(
            job=job, profile=profile, calibration=calibration,
            text=req.text, speed=req.speed,
            words_per_second=req.words_per_second,
            font_size_scale=req.font_size_scale,
            size_variation=req.size_variation,
            rotation_variation=req.rotation_variation,
            vertical_jitter=req.vertical_jitter,
            point_delay_s=req.point_delay_s,
            pressure=req.pressure,
        )

    t = threading.Thread(target=run, daemon=True)
    t.start()

    return WriteStatus(job_id=job_id, status="running", progress=0.0,
        chars_done=0, chars_total=len(req.text), current_line=0,
        message="Gestartet — Esc zum Abbrechen")

@router.get("/status/{job_id}", response_model=WriteStatus)
async def write_status(job_id: str):
    job = get_job(job_id)
    if not job: raise HTTPException(404, "Job not found")
    return WriteStatus(job_id=job_id, status=job.status,
        progress=job.progress, chars_done=job.chars_done,
        chars_total=job.chars_total, current_line=job.current_line,
        message=job.message)

@router.post("/pause/{job_id}")
async def pause_write(job_id: str):
    job = get_job(job_id)
    if not job: raise HTTPException(404, "Job not found")
    job.pause(); return {"status": "paused"}

@router.post("/resume/{job_id}")
async def resume_write(job_id: str):
    job = get_job(job_id)
    if not job: raise HTTPException(404, "Job not found")
    job.resume(); return {"status": "running"}

@router.post("/cancel/{job_id}")
async def cancel_write(job_id: str):
    job = get_job(job_id)
    if not job: raise HTTPException(404, "Job not found")
    job.cancel(); return {"status": "cancelled"}

@router.get("/mouse-pos")
async def get_mouse_pos():
    """Return current mouse cursor position (used during calibration)."""
    try:
        try:
            import win32api
            x, y = win32api.GetCursorPos()
        except Exception:
            import ctypes

            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            x, y = pt.x, pt.y
        return {"x": x, "y": y}
    except Exception as e:
        raise HTTPException(500, f"Cannot get mouse position: {e}")

@router.post("/test-square")
async def test_square(req: TestSquareRequest):
    """
    Draw a small square at the given coordinates using Pen Injection.
    """
    if not HAS_PEN_INJECTION:
        raise HTTPException(500, "Pen Injection not available")
        
    try:
        x, y, sz, sf = req.x, req.y, req.size, req.scaling_factor
        time.sleep(0.5)

        def sx(val): return int(val * sf)
        def sy(val): return int(val * sf)

        # Draw square using pen injector
        pen_injector.down(sx(x), sy(y), 512)
        time.sleep(0.1)
        
        # Top
        for i in range(11):
            pen_injector.move(sx(x + int(sz * i/10)), sy(y), 512)
            time.sleep(0.01)
        # Right
        for i in range(11):
            pen_injector.move(sx(x + sz), sy(y + int(sz * i/10)), 512)
            time.sleep(0.01)
        # Bottom
        for i in range(11):
            pen_injector.move(sx(x + sz - int(sz * i/10)), sy(y + sz), 512)
            time.sleep(0.01)
        # Left
        for i in range(11):
            pen_injector.move(sx(x), sy(y + sz - int(sz * i/10)), 512)
            time.sleep(0.01)
            
        pen_injector.up(sx(x), sy(y))

        return {"status": "ok", "x": x, "y": y, "size": sz}
    except Exception as e:
        raise HTTPException(500, f"Test square failed: {e}")
