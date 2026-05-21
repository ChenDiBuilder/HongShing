import { useState, useEffect } from "react";
import QRCampaignsScreen from "./screens/QRCampaignsScreen";
import RewardsScreen from "./screens/RewardsScreen";
import CustomersScreen from "./screens/CustomersScreen";
import NotificationsScreen from "./screens/NotificationsScreen";
import SettingsScreen from "./screens/SettingsScreen";

type Page = "login" | "dashboard" | "qr-campaigns" | "rewards" | "customers" | "notifications" | "settings";

export default function App() {
  const [page, setPage] = useState<Page>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dashboard, setDashboard] = useState<any>(null);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/admin/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) throw new Error("Invalid credentials");
      setPage("dashboard");
      loadDashboard();
    } catch {
      setError("Invalid email or password");
    } finally {
      setLoading(false);
    }
  }

  async function loadDashboard() {
    try {
      const r = await fetch("/api/admin/dashboard", { credentials: "include" });
      const d = await r.json();
      setDashboard(d.data);
    } catch {}
  }

  useEffect(() => {
    if (page === "dashboard") loadDashboard();
  }, [page]);

  if (page === "login") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100 p-4">
        <div className="w-full max-w-sm bg-white rounded-xl shadow-md p-8">
          <h1 className="text-2xl font-bold text-center mb-8">HongShing Admin</h1>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500" required />
            </div>
            <button type="submit" disabled={loading} className="w-full py-2 bg-red-600 text-white font-semibold rounded-lg disabled:opacity-50">
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>
          {error && <p className="text-red-500 text-sm text-center mt-4">{error}</p>}
        </div>
      </div>
    );
  }

  const navItems: { key: Page; label: string }[] = [
    { key: "dashboard", label: "Dashboard" },
    { key: "customers", label: "Customers" },
    { key: "qr-campaigns", label: "QR Campaigns" },
    { key: "rewards", label: "Rewards" },
    { key: "notifications", label: "Notifications" },
    { key: "settings", label: "Settings" },
  ];

  const nav = (
    <aside className="w-64 bg-gray-900 text-white p-6 min-h-screen">
      <h2 className="text-xl font-bold mb-8">HongShing</h2>
      <nav className="space-y-1">
        {navItems.map((item) => (
          <button
            key={item.key}
            onClick={() => setPage(item.key)}
            className={`block w-full text-left py-2 px-3 rounded ${page === item.key ? "bg-gray-800" : "hover:bg-gray-800"}`}
          >
            {item.label}
          </button>
        ))}
      </nav>
      <button onClick={() => setPage("login")} className="mt-8 text-sm text-gray-400 hover:text-white">
        Sign Out
      </button>
    </aside>
  );

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {nav}
      <main className="flex-1 p-8">
        {page === "dashboard" && (
          <div>
            <h1 className="text-3xl font-bold mb-8">Dashboard</h1>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white rounded-xl shadow-sm p-6">
                <p className="text-sm text-gray-500">Total Customers</p>
                <p className="text-3xl font-bold mt-1">{dashboard?.total_customers ?? 0}</p>
              </div>
              <div className="bg-white rounded-xl shadow-sm p-6">
                <p className="text-sm text-gray-500">Active Campaigns</p>
                <p className="text-3xl font-bold mt-1">{dashboard?.active_campaigns ?? 0}</p>
              </div>
              <div className="bg-white rounded-xl shadow-sm p-6">
                <p className="text-sm text-gray-500">Rewards Issued</p>
                <p className="text-3xl font-bold mt-1">{dashboard?.issued_rewards ?? 0}</p>
              </div>
              <div className="bg-white rounded-xl shadow-sm p-6">
                <p className="text-sm text-gray-500">Total Signups</p>
                <p className="text-3xl font-bold mt-1">{dashboard?.total_signups ?? 0}</p>
              </div>
              <div className="bg-white rounded-xl shadow-sm p-6">
                <p className="text-sm text-gray-500">Rewards Redeemed</p>
                <p className="text-3xl font-bold mt-1">{dashboard?.redeemed_rewards ?? 0}</p>
              </div>
              <div className="bg-white rounded-xl shadow-sm p-6">
                <p className="text-sm text-gray-500">Total Rewards</p>
                <p className="text-3xl font-bold mt-1">{dashboard?.total_rewards ?? 0}</p>
              </div>
              <div className="bg-white rounded-xl shadow-sm p-6">
                <p className="text-sm text-gray-500">Total Orders</p>
                <p className="text-3xl font-bold mt-1">{dashboard?.total_orders ?? 0}</p>
              </div>
              <div className="bg-white rounded-xl shadow-sm p-6">
                <p className="text-sm text-gray-500">Pending Orders</p>
                <p className="text-3xl font-bold mt-1">{dashboard?.confirmed_orders ?? 0}</p>
              </div>
            </div>
          </div>
        )}
        {page === "customers" && <CustomersScreen />}
        {page === "qr-campaigns" && <QRCampaignsScreen />}
        {page === "rewards" && <RewardsScreen />}
        {page === "notifications" && <NotificationsScreen />}
        {page === "settings" && <SettingsScreen />}
      </main>
    </div>
  );
}
