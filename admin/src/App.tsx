import { useState, useEffect, useCallback } from "react";
import DecisionsScreen from "./screens/DecisionsScreen";
import QRCampaignsScreen from "./screens/QRCampaignsScreen";
import RewardsScreen from "./screens/RewardsScreen";
import CustomersScreen from "./screens/CustomersScreen";
import SettingsScreen from "./screens/SettingsScreen";
import DevicesScreen from "./screens/DevicesScreen";
import ReservationSlotsScreen from "./screens/ReservationSlotsScreen";
import OrdersScreen from "./screens/OrdersScreen";
import { AnalyticsPanel, type AnalyticsData } from "./components/AnalyticsPanel";

type Page = "login" | "change-password" | "dashboard" | "decisions" | "qr-campaigns" | "rewards" | "customers" | "orders" | "settings" | "devices" | "reservation-slots";

interface DashboardData { scans_today: number; signups_today: number; redirects_today: number; sms_opt_in_rate: number; }

const apiBase = import.meta.env.VITE_API_BASE ?? "";

function Toast({ message, type, onDismiss }: { message: string; type: "success" | "error"; onDismiss: () => void }) {
  useEffect(() => { const t = setTimeout(onDismiss, 3000); return () => clearTimeout(t); }, [onDismiss]);
  return (
    <div className={`fixed top-4 right-4 z-50 px-5 py-3 rounded-xl shadow-lg text-sm font-medium animate-[fadeIn_0.2s_ease-out] ${type === "success" ? "bg-green-600 text-white" : "bg-red-600 text-white"}`}>
      {message}
    </div>
  );
}

function MetricCard({ label, value, onClick }: { label: string; value: string | number; onClick?: () => void }) {
  return (
    <div onClick={onClick} className={`bg-white rounded-xl shadow-sm p-6 ${onClick ? "cursor-pointer hover:shadow-md hover:-translate-y-0.5 transition-all" : ""}`}>
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-3xl font-bold mt-1">{value}</p>
      {onClick && <p className="text-xs text-red-500 mt-1 opacity-0 group-hover:opacity-100 hover:opacity-100">View →</p>}
    </div>
  );
}

