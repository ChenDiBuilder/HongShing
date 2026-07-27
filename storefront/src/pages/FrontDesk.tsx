import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";

type UsualItem = { name: string; quantity: number; ordered_in: number };
type LiveReward = { id: string; code: string; issued_at: string; expires_at: string | null };
type OrderRow = {
  id: string;
  status: string;
  total_cents: number;
  item_count: number;
  created_at: string;
};

type Lookup =
  | { found: false; phone_input: string; phone: string | null; reason?: string }
  | {
      found: true;
      phone_input: string;
      id: string;
      phone: string;
      name: string | null;
      email: string | null;
      customer_since: string;
      visits: number;
      total_spent_cents: number;
      last_order_at: string | null;
      usual: UsualItem[];
      rewards_live: LiveReward[];
      rewards_live_count: number;
      open_orders: OrderRow[];
      recent_orders: OrderRow[];
    };

const money = (cents: number) =>
  `$${(cents / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function sinceLabel(iso: string | null): string {
  if (!iso) return "—";
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  return months === 1 ? "a month ago" : `${months} months ago`;
}

function expiryLabel(iso: string | null): string {
  if (!iso) return "no expiry";
  const days = Math.ceil((new Date(iso).getTime() - Date.now()) / 86_400_000);
  if (days < 0) return "expired";
  if (days === 0) return "expires today";
  if (days === 1) return "1 day left";
  return `${days} days left`;
}

const prettyPhone = (e164: string | null) => {
  if (!e164) return "";
  const d = e164.replace(/\D/g, "").slice(-10);
  return d.length === 10 ? `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}` : e164;
};

export function FrontDesk() {
  const [digits, setDigits] = useState("");
  const [result, setResult] = useState<Lookup | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const lookup = useCallback(async (raw: string) => {
    if (raw.replace(/\D/g, "").length < 10) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        api(`/api/storefront/customer-lookup?phone=${encodeURIComponent(raw)}`),
        { credentials: "include" },
      );
      if (!res.ok) throw new Error(String(res.status));
      setResult((await res.json()).data as Lookup);
    } catch {
      setError("Couldn't reach the system. Check the connection and try again.");
      setResult(null);
    }
    setLoading(false);
  }, []);

  // Look up as soon as a full number is present — staff should never have to
  // find a button while someone is talking to them.
  useEffect(() => {
    const d = digits.replace(/\D/g, "");
    if (d.length === 10 || d.length === 11) {
      const t = setTimeout(() => lookup(digits), 150);
      return () => clearTimeout(t);
    }
    if (d.length === 0) setResult(null);
  }, [digits, lookup]);

  function clear() {
    setDigits("");
    setResult(null);
    setError(null);
    inputRef.current?.focus();
  }

  return (
    <div className="p-4 max-w-5xl mx-auto">
      {/* Lookup bar */}
      <div className="bg-white rounded-lg shadow p-4 mb-4">
        <label htmlFor="fd-phone" className="block text-sm font-medium text-gray-600 mb-2">
          Who's calling?
        </label>
        <div className="flex gap-2">
          <input
            id="fd-phone"
            ref={inputRef}
            value={digits}
            onChange={(e) => setDigits(e.target.value)}
            inputMode="tel"
            autoComplete="off"
            placeholder="416-977-3338"
            className="flex-1 min-h-[56px] px-4 text-2xl tracking-wide font-mono border-2 border-gray-300 rounded focus:border-gray-900 focus:outline-none"
          />
          <button
            onClick={clear}
            className="min-h-[56px] min-w-[88px] px-4 rounded border-2 border-gray-300 text-gray-600 hover:bg-gray-100 text-base"
          >
            Clear
          </button>
        </div>
        <p className="mt-2 text-xs text-gray-500">
          Type it however it's written down — we'll find them.
        </p>
      </div>

      {loading && <p className="text-gray-500 px-1">Looking up…</p>}
      {error && (
        <div className="bg-red-50 border border-red-300 text-red-800 rounded-lg p-4">{error}</div>
      )}

      {/* Unknown caller — the common case early on, and still useful */}
      {result && !result.found && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-baseline gap-3 flex-wrap">
            <h2 className="text-2xl font-bold text-gray-900">New caller</h2>
            {result.phone && (
              <span className="text-xl font-mono text-gray-700">{prettyPhone(result.phone)}</span>
            )}
          </div>
          <p className="mt-2 text-gray-600">
            {result.reason === "not_a_north_american_number"
              ? "That doesn't look like a 10-digit number — check the digits."
              : "First time we've seen this number. Take the order as usual; they'll be here next time."}
          </p>
        </div>
      )}

      {/* Known customer */}
      {result && result.found && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <div>
                <h2 className="text-3xl font-bold text-gray-900">
                  {result.name || "Customer"}
                </h2>
                <p className="text-lg font-mono text-gray-600 mt-1">
                  {prettyPhone(result.phone)}
                </p>
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold text-gray-900">{result.visits}</p>
                <p className="text-sm text-gray-500">
                  {result.visits === 1 ? "visit" : "visits"} · {money(result.total_spent_cents)}
                </p>
              </div>
            </div>
            <p className="mt-3 text-sm text-gray-500">
              Last order {sinceLabel(result.last_order_at)} · with us since{" "}
              {new Date(result.customer_since).toLocaleDateString(undefined, {
                month: "long",
                year: "numeric",
              })}
            </p>
          </div>

          {/* The usual — the line staff actually say out loud */}
          {result.usual.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-3">
                Usually orders
              </h3>
              <ul className="space-y-2">
                {result.usual.map((u) => (
                  <li key={u.name} className="flex items-baseline justify-between gap-4">
                    <span className="text-xl text-gray-900">{u.name}</span>
                    <span className="text-sm text-gray-500 whitespace-nowrap">
                      {u.ordered_in} of {result.visits} visits
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Live rewards — money they're about to be reminded of */}
          {result.rewards_live_count > 0 && (
            <div className="bg-amber-50 border-2 border-amber-300 rounded-lg p-6">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-amber-800 mb-3">
                Unused reward{result.rewards_live_count > 1 ? "s" : ""}
              </h3>
              {result.rewards_live.map((r) => (
                <div key={r.id} className="flex items-baseline justify-between gap-4">
                  <span className="text-2xl font-mono font-bold text-amber-900">{r.code}</span>
                  <span className="text-sm text-amber-800">{expiryLabel(r.expires_at)}</span>
                </div>
              ))}
              <p className="mt-3 text-sm text-amber-800">
                Mention it — it applies when they pick up.
              </p>
            </div>
          )}

          {/* On the pass right now */}
          {result.open_orders.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-3">
                Order in progress
              </h3>
              {result.open_orders.map((o) => (
                <div key={o.id} className="flex items-baseline justify-between gap-4">
                  <span className="text-xl text-gray-900 capitalize">{o.status}</span>
                  <span className="text-lg text-gray-700">
                    {o.item_count} {o.item_count === 1 ? "item" : "items"} · {money(o.total_cents)}
                  </span>
                </div>
              ))}
            </div>
          )}

          {result.recent_orders.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-3">
                Recent orders
              </h3>
              <ul className="divide-y divide-gray-100">
                {result.recent_orders.map((o) => (
                  <li key={o.id} className="flex items-baseline justify-between gap-4 py-2">
                    <span className="text-gray-700">
                      {new Date(o.created_at).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                      })}
                    </span>
                    <span className="text-gray-500 text-sm">
                      {o.item_count} {o.item_count === 1 ? "item" : "items"}
                    </span>
                    <span className="text-gray-900 font-medium">{money(o.total_cents)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
