import { useState, useEffect } from "react";

const apiBase = import.meta.env.DEV ? "" : "/product-demo/hongshing";

interface Order {
  id: string;
  user_id: string;
  total_cents: number;
  item_count: number;
  status: string;
  created_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  confirmed: "bg-blue-100 text-blue-700",
  preparing: "bg-yellow-100 text-yellow-700",
  ready: "bg-green-100 text-green-700",
  picked_up: "bg-gray-100 text-gray-500",
  cancelled: "bg-red-100 text-red-500",
};

interface Props { statusFilter?: string; }

export default function OrdersScreen({ statusFilter: initial }: Props) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [statusFilter, setStatusFilter] = useState(initial || "");
  const [loading, setLoading] = useState(true);

  useEffect(() => { setStatusFilter(initial || ""); }, [initial]);

  async function load() {
    setLoading(true);
    const params = statusFilter ? `?status=${statusFilter}` : "";
    const r = await fetch(`${apiBase}/api/admin/orders${params}`, { credentials: "include" });
    const d = await r.json();
    setOrders(d.data?.items || []);
    setLoading(false);
  }

  useEffect(() => { load(); }, [statusFilter]);

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Orders</h1>

      <div className="flex gap-2 mb-6 flex-wrap">
        {["", "confirmed", "preparing", "ready", "picked_up", "cancelled"].map((s) => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-4 py-2 rounded-full text-sm font-medium ${statusFilter === s ? "bg-red-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
            {s || "All"}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {loading ? (
          <p className="text-center text-gray-400 py-12">Loading orders...</p>
        ) : orders.length === 0 ? (
          <p className="text-center text-gray-400 py-12">No orders found</p>
        ) : (
        <>
        {orders.map((o) => (
          <div key={o.id} className="bg-white rounded-xl shadow-sm p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-400 font-mono">#{o.id.slice(-8)}</span>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${STATUS_COLORS[o.status] || "bg-gray-100"}`}>
                {o.status}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">{o.item_count} items · ${(o.total_cents / 100).toFixed(2)}</span>
              <span className="text-xs text-gray-400">{new Date(o.created_at).toLocaleString()}</span>
            </div>
          </div>
        ))}
        </>
        )}
      </div>
    </div>
  );
}
