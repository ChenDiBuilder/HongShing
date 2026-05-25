import { useState, useEffect } from "react";
import { formatPrice, RESTAURANT_INFO } from "../types";
import { api } from "../context/api";
import { useCart } from "../context/CartContext";

interface OrderConfirmationProps {
  order: any;
  primaryColor: string;
  setPage: (p: any) => void;
  loadMenu: () => void;
}

export function OrderConfirmation({ order, primaryColor, setPage, loadMenu }: OrderConfirmationProps) {
  const [status, setStatus] = useState(order?.status || "confirmed");
  const orderId = order?.order_id;

  useEffect(() => {
    if (!orderId) return;
    const timer = setInterval(async () => {
      try {
        const r = await fetch(api(`/api/customer/me/orders/${orderId}`), { credentials: "include" });
        const d = await r.json();
        if (d.order?.status) setStatus(d.order.status);
      } catch {}
    }, 10000);
    return () => clearInterval(timer);
  }, [orderId]);

  const statusText: Record<string, string> = {
    confirmed: "Order received! We're preparing your food.",
    preparing: "Your order is being prepared.",
    ready: "Your order is ready for pickup!",
    picked_up: "Order picked up. Enjoy!",
    cancelled: "This order was cancelled.",
  };

  const statusIcon: Record<string, string> = {
    confirmed: "✅",
    preparing: "👨‍🍳",
    ready: "🥡",
    picked_up: "🏠",
    cancelled: "❌",
  };

  return (
    <div className="text-center pb-8">
      <div className="text-5xl mb-4">{statusIcon[status] || "✅"}</div>
      <h1 className="text-2xl font-bold text-gray-800 mb-2">{statusText[status]}</h1>
      {status === "ready" && (
        <p className="text-lg font-bold mb-1" style={{ color: primaryColor }}>Come to the counter!</p>
      )}
      <p className="text-gray-500 text-sm mb-6">Order #{orderId?.slice(-8) || ""}</p>

      {order?.items && (
        <div className="text-left bg-white rounded-2xl p-4 shadow-sm border border-gray-100 mb-4 max-w-sm mx-auto">
          <p className="text-xs text-gray-400 uppercase tracking-wide font-semibold mb-2">Your Items</p>
          {order.items.map((i: any, idx: number) => (
            <div key={idx} className="flex justify-between text-sm py-1">
              <span>{i.quantity}x {i.name}</span>
              <span className="text-gray-500">{formatPrice(i.price_cents * i.quantity)}</span>
            </div>
          ))}
          <hr className="border-gray-100 my-2" />
          <div className="flex justify-between font-bold">
            <span>Total</span><span style={{ color: primaryColor }}>{formatPrice(order.total_cents)}</span>
          </div>
        </div>
      )}

      <div className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100 mb-6 max-w-sm mx-auto text-left text-sm space-y-2">
        <div className="flex justify-between"><span className="text-gray-400">Pickup at</span><span className="font-medium">{RESTAURANT_INFO.address}</span></div>
        <div className="flex justify-between"><span className="text-gray-400">Est. ready</span><span className="font-medium">{RESTAURANT_INFO.pickupEstimate}</span></div>
        <div className="flex justify-between"><span className="text-gray-400">Payment</span><span className="font-medium">Pay at pickup</span></div>
      </div>

      <div className="space-y-2 max-w-sm mx-auto">
        <button onClick={() => { setPage("menu"); loadMenu(); }}
          className="w-full py-4 text-white font-bold rounded-2xl text-lg active:scale-[0.98] transition-transform"
          style={{ backgroundColor: primaryColor }}>Order Again</button>
        <button onClick={() => setPage("profile")}
          className="w-full py-3 font-semibold rounded-2xl border-2 text-lg active:scale-[0.98] transition-transform"
          style={{ borderColor: primaryColor, color: primaryColor }}>View Rewards</button>
      </div>

      <p className="text-xs text-gray-400 mt-6">We'll text you updates at your phone number</p>
    </div>
  );
}

interface OrderTrackingProps {
  orders: any[];
  setPage: (p: any) => void;
  loadMenu: () => void;
  primaryColor: string;
}

