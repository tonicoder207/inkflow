"""
InkFlow v3 Backend
Works in 3 modes:
  1. Dev:      python main.py
  2. Embedded: ..\\python\\python.exe main.py   (portable Python in app folder)
  3. Service:  started by Electron via child_process.spawn
"""
import os, sys

# ── Path setup ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Dirs from env (set by Electron) or sensible defaults
PROFILES_DIR = os.environ.get("INKFLOW_PROFILES_DIR",
    os.path.join(BASE_DIR, "..", "data", "profiles"))
EXPORTS_DIR  = os.environ.get("INKFLOW_EXPORTS_DIR",
    os.path.join(BASE_DIR, "..", "data", "exports"))
PORT = int(os.environ.get("INKFLOW_PORT", "8000"))

os.makedirs(PROFILES_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR,  exist_ok=True)
os.environ["INKFLOW_PROFILES_DIR"] = os.path.abspath(PROFILES_DIR)
os.environ["INKFLOW_EXPORTS_DIR"]  = os.path.abspath(EXPORTS_DIR)

# ── App ───────────────────────────────────────────────────────────────────────
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="InkFlow API", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Static exports
exports_abs = os.path.abspath(EXPORTS_DIR)
if os.path.isdir(exports_abs):
    app.mount("/exports", StaticFiles(directory=exports_abs), name="exports")

# ── Routers ───────────────────────────────────────────────────────────────────
from api.profiles    import router as profiles_router
from api.render      import router as render_router
from api.export      import router as export_router
from api.onenote     import router as onenote_router
from api.calibration import router as calibration_router
from api.license     import router as license_router

app.include_router(profiles_router,    prefix="/api/profiles")
app.include_router(render_router,      prefix="/api/render")
app.include_router(export_router,      prefix="/api/export")
app.include_router(onenote_router,     prefix="/api/onenote")
app.include_router(calibration_router, prefix="/api/calibration")
app.include_router(license_router,     prefix="/api/license")

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "3.0.0",
            "profiles_dir": PROFILES_DIR, "exports_dir": EXPORTS_DIR}

# ── Entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=PORT,
                log_level="warning", access_log=False)
