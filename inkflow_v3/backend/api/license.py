import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from supabase import create_client, Client

router = APIRouter()

# Hier nutzen wir den ANON_KEY, der sicher im Build sein kann!
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY") # WICHTIG: Nur den Anon Key nutzen

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

class LicenseRequest(BaseModel):
    license_key: str
    device_id: str
    device_name: Optional[str] = "Unknown Device"
    platform: Optional[str] = "unknown"

@router.post("/activate")
async def activate(data: LicenseRequest):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    
    try:
        # Wir rufen die sichere RPC-Funktion auf dem Server auf
        res = supabase.rpc('activate_license_v2', {
            'input_key': data.license_key,
            'input_device_id': data.device_id,
            'input_device_name': data.device_name,
            'input_platform': data.platform
        }).execute()
        
        result = res.data
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/check")
async def check(data: LicenseRequest):
    if not supabase:
        return {"valid": False, "reason": "Config Error"}
    
    try:
        # Wir rufen die sichere Check-Funktion auf
        res = supabase.rpc('check_license_v2', {
            'input_key': data.license_key,
            'input_device_id': data.device_id
        }).execute()
        
        return res.data
    except Exception as e:
        return {"valid": False, "reason": str(e)}