export function OrderTracking({ orders, setPage, loadMenu, primaryColor }: OrderTrackingProps) {
  const cart = useCart();
  const statusColors: Record<string, string> = {
    confirmed: "bg-blue-100 text-blue-700",
    preparing: "bg-yellow-100 text-yellow-700",
    ready: "bg-green-100 text-green-700",
    picked_up: "bg-gray-100 text-gray-500",
    cancelled: "bg-red-100 text-red-500",
  };

  function handleReorder(order: any) {
    for (const item of (order.items || [])) {
      for (let i = 0; i < item.quantity; i++) {
        cart.addItem({ id: item.menu_item_id || item.id, category_id: "", name: item.name, description: null, price_cents: item.price_cents, image_url: null, tags: [] });
      }
    }
    setPage("cart");
  }

  if (orders.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <p className="text-4xl mb-3">📋</p>
        <p className="text-lg font-medium mb-4">No orders yet</p>
        <button onClick={() => { setPage("menu"); loadMenu(); }}
          className="px-6 py-3 text-white font-semibold rounded-xl" style={{ backgroundColor: primaryColor }}>
          Browse Menu
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3 pb-4">
      <h1 className="text-xl font-bold text-gray-800 mb-3">My Orders</h1>
      {orders.map((o: any) => (
        <div key={o.id} className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-400">#{o.id.slice(-8)}</span>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${statusColors[o.status] || "bg-gray-100"}`}>{o.status}</span>
          </div>
          {o.items?.map((i: any, idx: number) => (
            <div key={idx} className="flex justify-between text-sm py-0.5">
              <span>{i.quantity}x {i.name}</span>
              <span className="text-gray-500">{formatPrice(i.price_cents * i.quantity)}</span>
            </div>
          ))}
          <div className="flex justify-between text-sm font-bold mt-2 pt-2 border-t border-gray-50">
            <span>Total</span><span style={{ color: primaryColor }}>{formatPrice(o.total_cents)}</span>
          </div>
          <p className="text-xs text-gray-400 mt-1">{new Date(o.created_at).toLocaleDateString()}</p>
          <button onClick={() => handleReorder(o)}
            className="mt-2 px-4 py-2 text-sm font-semibold border-2 rounded-xl active:scale-95 transition-transform"
            style={{ borderColor: primaryColor, color: primaryColor }}>
            Reorder
          </button>
        </div>
      ))}
    </div>
  );
}

interface ProfileRewardsProps {
  rewards: any[];
  primaryColor: string;
  setPage: (p: any) => void;
  loadRewards: () => void;
}

export function ProfileRewards({ rewards, primaryColor, setPage, loadRewards }: ProfileRewardsProps) {
  const totalCount = rewards.length;

  return (
    <div className="space-y-3 pb-4">
      <div className="flex items-center justify-between mb-3">
        <h1 className="text-xl font-bold text-gray-800">My Rewards</h1>
        <button onClick={loadRewards} className="text-sm font-medium" style={{ color: primaryColor }}>Refresh</button>
      </div>

      <div className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100 mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-500">Loyalty Progress</span>
          <span className="text-sm font-semibold">{totalCount} orders</span>
        </div>
        <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden mb-2">
          <div className="h-full rounded-full transition-all" style={{
            width: `${Math.min(100, totalCount * (100 / 3))}%`,
            backgroundColor: primaryColor,
          }} />
        </div>
        {totalCount < 3 ? (
          <p className="text-xs text-gray-400 mt-1">Order pickup {3 - totalCount} more {3 - totalCount === 1 ? "time" : "times"} to earn a $5 reward</p>
        ) : (
          <p className="text-xs text-green-600 font-medium mt-1">You've earned a reward! Check below.</p>
        )}
      </div>

      {rewards.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <p className="text-4xl mb-3">🎁</p>
          <p className="text-lg font-medium mb-1">No rewards yet</p>
          <p className="text-sm">Order pickup 3 times to earn your first $5 reward!</p>
        </div>
      ) : (
        rewards.map((r: any) => (
          <div key={r.id} className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-400">{new Date(r.issued_at).toLocaleDateString()}</span>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${r.status === "issued" ? "bg-green-100 text-green-700" : r.status === "redeemed" ? "bg-gray-100 text-gray-500" : "bg-red-100 text-red-500"}`}>
                {r.status}
              </span>
            </div>
            <p className="text-2xl font-mono font-bold tracking-wider" style={{ color: primaryColor }}>{r.code}</p>
            {r.reward_value && (
              <p className="text-sm text-gray-600 mt-1">${(r.reward_value / 100).toFixed(2)} off your order</p>
            )}
            {r.expires_at && <p className="text-xs text-gray-400 mt-1">Expires {new Date(r.expires_at).toLocaleDateString()}</p>}
            {r.status === "issued" && (
              <button onClick={() => alert("Show this code to staff: " + r.code)}
                className="mt-3 px-4 py-2 text-sm font-semibold text-white rounded-xl active:scale-95 transition-transform"
                style={{ backgroundColor: primaryColor }}>
                Show to Staff
              </button>
            )}
          </div>
        ))
      )}

      <div className="pt-4">
        <button onClick={() => setPage("menu")}
          className="w-full py-4 text-white font-bold rounded-2xl text-lg active:scale-[0.98] transition-transform"
          style={{ backgroundColor: primaryColor }}>
          Order Pickup
        </button>
      </div>
    </div>
  );
}
