import { useState, useEffect } from "react";
import { formatPrice, taxRate, RESTAURANT_INFO, type UserReward } from "../types";
import { useCart } from "../context/CartContext";
import { api } from "../context/api";

interface Props {
  primaryColor: string;
  profile?: any;
  rewards?: UserReward[];
  loadRewards?: () => void;
  setPage: (p: any) => void;
}

// Mirror of the backend reward_service.calculate_discount, for a live cart preview.
// The server re-computes authoritatively at checkout; this only previews the line.
export function estimateDiscount(reward: UserReward | undefined, subtotalCents: number): number {
  if (!reward) return 0;
  const v = reward.reward_value ?? 0;
  if (subtotalCents <= 0 || v <= 0) return 0;
  if (reward.reward_type === "percent" || reward.reward_type === "percentage") {
    return Math.min(Math.floor((subtotalCents * v) / 100), subtotalCents);
  }
  if (reward.reward_type === "fixed") return Math.min(v, subtotalCents);
  return 0;
}

function PlaceOrderButton({ primaryColor, profile, rewardId, onPlace }: { primaryColor: string; profile?: any; rewardId?: string; onPlace: () => void }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleClick() {
    if (!profile) {
      window.dispatchEvent(new CustomEvent("signin-required"));
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await fetch(api("/api/cart/checkout"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ reward_id: rewardId ?? null }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.detail || "Checkout failed");
      onPlace();
      window.dispatchEvent(new CustomEvent("order-placed", { detail: d }));
    } catch (e: any) { setError(e.message || "Couldn't place order. Try again."); }
    finally { setLoading(false); }
  }

  return (
    <div className="space-y-2">
      {error && <p className="text-red-500 text-sm text-center bg-red-50 rounded-xl py-2">{error}</p>}
      <button onClick={handleClick} disabled={loading}
        className="w-full py-4 text-white font-bold rounded-2xl text-lg active:scale-[0.98] transition-transform disabled:opacity-50"
        style={{ backgroundColor: primaryColor }}>
        {!profile ? "Sign in to Checkout" : loading ? "Placing order..." : "Place Order"}
      </button>
    </div>
  );
}

export function CartPage({ primaryColor, profile, rewards, loadRewards, setPage }: Props) {
  const cart = useCart();
  interface CartItemData { item: any; quantity: number; cartItemId?: string; }
  const [guestName, setGuestName] = useState("");
  const [guestPhone, setGuestPhone] = useState("");

  // Load rewards once so we can preview/apply a discount (PRD-12 / SCRUM-76).
  useEffect(() => {
    if (profile && loadRewards && !(rewards && rewards.length)) loadRewards();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile]);

  const activeReward = rewards?.find((r) => r.status === "issued");
  const discountCents = estimateDiscount(activeReward, cart.subtotalCents);
  const discounted = cart.subtotalCents - discountCents;

  const tr = taxRate();
  const subtotal = formatPrice(cart.subtotalCents);
  const tax = formatPrice(Math.round(discounted * tr));
  const total = formatPrice(discounted + Math.round(discounted * tr));

  if (cart.items.length === 0) {
    return (
      <div className="text-center py-20 text-gray-400">
        <p className="text-4xl mb-3">🛒</p>
        <p className="text-lg font-medium mb-4">Your cart is empty</p>
        <button onClick={() => setPage("menu")}
          className="px-6 py-3 text-white font-semibold rounded-xl" style={{ backgroundColor: primaryColor }}>
          Browse Menu
        </button>
      </div>
    );
  }

  return (
    <div className="pb-32">
      <button onClick={() => setPage("menu")} className="text-sm text-gray-500 mb-4 hover:underline">← Continue Shopping</button>
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Your Order</h1>
      <div className="flex items-center justify-between mb-5">
        <p className="text-sm text-gray-500">{RESTAURANT_INFO.address ? `Pickup at ${RESTAURANT_INFO.address.split(",")[0]}` : "Pickup order"}</p>
        <button onClick={() => cart.clearCart()} className="text-sm text-red-500 hover:underline">Clear All</button>
      </div>

      <div className="space-y-3 mb-6">
        {cart.items.map((ci: CartItemData) => (
          <div key={ci.item.id} className="flex items-center gap-3 bg-white rounded-2xl p-3 shadow-sm border border-gray-100">
            <div className="w-12 h-12 bg-gray-100 rounded-xl flex-shrink-0 flex items-center justify-center text-lg">
              {ci.item.image_url ? <img src={ci.item.image_url} alt="" className="w-full h-full object-cover rounded-xl" /> : "🍽️"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-sm text-gray-800 truncate">{ci.item.name}</p>
              <p className="text-xs font-medium" style={{ color: primaryColor }}>{formatPrice(ci.item.price_cents)}</p>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => cart.updateQuantity(ci.item.id, ci.quantity - 1)}
                className="w-8 h-8 rounded-lg border border-gray-200 text-gray-500 font-bold text-sm">−</button>
              <span className="text-sm font-bold w-5 text-center">{ci.quantity}</span>
              <button onClick={() => cart.updateQuantity(ci.item.id, ci.quantity + 1)}
                className="w-8 h-8 rounded-lg border border-gray-200 text-gray-500 font-bold text-sm">+</button>
              <button onClick={() => cart.removeItem(ci.item.id)}
                className="w-8 h-8 rounded-lg text-red-400 hover:text-red-600 font-bold text-sm ml-1">✕</button>
            </div>
          </div>
        ))}
      </div>

      {!profile && (
        <div className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100 mb-4 space-y-3">
          <p className="text-sm font-semibold text-gray-700">Your Info</p>
          <input type="text" placeholder="Your name" value={guestName} onChange={(e) => setGuestName(e.target.value)}
            className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm" />
          <input type="tel" placeholder="Phone number" value={guestPhone} onChange={(e) => setGuestPhone(e.target.value)}
            className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm" />
        </div>
      )}

      <div className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100 space-y-2 mb-6">
        <div className="flex justify-between text-sm"><span className="text-gray-500">Subtotal</span><span className="font-medium">{subtotal}</span></div>
        {discountCents > 0 && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Reward{activeReward?.code ? ` (${activeReward.code})` : ""}</span>
            <span className="font-medium text-green-600">−{formatPrice(discountCents)}</span>
          </div>
        )}
        <div className="flex justify-between text-sm"><span className="text-gray-500">Tax (est.)</span><span className="font-medium">{tax}</span></div>
        <hr className="border-gray-100" />
        <div className="flex justify-between text-base"><span className="font-bold">Total</span><span className="font-bold" style={{ color: primaryColor }}>{total}</span></div>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 mb-6">
        <div className="flex items-center justify-between text-sm">
          <span className="text-amber-800 font-medium">Pickup at the restaurant</span>
          {RESTAURANT_INFO.pickupEstimate && <span className="text-amber-700">Ready in {RESTAURANT_INFO.pickupEstimate}</span>}
        </div>
        <p className="text-xs text-amber-600 mt-1">Pay at pickup{RESTAURANT_INFO.address ? ` · ${RESTAURANT_INFO.address}` : ""}</p>
      </div>

      <div className="fixed bottom-0 left-0 right-0 px-3 pb-4 bg-white/80 backdrop-blur">
        <div className="max-w-3xl mx-auto space-y-2">
          <PlaceOrderButton primaryColor={primaryColor} profile={profile} rewardId={activeReward?.id} onPlace={() => cart.clearCart()} />
        </div>
      </div>
    </div>
  );
}
