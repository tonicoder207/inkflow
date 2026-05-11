import type { HandwritingProfile, ProfileSummary, RenderSettings, RenderResult,
  CalibrationProfile, WriteRequest, WriteStatus, CalibrationComputeResult } from "@/types";

let BASE = "http://127.0.0.1:8000/api";

// If running in Electron, try to get the real backend URL
if (typeof window !== "undefined" && (window as any).inkflow?.getBackendStatus) {
  (window as any).inkflow.getBackendStatus().then((status: any) => {
    if (status.url) {
      BASE = `${status.url}/api`;
      console.log("Backend URL updated from Electron:", BASE);
    }
  });
}

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...opts?.headers },
    ...opts,
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(e.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// Health
export const checkHealth = () => req<{status:string;version:string}>("/health");

// Profiles
export const listProfiles   = ()     => req<ProfileSummary[]>("/profiles/");
export const getProfile     = (id:string) => req<HandwritingProfile>(`/profiles/${id}`);
export const deleteProfile  = (id:string) => req(`/profiles/${id}`, { method:"DELETE" });
export async function createProfile(name: string): Promise<HandwritingProfile> {
  const fd = new FormData(); fd.append("name", name);
  const res = await fetch(`${BASE}/profiles/create`, { method:"POST", body:fd });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
export async function uploadCharacter(profileId:string, character:string, blob:Blob): Promise<void> {
  const fd = new FormData(); fd.append("character", character); fd.append("file", blob, "char.png");
  const res = await fetch(`${BASE}/profiles/${profileId}/upload-character`, { method:"POST", body:fd });
  if (!res.ok) throw new Error(await res.text());
}
export const updateProfileSettings = (id:string, s:Partial<HandwritingProfile>) =>
  req<HandwritingProfile>(`/profiles/${id}/settings`, { method:"PUT", body:JSON.stringify(s) });

// Render
export const renderText = (s:RenderSettings) =>
  req<RenderResult>("/render/", { method:"POST", body:JSON.stringify(s) });

// Export
export const exportRender = (rid:string, format:string, dpi=300) =>
  req<{download_url:string;filename:string;size_bytes:number}>(
    "/export/", { method:"POST", body:JSON.stringify({render_id:rid, format, dpi}) });

// Calibration
export const listCalibrations  = ()      => req<CalibrationProfile[]>("/calibration/");
export const getCalibration    = (id:string) => req<CalibrationProfile>(`/calibration/${id}`);
export const createCalibration = (c:CalibrationProfile) =>
  req<CalibrationProfile>("/calibration/create", { method:"POST", body:JSON.stringify(c) });
export const updateCalibration = (id:string, c:CalibrationProfile) =>
  req<CalibrationProfile>(`/calibration/${id}`, { method:"PUT", body:JSON.stringify(c) });
export const deleteCalibration = (id:string) => req(`/calibration/${id}`, { method:"DELETE" });
export const computeCalibration = (id:string) =>
  req<CalibrationComputeResult>(`/calibration/${id}/compute`, { method:"POST" });

// OneNote writing
export const startWrite  = (r:WriteRequest)  => req<WriteStatus>("/onenote/start",  { method:"POST", body:JSON.stringify(r) });
export const getWriteStatus = (id:string)    => req<WriteStatus>(`/onenote/status/${id}`);
export const pauseWrite  = (id:string)       => req(`/onenote/pause/${id}`,  { method:"POST" });
export const resumeWrite = (id:string)       => req(`/onenote/resume/${id}`, { method:"POST" });
export const cancelWrite = (id:string)       => req(`/onenote/cancel/${id}`, { method:"POST" });
