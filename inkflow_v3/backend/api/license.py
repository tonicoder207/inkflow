"""InkFlow v3 — License API (no supabase SDK needed)"""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

class LicenseRequest(BaseModel):
    license_key: str
    device_id: str
    device_name: Optional[str] = "Unknown Device"
    platform: Optional[str] = "unknown"


def _headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def _rpc(func_name: str, payload: dict):
    """Call a Supabase RPC function using only the standard library."""
    import urllib.request, urllib.error, json
    url = f"{SUPABASE_URL}/rest/v1/rpc/{func_name}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=_headers(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise HTTPException(status_code=e.code, detail=body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/activate")
async def activate(data: LicenseRequest):
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    result = _rpc("activate_license_v2", {
        "input_key": data.license_key,
        "input_device_id": data.device_id,
        "input_device_name": data.device_name,
        "input_platform": data.platform,
    })

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Activation failed"))

    return result


@router.post("/check")
async def check(data: LicenseRequest):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"valid": False, "reason": "Config Error"}

    try:
        result = _rpc("check_license_v2", {
            "input_key": data.license_key,
            "input_device_id": data.device_id,
        })
        return result
    except Exception as e:
        return {"valid": False, "reason": str(e)}
