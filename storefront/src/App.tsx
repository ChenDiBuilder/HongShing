import { useState, useEffect, useCallback, useMemo } from "react";
import { api } from "./lib/api";
import type { StorefrontOrder, StorefrontReservation } from "./lib/types";
import { PinLogin } from "./pages/PinLogin";
import { OrdersDashboard } from "./pages/OrdersDashboard";
import { ReservationsView } from "./pages/ReservationsView";
import { FrontDesk } from "./pages/FrontDesk";

type Page = "login" | "frontdesk" | "orders" | "reservations";

export default function App() {
  const [page, setPage] = useState<Page>("login");
  const [device, setDevice] = useState<{ id: string; name: string; location?: string } | null>(null);
  const [orders, setOrders] = useState<StorefrontOrder[]>([]);
  const [reservations, setReservations] = useState<StorefrontReservation[]>([]);
  const [orderFilter, setOrderFilter] = useState("confirmed");
  const [refetchKey, setRefetchKey] = useState(0);
  const [restoring, setRestoring] = useState(true);

  useEffect(() => {
    async function restoreSession() {
      try {
        const res = await fetch(api("/api/storefront/orders"), { credentials: "include" });
        if (res.ok) {
          const data = await res.json();
          setOrders(data.orders || []);
          setPage("orders");
        }
      } catch { /* best-effort — no valid session, stay on the PIN screen */ }
      setRestoring(false);
    }
    restoreSession();
  }, []);

  const loadOrders = useCallback(async () => {
    try {
      const res = await fetch(api("/api/storefront/orders"), { credentials: "include" });
      const data = await res.json();
      setOrders(data.orders || []);
    } catch { /* best-effort — keep the last loaded orders on fetch failure */ }
  }, []);

  const loadReservations = useCallback(async () => {
    const today = new Date().toISOString().slice(0, 10);
    try {
      const res = await fetch(api(`/api/storefront/reservations?reservation_date=${today}`), { credentials: "include" });
      const data = await res.json();
      setReservations(data.reservations || []);
    } catch { /* best-effort — keep the last loaded reservations on fetch failure */ }
  }, []);

  useEffect(() => {
    if (page !== "orders") return;
    let cancelled = false;
    const tick = async () => { if (!cancelled) await loadOrders(); };
    void tick();
    const interval = setInterval(() => { void tick(); }, 8000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [page, loadOrders, refetchKey]);

  useEffect(() => {
    if (page !== "reservations") return;
    let cancelled = false;
    const tick = async () => { if (!cancelled) await loadReservations(); };
    void tick();
    return () => { cancelled = true; };
  }, [page, loadReservations, refetchKey]);

  function handleLogin(deviceData: { id: string; name: string; location?: string }) {
    setDevice(deviceData);
    setPage("orders");
  }

  async function handleLock() {
    await fetch(api("/api/storefront/auth/logout"), { method: "POST", credentials: "include" });
    setPage("login");
    setDevice(null);
  }

  const filteredOrders = useMemo(() => {
    if (orderFilter === "all") return orders;
    return orders.filter(o => o.status === orderFilter);
  }, [orders, orderFilter]);

  const filterCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const o of orders) {
      counts[o.status] = (counts[o.status] || 0) + 1;
    }
    return counts;
  }, [orders]);

  if (page === "login") {
    if (restoring) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-900">
          <p className="text-gray-400 text-lg">Checking session...</p>
        </div>
      );
    }
    return <PinLogin onLogin={handleLogin} />;
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-gray-900 text-white px-4 py-3">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h1 className="text-lg font-bold">{device?.name || "Storefront"}</h1>
            {device?.location && <p className="text-xs text-gray-400">{device.location}</p>}
          </div>
          <button
            onClick={handleLock}
            title="Lock this device and return to PIN screen"
            className="min-h-[44px] min-w-[44px] flex items-center gap-2 px-3 py-2 rounded text-sm text-gray-400 hover:bg-gray-800 hover:text-white transition-colors">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="Lock device">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7a5 5 0 0110 0v4"/>
            </svg>
            Lock
          </button>
        </div>
        <nav className="flex gap-2">
          <button
            onClick={() => setPage("frontdesk")}
            className={`min-h-[44px] px-4 py-2 rounded-lg text-base font-medium transition-colors ${page === "frontdesk" ? "bg-gray-700 text-white" : "text-gray-400 hover:text-white hover:bg-gray-800"}`}>
            Front Desk
          </button>
          <button
            onClick={() => { setPage("orders"); loadOrders(); }}
            className={`min-h-[44px] px-4 py-2 rounded-lg text-base font-medium transition-colors ${page === "orders" ? "bg-gray-700 text-white" : "text-gray-400 hover:text-white hover:bg-gray-800"}`}>
            Orders
            {orders.length > 0 && (
              <span className="ml-1.5 px-2 py-0.5 rounded-full text-xs bg-red-600 text-white">{orders.length}</span>
            )}
          </button>
          <button
            onClick={() => { setPage("reservations"); loadReservations(); }}
            className={`min-h-[44px] px-4 py-2 rounded-lg text-base font-medium transition-colors ${page === "reservations" ? "bg-gray-700 text-white" : "text-gray-400 hover:text-white hover:bg-gray-800"}`}>
            Reservations
          </button>
        </nav>
      </header>

      {page === "frontdesk" && <FrontDesk />}

      {page === "orders" && (
        <OrdersDashboard
          orders={filteredOrders}
          activeFilter={orderFilter}
          onFilterChange={setOrderFilter}
          filterCounts={filterCounts}
        />
      )}
      {page === "reservations" && (
        <ReservationsView
          reservations={reservations}
          onUpdate={() => setRefetchKey(k => k + 1)}
        />
      )}
    </div>
  );
}
