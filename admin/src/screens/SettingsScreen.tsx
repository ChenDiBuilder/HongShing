import { useState, useEffect } from "react";

const apiBase = import.meta.env.VITE_API_BASE ?? "";

interface Props { showToast: (msg: string, type?: "success" | "error") => void; }

interface Settings {
  restaurant_name?: string;
  primary_color?: string;
  logo_url?: string;
  external_ordering_url?: string;
  external_ordering_provider?: string;
  privacy_contact_email?: string;
  support_phone?: string;
}

export default function SettingsScreen({ showToast }: Props) {
  const [settings, setSettings] = useState<Settings>({});
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch(`${apiBase}/api/admin/settings`, { credentials: "include" })
      .then((r) => r.json())
      .then((d) => setSettings(d.data || {}));
  }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaved(false);
    const params = new URLSearchParams();
    if (settings.restaurant_name) params.append("restaurant_name", settings.restaurant_name);
    if (settings.primary_color) params.append("primary_color", settings.primary_color);
    if (settings.external_ordering_url) params.append("external_ordering_url", settings.external_ordering_url);
    if (settings.external_ordering_provider) params.append("external_ordering_provider", settings.external_ordering_provider);
    if (settings.privacy_contact_email) params.append("privacy_contact_email", settings.privacy_contact_email);
    if (settings.support_phone) params.append("support_phone", settings.support_phone);

    const r = await fetch(`${apiBase}/api/admin/settings?${params}`, {
      method: "PATCH",
      credentials: "include",
    });
    if (r.ok) { setSaved(true); showToast("Settings saved!", "success"); }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Settings</h1>

      <form onSubmit={handleSave} className="bg-white rounded-xl shadow-sm p-6 space-y-4 max-w-2xl">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Restaurant Name</label>
          <input value={settings.restaurant_name || ""} onChange={(e) => setSettings({ ...settings, restaurant_name: e.target.value })} className="w-full px-3 py-2 border rounded-lg" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Primary Color</label>
          <input value={settings.primary_color || ""} onChange={(e) => setSettings({ ...settings, primary_color: e.target.value })} className="w-full px-3 py-2 border rounded-lg" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Logo</label>
          {settings.logo_url ? (
            <div className="flex items-center gap-3">
              <img src={settings.logo_url} alt="Restaurant logo" className="h-12 w-auto border rounded" />
              <span className="text-xs text-gray-500 break-all">{settings.logo_url}</span>
            </div>
          ) : (
            <p className="text-sm text-gray-400">No logo configured (set via the restaurant profile at provisioning).</p>
          )}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">External Ordering URL</label>
          <input value={settings.external_ordering_url || ""} onChange={(e) => setSettings({ ...settings, external_ordering_url: e.target.value })} placeholder="https://..." className="w-full px-3 py-2 border rounded-lg" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Ordering Provider</label>
          <select value={settings.external_ordering_provider || ""} onChange={(e) => setSettings({ ...settings, external_ordering_provider: e.target.value })} className="w-full px-3 py-2 border rounded-lg">
            <option value="">None</option>
            <option value="toast">Toast</option>
            <option value="square">Square</option>
            <option value="custom">Custom</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Privacy Contact Email</label>
          <input value={settings.privacy_contact_email || ""} onChange={(e) => setSettings({ ...settings, privacy_contact_email: e.target.value })} className="w-full px-3 py-2 border rounded-lg" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Support Phone</label>
          <input value={settings.support_phone || ""} onChange={(e) => setSettings({ ...settings, support_phone: e.target.value })} className="w-full px-3 py-2 border rounded-lg" />
        </div>
        <button type="submit" className="px-4 py-2 bg-red-600 text-white rounded-lg">Save</button>
        {saved && <span className="text-green-600 ml-4">Saved!</span>}
      </form>
    </div>
  );
}
