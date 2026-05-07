"""InkFlow v3 — Calibration API"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import APIRouter, HTTPException
import cv2
import numpy as np
from models import CalibrationProfile
from utils.calibration_store import (list_calibrations, load_calibration,
    save_calibration, delete_calibration)

router = APIRouter()

@router.get("/", response_model=list[CalibrationProfile])
async def get_calibrations(): return list_calibrations()

@router.post("/create", response_model=CalibrationProfile)
async def create_cal(cal: CalibrationProfile):
    if not cal.id:
        import uuid
        cal.id = str(uuid.uuid4())[:8]
    save_calibration(cal)
    return cal

@router.get("/{cal_id}", response_model=CalibrationProfile)
async def get_cal(cal_id: str):
    try: return load_calibration(cal_id)
    except FileNotFoundError: raise HTTPException(404, "Not found")

@router.put("/{cal_id}", response_model=CalibrationProfile)
async def update_cal(cal_id: str, cal: CalibrationProfile):
    cal.id = cal_id
    save_calibration(cal); return cal

@router.delete("/{cal_id}")
async def del_cal(cal_id: str):
    delete_calibration(cal_id); return {"deleted": cal_id}

@router.post("/{cal_id}/compute")
async def compute_from_points(cal_id: str):
    """
    After user has clicked the calibration points,
    compute write area dimensions, line height and perspective transform.
    Preferred scheme: 4 points (top_left, top_right, bottom_right, bottom_left).
    Also supports first_line and second_line for precision height.
    """
    try: cal = load_calibration(cal_id)
    except FileNotFoundError: raise HTTPException(404, "Not found")

    pts = {p.label: p for p in cal.points}

    # Precision line height from first/second line clicks
    if "first_line" in pts and "second_line" in pts:
        cal.first_line_y = pts["first_line"].y
        cal.second_line_y = pts["second_line"].y
        cal.line_height_px = abs(cal.second_line_y - cal.first_line_y)

    required4 = ["top_left", "top_right", "bottom_right", "bottom_left"]
    if all(name in pts for name in required4):
        tl = pts["top_left"]
        tr = pts["top_right"]
        br = pts["bottom_right"]
        bl = pts["bottom_left"]

        top_w = max(1.0, float(np.hypot(tr.x - tl.x, tr.y - tl.y)))
        bottom_w = max(1.0, float(np.hypot(br.x - bl.x, br.y - bl.y)))
        left_h = max(1.0, float(np.hypot(bl.x - tl.x, bl.y - tl.y)))
        right_h = max(1.0, float(np.hypot(br.x - tr.x, br.y - tr.y)))
        width = int(round((top_w + bottom_w) / 2.0))
        height = int(round((left_h + right_h) / 2.0))

        src = np.array([
            [0.0, 0.0],
            [float(width), 0.0],
            [float(width), float(height)],
            [0.0, float(height)],
        ], dtype=np.float32)
        dst = np.array([
            [float(tl.x), float(tl.y)],
            [float(tr.x), float(tr.y)],
            [float(br.x), float(br.y)],
            [float(bl.x), float(bl.y)],
        ], dtype=np.float32)

        matrix = cv2.getPerspectiveTransform(src, dst)

        cal.write_area_x = int(min(tl.x, tr.x, br.x, bl.x))
        cal.write_area_y = int(min(tl.y, tr.y, br.y, bl.y))

        # Add a small buffer for OneNote rule lines if not set
        if cal.line_top_offset == 0:
            cal.line_top_offset = 2

        cal.write_area_width = width
        cal.write_area_height = height
        cal.transform_matrix = matrix.tolist()
        if cal.line_height_px <= 0:
            cal.line_height_px = 26

        save_calibration(cal)
        return {
            "computed": True,
            "line_height_px": cal.line_height_px,
            "write_area_width": cal.write_area_width,
            "write_area_height": cal.write_area_height,
        }

    # Backward compatibility: 2-point calibration (top_left + bottom_right)
    if "top_left" in pts and "bottom_right" in pts:
        tl = pts["top_left"]
        br = pts["bottom_right"]
        cal.write_area_x      = tl.x
        cal.write_area_y      = tl.y
        cal.write_area_width  = br.x - tl.x
        cal.write_area_height = br.y - tl.y
        cal.transform_matrix = []
        # Default line height for OneNote (configurable, ~26px is standard)
        if cal.line_height_px <= 0:
            cal.line_height_px = 26
        save_calibration(cal)
        return {"computed": True, "line_height_px": cal.line_height_px,
                "write_area_width": cal.write_area_width,
                "write_area_height": cal.write_area_height}

    missing = [r for r in required4 if r not in pts]
    if missing: raise HTTPException(400, f"Missing points: {missing}")
