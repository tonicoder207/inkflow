const LICENSE_SERVER = "http://localhost:8001";

export async function getDeviceId(): Promise<string> {
  let id = localStorage.getItem("inkflow_machine_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("inkflow_machine_id", id);
  }
  return id;
}

export async function activateLicense(key: string) {
  const device_id = await getDeviceId();
  try {
    const res = await fetch(`${LICENSE_SERVER}/activate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ license_key: key, device_id, device_name: "Desktop", platform: "windows" })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Error");
    return { status: "success", ...data };
  } catch (error: any) { return { status: "error", message: error.message }; }
}

export async function checkLicense(key: string) {
  const device_id = await getDeviceId();
  try {
    const res = await fetch(`${LICENSE_SERVER}/check`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ license_key: key, device_id })
    });
    return await res.json();
  } catch (e) { return { valid: false, reason: "Offline" }; }
}
