import { useState, useEffect, useCallback } from "react";

const apiBase = import.meta.env.DEV ? "" : "/product-demo/hongshing";

interface Device { id: string; name: string; location?: string; status: string; paired_at?: string; created_at: string; }

interface Props { showToast: (msg: string, type?: "success" | "error") => void; }

export default function DevicesScreen({ showToast }: Props) {
  const [devices, setDevices] = useState<Device[]>([]);
  const [name, setName] = useState(""); const [location, setLocation] = useState("");
  const [newDevice, setNewDevice] = useState<{ name: string; pin: string } | null>(null);
  const [error, setError] = useState("");

  const loadDevices = useCallback(async () => {
    const r = await fetch(`${apiBase}/api/admin/devices`, { credentials: "include" }); const d = await r.json(); setDevices(d.data || []);
  }, []);

  useEffect(() => { loadDevices(); }, [loadDevices]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault(); setError("");
    if (!name.trim()) { setError("Device name is required"); return; }
    try {
      const r = await fetch(`${apiBase}/api/admin/devices`, { method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify({ name: name.trim(), location: location.trim() || undefined }) });
      const d = await r.json();
      if (r.ok) {
      setNewDevice({ name: d.data.name, pin: d.data.pin });
      navigator.clipboard.writeText(d.data.pin).catch(() => {});
      setName(""); setLocation(""); loadDevices(); showToast(`Device created! PIN ${d.data.pin} copied`, "success");
    }
      else showToast(d.detail || "Failed to create device", "error");
    } catch { showToast("Failed to create device", "error"); }
  }

  async function handleDeactivate(id: string) {
    await fetch(`${apiBase}/api/admin/devices/${id}`, { method: "DELETE", credentials: "include" }); loadDevices(); showToast("Device deactivated", "success");
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Devices</h1>
      {newDevice && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-6 mb-6">
          <h3 className="text-lg font-semibold text-green-800 mb-2">Device Created — {newDevice.name}</h3>
          <p className="text-sm text-green-700 mb-2">Use this PIN on the storefront to connect. Locking will allow reuse.</p>
          <div className="bg-white rounded-lg px-4 py-3 inline-block"><span className="text-3xl font-mono font-bold tracking-widest text-gray-900">{newDevice.pin}</span></div>
          <button onClick={() => setNewDevice(null)} className="block mt-4 text-sm text-green-700 underline">Dismiss</button>
        </div>
      )}
      <form onSubmit={handleCreate} className="bg-white rounded-xl shadow-sm p-6 mb-8 space-y-4">
        <h2 className="text-lg font-semibold">Onboard New Device</h2>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Device Name *</label>
          <input value={name} onChange={e => setName(e.target.value)} placeholder="Kitchen Display" className="w-full px-3 py-2 border rounded-lg" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Location (optional)</label>
          <input value={location} onChange={e => setLocation(e.target.value)} placeholder="Kitchen" className="w-full px-3 py-2 border rounded-lg" />
        </div>
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <button type="submit" className="px-4 py-2 bg-red-600 text-white rounded-lg">Generate PIN & Create</button>
      </form>
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b"><tr><th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Name</th><th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Location</th><th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Status</th><th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Created</th><th className="text-right px-4 py-3 text-sm font-medium text-gray-500">Actions</th></tr></thead>
          <tbody>
            {devices.map(d => (
              <tr key={d.id} className="border-b last:border-0">
                <td className="px-4 py-3 font-medium">{d.name}</td><td className="px-4 py-3 text-sm text-gray-500">{d.location || "-"}</td>
                <td className="px-4 py-3"><span className={`text-xs font-medium px-2 py-1 rounded-full ${d.status === "paired" ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"}`}>{d.status}</span></td>
                <td className="px-4 py-3 text-sm text-gray-500">{d.created_at?.slice(0, 10)}</td>
                <td className="px-4 py-3 text-right"><button onClick={() => handleDeactivate(d.id)} className="text-sm text-red-600 hover:underline">Deactivate</button></td>
              </tr>
            ))}
            {devices.length === 0 && <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No devices yet — create one above</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
