import { useState, useEffect } from "react";

const apiBase = import.meta.env.VITE_API_BASE ?? "";

interface Customer {
  id: string;
  phone?: string;
  name?: string;
  email?: string;
  created_at: string;
}

interface CustomerDetail {
  id: string;
  phone?: string;
  name?: string;
  email?: string;
  created_at: string;
  rewards: { id: string; code: string; status: string; issued_at: string }[];
  orders: { id: string; total_cents: number; item_count: number; status: string; created_at: string }[];
}

const STATUS_COLORS: Record<string, string> = {
  confirmed: "bg-blue-100 text-blue-700",
  preparing: "bg-yellow-100 text-yellow-700",
  ready: "bg-green-100 text-green-700",
  picked_up: "bg-gray-100 text-gray-500",
  cancelled: "bg-red-100 text-red-500",
};

interface Props { selectedCustomerId?: string | null; }

export default function CustomersScreen({ selectedCustomerId }: Props) {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<CustomerDetail | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    const params = search ? `?search=${encodeURIComponent(search)}` : "";
    const r = await fetch(`${apiBase}/api/admin/customers${params}`, { credentials: "include" });
    const d = await r.json();
    setCustomers(d.data?.items || []);
    setLoading(false);
  }

  async function viewCustomer(id: string) {
    const r = await fetch(`${apiBase}/api/admin/customers/${id}`, { credentials: "include" });
    const d = await r.json();
    setSelected(d.data);
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const r = await fetch(`${apiBase}/api/admin/customers`, { credentials: "include" });
      const d = await r.json();
      if (!cancelled) { setCustomers(d.data?.items || []); setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!selectedCustomerId) return;
    let cancelled = false;
    (async () => {
      const r = await fetch(`${apiBase}/api/admin/customers/${selectedCustomerId}`, { credentials: "include" });
      const d = await r.json();
      if (!cancelled) setSelected(d.data);
    })();
    return () => { cancelled = true; };
  }, [selectedCustomerId]);

  if (selected) {
    return (
      <div>
        <button onClick={() => setSelected(null)} className="text-sm text-red-600 hover:underline mb-4">← Back to Customers</button>
        <h1 className="text-2xl font-bold mb-4">{selected.name || selected.phone || "Customer"}</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="bg-white rounded-xl shadow-sm p-4">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Phone</p>
            <p className="font-mono">{selected.phone || "-"}</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-4">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Joined</p>
            <p>{new Date(selected.created_at).toLocaleDateString()}</p>
          </div>
        </div>

        <h2 className="text-lg font-bold mb-3">Orders ({selected.orders.length})</h2>
        <div className="space-y-2 mb-6">
          {selected.orders.map((o) => (
            <div key={o.id} className="bg-white rounded-xl shadow-sm p-3 flex items-center justify-between">
              <div><span className="text-sm font-mono text-gray-400">#{o.id.slice(-8)}</span><span className="text-sm ml-3">{o.item_count} items · ${(o.total_cents / 100).toFixed(2)}</span></div>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${STATUS_COLORS[o.status] || "bg-gray-100"}`}>{o.status}</span>
            </div>
          ))}
          {selected.orders.length === 0 && <p className="text-gray-400 text-sm">No orders</p>}
        </div>

        <h2 className="text-lg font-bold mb-3">Rewards ({selected.rewards.length})</h2>
        <div className="space-y-2">
          {selected.rewards.map((r) => (
            <div key={r.id} className="bg-white rounded-xl shadow-sm p-3 flex items-center justify-between">
              <span className="font-mono font-bold">{r.code}</span>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${r.status === "issued" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>{r.status}</span>
            </div>
          ))}
          {selected.rewards.length === 0 && <p className="text-gray-400 text-sm">No rewards</p>}
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Customers</h1>
      <div className="flex gap-4 mb-6">
        <input value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()}
          placeholder="Search by phone or name..." className="px-4 py-2 border rounded-lg flex-1" />
        <button onClick={load} className="px-4 py-2 bg-red-600 text-white rounded-lg">Search</button>
      </div>
      <div className="bg-white rounded-xl shadow-sm">
        {loading ? (
          <p className="text-center text-gray-400 py-12">Loading customers...</p>
        ) : customers.length === 0 ? (
          <p className="text-center text-gray-400 py-8">No customers found</p>
        ) : (
        <table className="w-full">
          <thead><tr className="border-b text-left text-sm text-gray-500"><th className="p-4">Phone</th><th className="p-4">Name</th><th className="p-4">Email</th><th className="p-4">Joined</th></tr></thead>
          <tbody>
            {customers.map((c) => (
              <tr key={c.id} onClick={() => viewCustomer(c.id)} className="border-b hover:bg-gray-50 cursor-pointer">
                <td className="p-4 font-mono">{c.phone || "-"}</td>
                <td className="p-4">{c.name || "-"}</td>
                <td className="p-4 text-sm text-gray-600">{c.email || "-"}</td>
                <td className="p-4 text-sm">{new Date(c.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        )}
      </div>
    </div>
  );
}
