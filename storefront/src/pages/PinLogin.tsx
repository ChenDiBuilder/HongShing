import { useState } from "react";
import { api } from "../lib/api";

interface Props {
  onLogin: (device: { id: string; name: string; location?: string }) => void;
}

export function PinLogin({ onLogin }: Props) {
  const [pin, setPin] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (pin.length !== 4) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(api("/api/storefront/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ pin }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || "Invalid PIN");
      }
      const data = await res.json();
      onLogin(data.device);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900 p-4">
      <div className="w-full max-w-sm bg-gray-800 rounded-xl p-8 text-center">
        <h1 className="text-2xl font-bold text-white mb-2">Staff Login</h1>
        <p className="text-gray-400 text-sm mb-8">Storefront</p>
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Enter Device PIN</label>
            <input
              type="password"
              inputMode="numeric"
              maxLength={4}
              value={pin}
              onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 4))}
              className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white text-center text-2xl tracking-widest focus:outline-none focus:ring-2 focus:ring-red-500"
              placeholder="0000"
              autoFocus
            />
          </div>
          <button
            type="submit"
            disabled={loading || pin.length !== 4}
            className="w-full py-3 bg-red-600 text-white font-semibold rounded-lg disabled:opacity-50"
          >
            {loading ? "Connecting..." : "Connect"}
          </button>
        </form>
        {error && <p className="text-red-400 text-sm mt-4">{error}</p>}
        <p className="text-gray-500 text-xs mt-6 leading-relaxed">
          Create a device in the admin panel to get a PIN. Locking the device allows re-login with the same PIN.
        </p>
      </div>
    </div>
  );
}
