import { useState, useEffect, useCallback } from "react";
import QRCode from "qrcode";

const apiBase = import.meta.env.DEV ? "" : "/product-demo/hongshing";

interface QRCampaign { id: string; name: string; source_code: string; landing_headline?: string; active: boolean; }

// Customer signup SPA is served at the root of this same host (admin lives at
// /admin/), so derive the landing URL from the current origin — works on the
// demo domain and a customer's own domain alike.
const CUSTOMER_WEB_URL = `${window.location.origin}/`;
function getLandingUrl(sourceCode: string) { return `${CUSTOMER_WEB_URL}?source=${encodeURIComponent(sourceCode)}`; }

function QRCodes({ campaigns }: { campaigns: QRCampaign[] }) {
  return <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">{campaigns.map(c => <QRCodeCard key={c.id} campaign={c} />)}</div>;
}

function QRCodeCard({ campaign }: { campaign: QRCampaign }) {
  const canvasRef = React.useRef<HTMLCanvasElement>(null);
  const url = getLandingUrl(campaign.source_code);
  React.useEffect(() => { if (canvasRef.current) QRCode.toCanvas(canvasRef.current, url, { width: 240, margin: 2, color: { dark: "#000000", light: "#ffffff" } }); }, [url]);
  return (
    <div className="bg-white rounded-xl shadow-sm p-6 flex flex-col items-center text-center">
      <canvas ref={canvasRef} className="rounded-lg border border-gray-100" />
      <h3 className="font-semibold mt-3">{campaign.name}</h3>
      <code className="text-xs text-gray-500 mt-1 bg-gray-50 px-2 py-0.5 rounded font-mono">{campaign.source_code}</code>
      <p className="text-[11px] text-gray-400 mt-2 break-all leading-tight px-2">{url}</p>
      <button onClick={() => { if (canvasRef.current) { const a = document.createElement("a"); a.href = canvasRef.current.toDataURL("image/png"); a.download = `qr-${campaign.source_code}.png`; a.click(); } }} className="mt-3 px-4 py-1.5 bg-red-600 text-white text-sm rounded-lg">Download PNG</button>
    </div>
  );
}

import React from "react";

interface Props { showToast: (msg: string, type?: "success" | "error") => void; }

export default function QRCampaignsScreen({ showToast }: Props) {
  const [campaigns, setCampaigns] = useState<QRCampaign[]>([]);
  const [name, setName] = useState(""); const [sourceCode, setSourceCode] = useState(""); const [headline, setHeadline] = useState("");
  const [generating, setGenerating] = useState(false);

  const loadCampaigns = useCallback(async () => {
    try { const r = await fetch(`${apiBase}/api/admin/qr-campaigns`, { credentials: "include" }); const d = await r.json(); setCampaigns(d.data || []); } catch {}
  }, []);

  useEffect(() => { loadCampaigns(); }, [loadCampaigns]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault(); setGenerating(true);
    try {
      const r = await fetch(`${apiBase}/api/admin/qr-campaigns`, { method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify({ name: name.trim(), source_code: sourceCode.trim(), landing_headline: headline.trim() || undefined }) });
      if (r.ok) { setName(""); setSourceCode(""); setHeadline(""); await loadCampaigns(); showToast("Campaign created!", "success"); }
      else { const d = await r.json().catch(() => ({})); showToast(d.detail || "Failed to create campaign", "error"); }
    } catch { showToast("Failed to create campaign", "error"); }
    finally { setGenerating(false); }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">QR Campaigns</h1>
      <form onSubmit={handleCreate} className="bg-white rounded-xl shadow-sm p-6 mb-8 space-y-4">
        <h2 className="text-lg font-semibold">Create Campaign</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <input value={name} onChange={e => setName(e.target.value)} placeholder="Campaign name (e.g. Receipt QR)" className="px-3 py-2 border rounded-lg" required />
          <input value={sourceCode} onChange={e => setSourceCode(e.target.value)} placeholder="Source code (e.g. receipt)" className="px-3 py-2 border rounded-lg font-mono text-sm" required />
          <input value={headline} onChange={e => setHeadline(e.target.value)} placeholder="Headline (optional)" className="px-3 py-2 border rounded-lg" />
        </div>
        <button type="submit" disabled={generating} className="px-6 py-2 bg-red-600 text-white rounded-lg font-medium disabled:opacity-50">{generating ? "Creating..." : "Create Campaign + Generate QR"}</button>
      </form>
      {campaigns.length === 0 ? <div className="bg-white rounded-xl shadow-sm p-12 text-center text-gray-400"><p className="text-lg mb-2">No campaigns yet</p><p className="text-sm">Create one above to generate a QR code.</p></div> : <QRCodes campaigns={campaigns} />}
    </div>
  );
}
