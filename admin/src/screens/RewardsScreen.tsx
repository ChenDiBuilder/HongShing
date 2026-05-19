import { useState, useEffect } from "react";

interface RewardTemplate {
  id: string;
  name: string;
  reward_type: string;
  reward_value: number;
  valid_days: number;
  active: boolean;
}

interface Reward {
  id: string;
  code: string;
  status: string;
  source_code?: string;
  issued_at: string;
}

export default function RewardsScreen() {
  const [templates, setTemplates] = useState<RewardTemplate[]>([]);
  const [rewards, setRewards] = useState<Reward[]>([]);
  const [tab, setTab] = useState<"templates" | "issued">("templates");
  const [name, setName] = useState("");
  const [value, setValue] = useState(500);
  const [rewardType, setRewardType] = useState("fixed");
  const [validDays, setValidDays] = useState(30);

  useEffect(() => {
    fetch("/api/admin/reward-templates", { credentials: "include" })
      .then((r) => r.json())
      .then((d) => setTemplates(d.data || []));
    fetch("/api/admin/rewards", { credentials: "include" })
      .then((r) => r.json())
      .then((d) => setRewards(d.data || []));
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const params = new URLSearchParams({
      name,
      reward_type: rewardType,
      reward_value: String(value),
      valid_days: String(validDays),
    });
    await fetch(`/api/admin/reward-templates?${params}`, {
      method: "POST",
      credentials: "include",
    });
    setName("");
    const r = await fetch("/api/admin/reward-templates", { credentials: "include" });
    setTemplates((await r.json()).data || []);
  }

  async function handleRedeem(rewardId: string) {
    await fetch(`/api/admin/rewards/${rewardId}/redeem`, {
      method: "PATCH",
      credentials: "include",
    });
    const r = await fetch("/api/admin/rewards", { credentials: "include" });
    setRewards((await r.json()).data || []);
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Rewards</h1>

      <div className="flex gap-4 mb-6">
        <button
          onClick={() => setTab("templates")}
          className={`px-4 py-2 rounded-lg ${tab === "templates" ? "bg-red-600 text-white" : "bg-gray-200"}`}
        >
          Templates
        </button>
        <button
          onClick={() => setTab("issued")}
          className={`px-4 py-2 rounded-lg ${tab === "issued" ? "bg-red-600 text-white" : "bg-gray-200"}`}
        >
          Issued Codes
        </button>
      </div>

      {tab === "templates" && (
        <>
          <form onSubmit={handleCreate} className="bg-white rounded-xl shadow-sm p-6 mb-8 space-y-4">
            <h2 className="text-lg font-semibold">Create Template</h2>
            <div className="grid grid-cols-2 gap-4">
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Template name" className="px-3 py-2 border rounded-lg" required />
              <select value={rewardType} onChange={(e) => setRewardType(e.target.value)} className="px-3 py-2 border rounded-lg">
                <option value="fixed">Fixed ($)</option>
                <option value="percentage">Percentage (%)</option>
              </select>
              <input type="number" value={value} onChange={(e) => setValue(Number(e.target.value))} placeholder="Value (cents or %)" className="px-3 py-2 border rounded-lg" />
              <input type="number" value={validDays} onChange={(e) => setValidDays(Number(e.target.value))} placeholder="Valid days" className="px-3 py-2 border rounded-lg" />
            </div>
            <button type="submit" className="px-4 py-2 bg-red-600 text-white rounded-lg">Create</button>
          </form>

          <div className="bg-white rounded-xl shadow-sm">
            <table className="w-full">
              <thead><tr className="border-b text-left text-sm text-gray-500"><th className="p-4">Name</th><th className="p-4">Type</th><th className="p-4">Value</th><th className="p-4">Valid Days</th><th className="p-4">Active</th></tr></thead>
              <tbody>
                {templates.map((t) => (
                  <tr key={t.id} className="border-b">
                    <td className="p-4">{t.name}</td><td className="p-4">{t.reward_type}</td>
                    <td className="p-4">{t.reward_type === "fixed" ? `$${(t.reward_value / 100).toFixed(2)}` : `${t.reward_value}%`}</td>
                    <td className="p-4">{t.valid_days}</td><td className="p-4">{t.active ? "✅" : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {tab === "issued" && (
        <div className="bg-white rounded-xl shadow-sm">
          <table className="w-full">
            <thead><tr className="border-b text-left text-sm text-gray-500"><th className="p-4">Code</th><th className="p-4">Status</th><th className="p-4">Source</th><th className="p-4">Issued</th><th className="p-4">Action</th></tr></thead>
            <tbody>
              {rewards.map((r) => (
                <tr key={r.id} className="border-b">
                  <td className="p-4 font-mono">{r.code}</td><td className="p-4">{r.status}</td>
                  <td className="p-4 text-sm text-gray-600">{r.source_code || "-"}</td>
                  <td className="p-4 text-sm">{new Date(r.issued_at).toLocaleDateString()}</td>
                  <td className="p-4">
                    {r.status === "issued" && (
                      <button onClick={() => handleRedeem(r.id)} className="px-3 py-1 bg-green-600 text-white text-sm rounded">Redeem</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
