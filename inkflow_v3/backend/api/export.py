"""InkFlow v3 — Export API"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from models import ExportRequest, ExportResult
from engine import session_cache
from engine.exporter import export_pages

router = APIRouter()

@router.post("/", response_model=ExportResult)
async def do_export(req: ExportRequest):
    pages = session_cache.get(req.render_id)
    if pages is None: raise HTTPException(404, "Session expired, please re-render")
    try: result = export_pages(pages, fmt=req.format, dpi=req.dpi)
    except Exception as e: raise HTTPException(500, str(e))
    return ExportResult(
        download_url=f"http://127.0.0.1:8000/exports/{result['filename']}",
        filename=result["filename"],
        size_bytes=result["size_bytes"],
        filepath=result.get("filepath", ""))

@router.get("/download/{filename}")
async def download(filename: str):
    from utils.calibration_store import _cal_dir
    import pathlib
    env = os.environ.get("INKFLOW_EXPORTS_DIR", "")
    fpath = pathlib.Path(env) / filename if env else pathlib.Path(filename)
    if not fpath.exists(): raise HTTPException(404, "File not found")
    return FileResponse(str(fpath), filename=filename, media_type="application/octet-stream")