function Spinner({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="text-center">
        <div className="w-10 h-10 border-4 border-red-200 border-t-red-600 rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm text-gray-400">{label}</p>
      </div>
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState<Page>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [dateRange, setDateRange] = useState("14");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [ordersFilter, setOrdersFilter] = useState("");
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);
  const [restoring, setRestoring] = useState(true);

  // A dev-server reload (or a plain refresh) shouldn't dump an authed session
  // back at the login form — the cookie is still valid; use it.
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${apiBase}/api/admin/dashboard`, { credentials: "include" });
        if (r.ok) setPage("dashboard");
      } catch { /* not signed in — stay on login */ }
      setRestoring(false);
    })();
  }, []);

  const showToast = useCallback((message: string, type: "success" | "error" = "success") => { setToast({ message, type }); }, []);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault(); setLoading(true); setError("");
    try {
      const res = await fetch(`${apiBase}/api/admin/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify({ email, password }) });
      if (!res.ok) throw new Error("Invalid credentials");
      const data = await res.json().catch(() => ({}));
      if (data.must_change_password) { setPage("change-password"); return; }
      setPage("dashboard"); loadDashboard(); loadAnalytics();
    } catch { setError("Invalid email or password"); }
    finally { setLoading(false); }
  }

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault(); setLoading(true); setError("");
    try {
      const res = await fetch(`${apiBase}/api/admin/auth/change-password`, { method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify({ current_password: password, new_password: newPassword }) });
      if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.detail || "Could not change password"); }
      setPassword(""); setNewPassword("");
      setPage("dashboard"); loadDashboard(); loadAnalytics();
    } catch (err) { setError(err instanceof Error ? err.message : "Could not change password"); }
    finally { setLoading(false); }
  }

  async function handleLogout() {
    try { await fetch(`${apiBase}/api/admin/auth/logout`, { method: "POST", credentials: "include" }); } catch { /* best-effort — sign out locally regardless */ }
    setEmail(""); setPassword(""); setNewPassword(""); setPage("login");
  }

  const loadDashboard = useCallback(async () => {
    try { const r = await fetch(`${apiBase}/api/admin/dashboard`, { credentials: "include" }); const d = await r.json(); setDashboard(d.data); } catch { /* best-effort — errors surface via empty UI state */ }
  }, []);

  const loadAnalytics = useCallback(async () => {
    try { const r = await fetch(`${apiBase}/api/admin/analytics?days=${dateRange}`, { credentials: "include" }); const d = await r.json(); setAnalytics(d.data); } catch { /* best-effort — errors surface via empty UI state */ }
  }, [dateRange]);

  useEffect(() => { if (page === "dashboard") { loadDashboard(); loadAnalytics(); } }, [page, loadDashboard, loadAnalytics]);

  // SCRUM-237: the fixed sidebar ate ~55% of a phone screen; below lg it becomes
  // a top bar + slide-over drawer. Drawer closes on any navigation.
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  function navigateTo(key: Page, filter?: string) {
    setPage(key);
    setMobileNavOpen(false);
    if (key === "orders" && filter) setOrdersFilter(filter);
    if (key === "customers" && filter) setSelectedCustomerId(filter);
  }

  function handleViewCustomer(customerId: string) {
    setSelectedCustomerId(customerId);
    setPage("customers");
  }

  if (page === "login") {
    if (restoring) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-100">
          <Spinner label="Checking session..." />
        </div>
      );
    }
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100 p-4">
        <div className="w-full max-w-sm bg-white rounded-xl shadow-md p-8">
          <h1 className="text-2xl font-bold text-center mb-8">Admin</h1>
          <form onSubmit={handleLogin} className="space-y-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Email</label><input type="email" value={email} onChange={e => setEmail(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500" required /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Password</label><input type="password" value={password} onChange={e => setPassword(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500" required /></div>
            <button type="submit" disabled={loading} className="w-full py-2 bg-red-600 text-white font-semibold rounded-lg disabled:opacity-50">{loading ? "Signing in..." : "Sign In"}</button>
          </form>
          {error && <p className="text-red-500 text-sm text-center mt-4">{error}</p>}
        </div>
      </div>
    );
  }

  if (page === "change-password") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100 p-4">
        <div className="w-full max-w-sm bg-white rounded-xl shadow-md p-8">
          <h1 className="text-2xl font-bold text-center mb-2">Set a new password</h1>
          <p className="text-sm text-gray-500 text-center mb-6">Your account is using a temporary password. Choose a new one to continue.</p>
          <form onSubmit={handleChangePassword} className="space-y-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">New password</label><input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} minLength={8} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500" required /></div>
            <button type="submit" disabled={loading} className="w-full py-2 bg-red-600 text-white font-semibold rounded-lg disabled:opacity-50">{loading ? "Saving..." : "Set password"}</button>
          </form>
          {error && <p className="text-red-500 text-sm text-center mt-4">{error}</p>}
        </div>
      </div>
    );
  }

  const navItems: { key: Page; label: string }[] = [
    { key: "dashboard", label: "Dashboard" },
    { key: "decisions", label: "This Week" },
    { key: "customers", label: "Customer Profiles" },
    { key: "orders", label: "Order History" },
    { key: "qr-campaigns", label: "QR & Campaigns" },
    { key: "rewards", label: "Loyalty Rewards" },
    { key: "devices", label: "Devices & Kiosks" },
    { key: "reservation-slots", label: "Reservation Slots" },
    { key: "settings", label: "Restaurant Settings" },
  ];

  const navContent = (
    <>
      <h2 className="text-xl font-bold mb-8">Admin</h2>
      <nav className="space-y-1 flex-1">
        {navItems.map(item => (
          <button key={item.key} onClick={() => navigateTo(item.key)} className={`block w-full text-left py-2 px-3 rounded text-sm ${page === item.key ? "bg-gray-800 font-medium" : "hover:bg-gray-800 text-gray-300"}`}>{item.label}</button>
        ))}
      </nav>
      <button onClick={handleLogout} className="text-sm text-gray-500 hover:text-white text-left">Sign Out</button>
    </>
  );

  return (
    <div className="min-h-screen bg-gray-50 lg:flex">
      {/* Mobile top bar (hidden on lg+) */}
      <header className="lg:hidden sticky top-0 z-40 bg-gray-900 text-white flex items-center gap-3 px-4 py-3">
        <button onClick={() => setMobileNavOpen(true)} aria-label="Open navigation" className="p-1 -ml-1">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M4 6h16M4 12h16M4 18h16" /></svg>
        </button>
        <h2 className="text-lg font-bold">Admin</h2>
        <span className="ml-auto text-sm text-gray-400">{navItems.find(i => i.key === page)?.label ?? ""}</span>
      </header>

      {/* Mobile slide-over drawer */}
      {mobileNavOpen && (
        <div className="lg:hidden fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileNavOpen(false)} aria-hidden="true" />
          <aside className="absolute left-0 top-0 bottom-0 w-64 bg-gray-900 text-white p-6 flex flex-col shadow-xl">
            {navContent}
          </aside>
        </div>
      )}

      {/* Desktop sidebar (unchanged look, hidden below lg) */}
      <aside className="hidden lg:flex w-64 bg-gray-900 text-white p-6 min-h-screen flex-col">
        {navContent}
      </aside>

      <main className="flex-1 p-4 lg:p-8">
        {page === "dashboard" && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h1 className="text-3xl font-bold">Dashboard</h1>
              <select
                value={dateRange}
                onChange={(e) => setDateRange(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-red-500">
                <option value="7">Last 7 days</option>
                <option value="14">Last 14 days</option>
                <option value="30">Last 30 days</option>
                <option value="90">Last 90 days</option>
              </select>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
              <MetricCard label="Scans Today" value={dashboard?.scans_today ?? 0} />
              <MetricCard label="Signups Today" value={dashboard?.signups_today ?? 0} />
              <MetricCard label="Redirects Today" value={dashboard?.redirects_today ?? 0} />
              <MetricCard label="Orders Today" value={analytics?.summary?.today?.orders ?? 0} />
              <MetricCard label="Revenue Today" value={`$${((analytics?.summary?.today?.revenue_cents ?? 0) / 100).toFixed(2)}`} />
              <MetricCard label="SMS Opt-in" value={`${dashboard?.sms_opt_in_rate ?? 0}%`} />
            </div>

            {!analytics ? (
              <div className="mt-10"><Spinner label="Loading analytics..." /></div>
            ) : (
              <AnalyticsPanel data={analytics} />
            )}
          </div>
        )}
        {page === "decisions" && <DecisionsScreen showToast={showToast} />}
        {page === "customers" && <CustomersScreen selectedCustomerId={selectedCustomerId} />}
        {page === "orders" && <OrdersScreen statusFilter={ordersFilter} onViewCustomer={handleViewCustomer} />}
        {page === "qr-campaigns" && <QRCampaignsScreen showToast={showToast} />}
        {page === "rewards" && <RewardsScreen showToast={showToast} />}
        {page === "devices" && <DevicesScreen showToast={showToast} />}
        {page === "reservation-slots" && <ReservationSlotsScreen showToast={showToast} />}
        {page === "settings" && <SettingsScreen showToast={showToast} />}
      </main>
      {toast && <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />}
    </div>
  );
}
