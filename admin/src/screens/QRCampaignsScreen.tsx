import { useState, useEffect } from "react";

interface QRCampaign {
  id: string;
  name: string;
  source_code: string;
  landing_headline?: string;
  active: boolean;
}

export default function QRCampaignsScreen() {
  const [campaigns, setCampaigns] = useState<QRCampaign[]>([]);
  const [name, setName] = useState("");
  const [sourceCode, setSourceCode] = useState("");
  const [headline, setHeadline] = useState("");

  useEffect(() => {
    fetch("/api/admin/qr-campaigns", { credentials: "include" })
      .then((r) => r.json())
      .then((d) => setCampaigns(d.data || []));
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const params = new URLSearchParams({ name, source_code: sourceCode });
    if (headline) params.append("landing_headline", headline);
    await fetch(`/api/admin/qr-campaigns?${params}`, {
      method: "POST",
      credentials: "include",
    });
    setName("");
    setSourceCode("");
    setHeadline("");
    // Refresh
    const r = await fetch("/api/admin/qr-campaigns", { credentials: "include" });
    const d = await r.json();
    setCampaigns(d.data || []);
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">QR Campaigns</h1>

      <form onSubmit={handleCreate} className="bg-white rounded-xl shadow-sm p-6 mb-8 space-y-4">
        <h2 className="text-lg font-semibold">Create Campaign</h2>
        <div className="grid grid-cols-2 gap-4">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Campaign name"
            className="px-3 py-2 border rounded-lg"
            required
          />
          <input
            value={sourceCode}
            onChange={(e) => setSourceCode(e.target.value)}
            placeholder="source_code (e.g. receipt)"
            className="px-3 py-2 border rounded-lg"
            required
          />
          <input
            value={headline}
            onChange={(e) => setHeadline(e.target.value)}
            placeholder="Landing headline"
            className="px-3 py-2 border rounded-lg col-span-2"
          />
        </div>
        <button type="submit" className="px-4 py-2 bg-red-600 text-white rounded-lg">
          Create
        </button>
      </form>

      <div className="bg-white rounded-xl shadow-sm">
        <table className="w-full">
          <thead>
            <tr className="border-b text-left text-sm text-gray-500">
              <th className="p-4">Name</th>
              <th className="p-4">Source Code</th>
              <th className="p-4">Headline</th>
              <th className="p-4">Active</th>
            </tr>
          </thead>
          <tbody>
            {campaigns.map((c) => (
              <tr key={c.id} className="border-b">
                <td className="p-4">{c.name}</td>
                <td className="p-4 font-mono text-sm">{c.source_code}</td>
                <td className="p-4 text-sm text-gray-600">{c.landing_headline || "-"}</td>
                <td className="p-4">{c.active ? "✅" : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
