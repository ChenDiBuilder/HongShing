import { useState } from "react";
import { api } from "../lib/api";
import { STATUS_COLORS, STATUS_LABEL, ORDER_FILTERS, timeAgo, formatOrderForCopy } from "../lib/types";

interface Props {
  orders: any[];
  activeFilter: string;
  onFilterChange: (key: string) => void;
  filterCounts: Record<string, number>;
}

export function OrdersDashboard({ orders, activeFilter, onFilterChange, filterCounts }: Props) {
  return (
    <main className="p-4">
      <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
        {ORDER_FILTERS.map((f) => {
          const isActive = activeFilter === f.key;
          const count = f.key !== "all" ? filterCounts[f.key] : 0;
          return (
            <button
              key={f.key}
              onClick={() => onFilterChange(f.key)}
              className={`flex-shrink-0 px-4 py-3 rounded-xl text-sm font-bold min-w-[44px] transition-colors ${isActive ? "bg-gray-900 text-white" : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"}`}>
              {f.label}
              {count > 0 && (
                <span className="ml-1.5 px-2 py-0.5 rounded-full text-xs bg-gray-200 text-gray-700">{count}</span>
              )}
            </button>
          );
        })}
      </div>

      {orders.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-5xl mb-3" aria-hidden="true">📋</p>
          <p className="text-xl font-bold text-gray-500" role="status">No active orders</p>
          <p className="text-base mt-1 text-gray-400">New orders will appear here automatically</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {orders.map((order: any) => (
            <OrderCard key={order.id} order={order} />
          ))}
        </div>
      )}
    </main>
  );
}

function OrderCard({ order }: { order: any }) {
  const [status, setStatus] = useState(order.status);
  const [copied, setCopied] = useState(false);

  async function updateStatus(newStatus: string) {
    try {
      const res = await fetch(api(`/api/storefront/orders/${order.id}/status`), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) setStatus(newStatus);
    } catch {}
  }

  function handleCopy() {
    navigator.clipboard.writeText(formatOrderForCopy({ ...order, status })).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {});
  }

  const statusBadge = (
    <span className={`text-base font-bold px-3 py-1.5 rounded-xl border min-w-[44px] text-center ${STATUS_COLORS[status] || "bg-gray-100"}`}>
      {STATUS_LABEL[status] || status}
    </span>
  );

  return (
    <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b flex items-center justify-between bg-gray-50/50">
        <div>
          <span className="font-mono text-lg font-bold text-gray-800">#{order.id.slice(0, 8)}</span>
          <p className="text-sm text-gray-500 mt-0.5">Placed {timeAgo(order.created_at)}</p>
        </div>
        {statusBadge}
      </div>

      {order.customer_name && (
        <div className="px-5 pt-3">
          <p className="text-base font-semibold text-gray-800">{order.customer_name}</p>
        </div>
      )}
      {order.customer_phone && (
        <div className="px-5 pb-1">
          <a href={`tel:${order.customer_phone}`} className="text-xl font-bold text-blue-600 hover:underline inline-block min-h-[44px] flex items-center">
            {order.customer_phone}
          </a>
        </div>
      )}

      <div className="px-5 py-3 space-y-2.5">
        {order.items?.map((item: any, i: number) => (
          <div key={i} className="flex justify-between text-base">
            <span className="font-medium text-gray-800">{item.quantity}x {item.name}</span>
            <span className="text-gray-500 ml-2">${(item.price_cents / 100).toFixed(2)}</span>
          </div>
        ))}
      </div>

      <div className="px-5 py-3 border-t bg-gray-50/50 flex justify-between text-lg font-bold">
        <span>Total ({order.item_count} items)</span>
        <span>${(order.total_cents / 100).toFixed(2)}</span>
      </div>

      <div className="px-5 py-3 border-t flex items-center gap-3 flex-wrap">
        {status === "confirmed" && (
          <>
            <button onClick={() => updateStatus("preparing")} className="min-h-[44px] px-5 py-2.5 bg-blue-600 text-white text-base font-bold rounded-xl active:scale-95 transition-transform">
              Start Preparing
            </button>
            <button onClick={() => updateStatus("cancelled")} className="min-h-[44px] px-4 py-2.5 bg-gray-100 text-gray-700 text-base font-medium rounded-xl active:scale-95 transition-transform">
              Cancel
            </button>
          </>
        )}
        {status === "preparing" && (
          <button onClick={() => updateStatus("ready")} className="min-h-[44px] px-5 py-2.5 bg-green-600 text-white text-base font-bold rounded-xl active:scale-95 transition-transform">
            Mark Ready
          </button>
        )}
        {status === "ready" && (
          <>
            <button onClick={() => updateStatus("picked_up")} className="min-h-[44px] px-5 py-2.5 bg-gray-700 text-white text-base font-bold rounded-xl active:scale-95 transition-transform">
              Picked Up
            </button>
            <button onClick={() => updateStatus("cancelled")} className="min-h-[44px] px-4 py-2.5 bg-gray-100 text-gray-700 text-base font-medium rounded-xl active:scale-95 transition-transform">
              Cancel
            </button>
          </>
        )}
        <button
          onClick={handleCopy}
          className={`min-h-[44px] px-4 py-2.5 rounded-xl text-base font-medium border active:scale-95 transition-all ${copied ? "bg-green-600 text-white border-green-600" : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"}`}>
          {copied ? "Copied!" : "Copy"}
        </button>
        <button
          onClick={() => window.print()}
          className="min-h-[44px] px-4 py-2.5 rounded-xl text-base font-medium border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 active:scale-95 transition-transform">
          Print
        </button>
      </div>
    </div>
  );
}
