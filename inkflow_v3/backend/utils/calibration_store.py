"""InkFlow v3 — Calibration Manager"""
import json, os
from pathlib import Path
from datetime import datetime
from models import CalibrationProfile

def _cal_dir() -> Path:
    env = os.environ.get("INKFLOW_PROFILES_DIR")
    base = Path(env) if env else Path(__file__).parent.parent.parent / "data" / "profiles"
    return base.parent / "calibrations"

def list_calibrations() -> list[CalibrationProfile]:
    d = _cal_dir()
    if not d.exists(): return []
    result = []
    for f in sorted(d.glob("*.json")):
        try:
            with open(f, "r") as fp:
                result.append(CalibrationProfile(**json.load(fp)))
        except: continue
    return result

def load_calibration(cal_id: str) -> CalibrationProfile:
    f = _cal_dir() / f"{cal_id}.json"
    if not f.exists(): raise FileNotFoundError(f"Calibration '{cal_id}' not found")
    with open(f, "r") as fp:
        return CalibrationProfile(**json.load(fp))

def save_calibration(cal: CalibrationProfile):
    d = _cal_dir()
    d.mkdir(parents=True, exist_ok=True)
    cal.created_at = cal.created_at or datetime.utcnow().isoformat()
    with open(d / f"{cal.id}.json", "w") as f:
        json.dump(cal.model_dump(), f, indent=2)

def delete_calibration(cal_id: str):
    f = _cal_dir() / f"{cal_id}.json"
    if f.exists(): f.unlink()
