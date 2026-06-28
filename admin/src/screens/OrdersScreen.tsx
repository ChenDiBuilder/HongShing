import { useState, useEffect } from "react";

const apiBase = import.meta.env.DEV ? "" : "/product-demo/hongshing";

interface OrderItem {
  name: string;
  price_cents: number;
  quantity: number;
}

interface Order {
  id: string;
  user_id: string;
  user_phone?: string;
  total_cents: number;
  item_count: number;
  status: string;
  items: OrderItem[];
  created_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  confirmed: "bg-blue-100 text-blue-700",
  preparing: "bg-yellow-100 text-yellow-700",
  ready: "bg-green-100 text-green-700",
  picked_up: "bg-gray-100 text-gray-500",
  cancelled: "bg-red-100 text-red-500",
};

interface Props {
  statusFilter?: string;
  onViewCustomer?: (id: string) => void;
}

export default function OrdersScreen({ statusFilter: initial, onViewCustomer }: Props) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [statusFilter, setStatusFilter] = useState(initial || "");
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => { setStatusFilter(initial || ""); }, [initial]);

  async function load() {
    setLoading(true);
    try {
      const params = statusFilter ? `?status=${statusFilter}` : "";
      const r = await fetch(`${apiBase}/api/admin/orders${params}`, { credentials: "include" });
      const d = await r.json();
      setOrders(d.data?.items || []);
    } catch {
      setOrders([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [statusFilter]);

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Orders</h1>

      <div className="flex gap-2 mb-6 flex-wrap">
        {["", "confirmed", "preparing", "ready", "picked_up", "cancelled"].map((s) => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${statusFilter === s ? "bg-red-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
            {s ? s.replace("_", " ") : "All"}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {loading ? (
          <p className="text-center text-gray-400 py-12">Loading orders...</p>
        ) : orders.length === 0 ? (
          <p className="text-center text-gray-400 py-12">No orders found</p>
        ) : (
          orders.map((o) => {
            const isExpanded = expandedId === o.id;
            return (
              <div key={o.id} className="bg-white rounded-xl shadow-sm overflow-hidden">
                <div
                  className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => setExpandedId(isExpanded ? null : o.id)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-gray-400 font-mono">#{o.id.slice(-8)}</span>
                      {o.user_phone && (
                        <button
                          onClick={(e) => { e.stopPropagation(); onViewCustomer?.(o.user_id); }}
                          className="text-xs text-red-600 hover:text-red-800 font-medium bg-red-50 px-2 py-0.5 rounded-full"
                        >
                          {o.user_phone}
                        </button>
                      )}
                    </div>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${STATUS_COLORS[o.status] || "bg-gray-100"}`}>
                      {o.status.replace("_", " ")}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-sm text-gray-600">{o.item_count} items · ${(o.total_cents / 100).toFixed(2)}</span>
                      {o.items.length > 0 && (
                        <span className="text-xs text-gray-400 ml-3 truncate max-w-xs inline-block align-bottom">
                          {o.items.map(i => `${i.quantity}x ${i.name}`).join(", ")}
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-gray-400">{new Date(o.created_at).toLocaleString()}</span>
                  </div>
                  <div className="mt-2 text-xs text-gray-400 flex items-center gap-1">
                    <svg className={`w-3 h-3 transition-transform ${isExpanded ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                    {isExpanded ? "Hide items" : o.items.length > 0 ? `${o.items.length} item types` : "View details"}
                  </div>
                </div>

                {isExpanded && (
                  <div className="border-t border-gray-100 px-4 py-3 bg-gray-50">
                    <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Order Items</h4>
                    <div className="space-y-2">
                      {o.items.length > 0 ? o.items.map((item, i) => (
                        <div key={i} className="flex justify-between text-sm">
                          <span className="text-gray-700">
                            <span className="font-medium text-gray-400 mr-2">{item.quantity}x</span>
                            {item.name}
                          </span>
                          <span className="text-gray-500">${((item.price_cents * item.quantity) / 100).toFixed(2)}</span>
                        </div>
                      )) : (
                        <p className="text-sm text-gray-400">No item details available</p>
                      )}
                    </div>
                    <div className="mt-3 pt-3 border-t border-gray-200 flex justify-between text-sm">
                      <span className="font-medium text-gray-700">Total</span>
                      <span className="font-bold text-gray-900">${(o.total_cents / 100).toFixed(2)}</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
