import { useState } from "react";
import { api } from "../context/api";
import { formatPrice } from "../types";

interface LandingPageProps {
  primaryColor: string;
  setPage: (p: any) => void;
  setProfile: (p: any) => void;
  loadCart: () => void;
  loadRewards: () => void;
  setPhone: (v: string) => void;
  phone: string;
  source?: string;
}

export function LandingPage({ primaryColor, setPage, setProfile: _setProfile, loadCart: _loadCart, loadRewards: _loadRewards, setPhone, phone, source }: LandingPageProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSendOTP(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await fetch(api("/api/auth/send-otp"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, source_code: source }),
      });
      setPage("otp");
    } catch { setError("Couldn't send code. Try again."); }
    finally { setLoading(false); }
  }

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <div className="flex-1 flex flex-col items-center justify-center px-4 pb-8">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-bold mb-1" style={{ color: primaryColor }}>Your Phone Number</h1>
          <p className="text-gray-500 text-sm mb-6 leading-relaxed">
            We'll use this to save your rewards, order history, and send pickup updates.
          </p>

          <form onSubmit={handleSendOTP} className="space-y-4">
            <input
              type="tel"
              placeholder="(647) 555-1234"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full px-4 py-4 border border-gray-300 rounded-xl text-center text-lg focus:outline-none focus:ring-2"
              style={{ "--tw-ring-color": primaryColor } as any}
            />
            <button
              type="submit"
              disabled={loading || !phone}
              className="w-full py-4 text-white font-semibold rounded-xl text-lg disabled:opacity-50 active:scale-[0.98] transition-transform"
              style={{ backgroundColor: primaryColor }}>
              {loading ? "Sending..." : "Send Code"}
            </button>
          </form>

          <p className="text-xs text-gray-400 mt-4 text-center leading-relaxed">
            By continuing, you agree to receive messages related to your rewards and orders.
            Message and data rates may apply.
          </p>

          {error && <p className="text-red-500 mt-4 text-sm text-center">{error}</p>}
        </div>
      </div>
    </div>
  );
}

export function OtpPage({ phone, setOtp, otp, loading, error, handleVerify, setPage, primaryColor }: any) {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <div className="flex-1 flex flex-col items-center justify-center px-4 pb-8">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-bold mb-1" style={{ color: primaryColor }}>Enter Your Code</h1>
          <p className="text-gray-500 text-sm mb-2">We sent a 6-digit code to {phone}</p>

          <div className="space-y-4">
            <input
              type="text" inputMode="numeric" maxLength={6}
              value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
              className="w-full px-4 py-4 border border-gray-300 rounded-xl text-center text-2xl tracking-[0.3em] focus:outline-none focus:ring-2"
              style={{ "--tw-ring-color": primaryColor } as any}
              placeholder="000000"
            />
            <button
              onClick={handleVerify}
              disabled={loading || otp.length !== 6}
              className="w-full py-4 text-white font-semibold rounded-xl text-lg disabled:opacity-50 active:scale-[0.98] transition-transform"
              style={{ backgroundColor: primaryColor }}>
              {loading ? "Verifying..." : "Verify"}
            </button>
            <button onClick={() => setPage("landing")}
              className="w-full py-2 text-sm text-gray-500 hover:underline">
              Back
            </button>
          </div>

          {error && <p className="text-red-500 mt-4 text-sm text-center">{error}</p>}
        </div>
      </div>
    </div>
  );
}

export function RewardPage({ rewardCode, setPage, primaryColor, rewardSuccessCopy, loadMenu, loadRewards, profile, handleLogout }: any) {
  const reward = profile?.rewards?.[0];

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <div className="flex-1 flex flex-col items-center justify-center px-4 pb-8">
        <div className="w-full max-w-sm text-center">
          <div className="text-5xl mb-4">🎉</div>
          <h1 className="text-2xl font-bold mb-2" style={{ color: primaryColor }}>Welcome back{profile?.name ? `, ${profile.name}` : ""}!</h1>
          <p className="text-gray-600 mb-6">{rewardSuccessCopy || "Your rewards and order history are ready."}</p>

          {reward ? (
            <div className="bg-gray-50 rounded-2xl p-5 mb-6 text-left">
              <p className="text-xs text-gray-400 uppercase tracking-wider font-semibold mb-1">Active Reward</p>
              <div className="flex items-center justify-between mb-2">
                <span className="text-2xl font-bold tracking-wider" style={{ color: primaryColor }}>{reward.code}</span>
                <span className={`text-xs font-semibold px-2 py-1 rounded-full ${reward.status === "issued" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                  {reward.status === "issued" ? "Ready" : reward.status}
                </span>
              </div>
              {reward.reward_value && (
                <p className="text-sm text-gray-600">Save {formatPrice(reward.reward_value)} on your next order</p>
              )}
              <p className="text-xs text-gray-400 mt-2">Show this code to staff when ordering</p>
            </div>
          ) : rewardCode ? (
            <div className="bg-gray-50 rounded-2xl px-6 py-5 mb-6">
              <p className="text-xs text-gray-400 uppercase tracking-wider font-semibold mb-1">Your Reward Code</p>
              <p className="text-3xl font-mono font-bold tracking-wider" style={{ color: primaryColor }}>{rewardCode}</p>
              <p className="text-xs text-gray-400 mt-2">Show this code to staff when ordering</p>
            </div>
          ) : (
            <p className="text-gray-400 text-sm mb-6">No active rewards yet. Order pickup to start earning!</p>
          )}

          <button onClick={() => { loadMenu(); setPage("menu"); }}
            className="w-full py-4 text-white font-bold rounded-xl text-lg mb-3 active:scale-[0.98] transition-transform"
            style={{ backgroundColor: primaryColor }}>
            Browse Menu
          </button>
          <button onClick={() => { loadRewards(); setPage("profile"); }}
            className="w-full py-4 font-bold rounded-xl text-lg border-2 mb-3 active:scale-[0.98] transition-transform"
            style={{ borderColor: primaryColor, color: primaryColor }}>
            View My Rewards
          </button>
          <button onClick={() => setPage("home")}
            className="w-full py-2 text-sm text-gray-500 hover:underline">
            Back to Home
          </button>
          {handleLogout && (
            <button onClick={handleLogout}
              className="w-full py-2 text-sm text-red-400 hover:text-red-600 hover:underline">
              Sign Out
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
