import os
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="InkFlow License API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
API_SECRET_KEY = os.getenv("API_SECRET_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# Models
class LicenseActivate(BaseModel):
    license_key: str
    device_id: str
    device_name: Optional[str] = "Unknown Device"
    platform: Optional[str] = "unknown"

class LicenseCheck(BaseModel):
    license_key: str
    device_id: str

class LicenseCreate(BaseModel):
    license_key: Optional[str] = None
    expires_at: Optional[datetime] = None
    max_devices: int = 1
    license_type: str = "standard"
    notes: Optional[str] = None

# Middleware for Admin API
async def verify_admin_token(authorization: str = Header(None)):
    if authorization != f"Bearer {API_SECRET_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/activate")
async def activate_license(data: LicenseActivate):
    if not supabase: raise HTTPException(status_code=500, detail="Backend not configured")
    res = supabase.table("licenses").select("*").eq("license_key", data.license_key).execute()
    if not res.data: raise HTTPException(status_code=404, detail="License key not found")
    license = res.data[0]
    if license["status"] != "active": raise HTTPException(status_code=400, detail=f"License is {license['status']}")
    if license["expires_at"] and datetime.fromisoformat(license["expires_at"].replace("Z", "+00:00")) < datetime.now(datetime.timezone.utc):
        raise HTTPException(status_code=400, detail="License has expired")
    dev_res = supabase.table("devices").select("*").eq("license_id", license["id"]).execute()
    existing_devices = dev_res.data
    is_already_registered = any(d["device_id"] == data.device_id for d in existing_devices)
    if not is_already_registered:
        if len(existing_devices) >= license["max_devices"]: raise HTTPException(status_code=400, detail="Maximum devices reached")
        supabase.table("devices").insert({"license_id": license["id"], "device_id": data.device_id, "device_name": data.device_name, "platform": data.platform}).execute()
    supabase.table("activations").insert({"license_id": license["id"], "device_id": data.device_id}).execute()
    return {"status": "success", "license_type": license["license_type"], "expires_at": license["expires_at"]}

@app.post("/check")
async def check_license(data: LicenseCheck):
    if not supabase: return {"valid": False, "reason": "Config Error"}
    res = supabase.table("licenses").select("*").eq("license_key", data.license_key).execute()
    if not res.data: return {"valid": False, "reason": "Not found"}
    license = res.data[0]
    if license["status"] != "active": return {"valid": False, "reason": "Inactive"}
    if license["expires_at"] and datetime.fromisoformat(license["expires_at"].replace("Z", "+00:00")) < datetime.now(datetime.timezone.utc):
        return {"valid": False, "reason": "Expired"}
    dev_res = supabase.table("devices").select("*").eq("license_id", license["id"]).eq("device_id", data.device_id).execute()
    if not dev_res.data: return {"valid": False, "reason": "Unauthorized Device"}
    supabase.table("devices").update({"last_seen": datetime.now().isoformat()}).eq("id", dev_res.data[0]["id"]).execute()
    return {"valid": True, "license_type": license["license_type"], "expires_at": license["expires_at"]}

@app.get("/admin/stats", dependencies=[Depends(verify_admin_token)])
async def get_stats():
    l_count = supabase.table("licenses").select("id", count="exact").execute().count
    d_count = supabase.table("devices").select("id", count="exact").execute().count
    a_count = supabase.table("activations").select("id", count="exact").execute().count
    return {"total_licenses": l_count, "total_devices": d_count, "total_activations": a_count}

@app.get("/admin/licenses", dependencies=[Depends(verify_admin_token)])
async def list_licenses():
    res = supabase.table("licenses").select("*, devices(*)").order("created_at", desc=True).execute()
    return res.data

@app.post("/admin/licenses", dependencies=[Depends(verify_admin_token)])
async def create_license(data: LicenseCreate):
    import secrets
    key = data.license_key or f"INK-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
    res = supabase.table("licenses").insert({"license_key": key, "expires_at": data.expires_at.isoformat() if data.expires_at else None, "max_devices": data.max_devices, "license_type": data.license_type, "notes": data.notes}).execute()
    return res.data[0]

class LicenseStatusUpdate(BaseModel):
    status: str

@app.put("/admin/licenses/{license_id}/status", dependencies=[Depends(verify_admin_token)])
async def update_license_status(license_id: str, data: LicenseStatusUpdate):
    res = supabase.table("licenses").update({"status": data.status}).eq("id", license_id).execute()
    return res.data[0] if res.data else {"error": "License not found"}

@app.delete("/admin/licenses/{license_id}", dependencies=[Depends(verify_admin_token)])
async def delete_license(license_id: str):
    res = supabase.table("licenses").delete().eq("id", license_id).execute()
    return {"status": "deleted"}

@app.get("/admin/devices", dependencies=[Depends(verify_admin_token)])
async def list_devices():
    res = supabase.table("devices").select("*, licenses(license_key, license_type)").order("created_at", desc=True).execute()
    return res.data

@app.delete("/admin/devices/{device_id}", dependencies=[Depends(verify_admin_token)])
async def delete_device(device_id: str):
    res = supabase.table("devices").delete().eq("id", device_id).execute()
    return {"status": "deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
