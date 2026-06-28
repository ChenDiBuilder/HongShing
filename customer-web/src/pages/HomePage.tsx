import { RESTAURANT_INFO } from "../types";

interface Props {
  primaryColor: string;
  logoUrl?: string;
  secondaryColor?: string;
  restaurantName?: string;
  campaign?: { landing_headline?: string; landing_subtitle?: string } | null;
  setPage: (p: any) => void;
  loadMenu: () => void;
  onClaimReward: () => void;
}

function todayHours() {
  const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const today = days[new Date().getDay()];
  return RESTAURANT_INFO.hours[today as keyof typeof RESTAURANT_INFO.hours] || "Hours unavailable";
}

export function HomePage({ primaryColor, logoUrl, secondaryColor, restaurantName, campaign, setPage, loadMenu, onClaimReward }: Props) {
  const headline = campaign?.landing_headline || "Order Pickup & Earn Rewards";
  const subtitle = campaign?.landing_subtitle || "Browse our menu, order ahead, and claim exclusive rewards.";
  const hasHours = Object.keys(RESTAURANT_INFO.hours).length > 0;
  // Secondary brand colour accents the secondary CTA; falls back to primary.
  const accent = secondaryColor || primaryColor;

  return (
    <div className="min-h-screen bg-white">
      <div className="flex flex-col items-center px-4 pb-8">
        {logoUrl && <img src={logoUrl} alt={restaurantName || "logo"} className="h-16 mt-8 mb-2" />}
        <h1 className="text-4xl font-extrabold text-center mt-6 mb-1 tracking-tight" style={{ color: primaryColor }}>
          {campaign ? headline : (restaurantName || "Welcome")}
        </h1>
        {!campaign && (
          <h1 className="text-4xl font-extrabold text-center mb-2 tracking-tight" style={{ color: primaryColor }}>
            Pickup & Rewards
          </h1>
        )}
        <p className="text-gray-600 text-center text-lg max-w-sm mb-8 leading-relaxed">
          {subtitle}
        </p>

        <div className="w-full max-w-sm space-y-3">
          <button onClick={() => { loadMenu(); setPage("menu"); }}
            className="w-full py-4 text-white font-bold rounded-xl text-lg shadow-lg active:scale-[0.98] transition-transform"
            style={{ backgroundColor: primaryColor }}>
            Order Pickup
          </button>
          <button onClick={() => { loadMenu(); setPage("menu"); }}
            className="w-full py-4 font-bold rounded-xl text-lg border-2 active:scale-[0.98] transition-transform"
            style={{ borderColor: accent, color: accent }}>
            View Menu
          </button>
          <button onClick={onClaimReward}
            className="w-full py-3 font-semibold rounded-xl text-base border border-gray-300 text-gray-700 active:scale-[0.98] transition-transform">
            Claim My Reward
          </button>
        </div>

        {(hasHours || RESTAURANT_INFO.address || RESTAURANT_INFO.phone) && (
          <div className="w-full max-w-sm mt-10 bg-gray-50 rounded-2xl p-5 space-y-3 text-sm">
            {hasHours && (
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Today's Hours</span>
                <span className={`font-semibold ${todayHours() === "Closed" ? "text-red-500" : "text-gray-800"}`}>
                  {todayHours()}
                </span>
              </div>
            )}
            {hasHours && (RESTAURANT_INFO.address || RESTAURANT_INFO.phone) && <hr className="border-gray-200" />}
            {RESTAURANT_INFO.address && <p className="text-gray-500 text-xs leading-relaxed">{RESTAURANT_INFO.address}</p>}
            {RESTAURANT_INFO.phone && (
              <a href={`tel:${RESTAURANT_INFO.phone}`}
                className="inline-block text-sm font-medium" style={{ color: primaryColor }}>
                {RESTAURANT_INFO.phone}
              </a>
            )}
          </div>
        )}

        <p className="mt-8 text-xs text-gray-400 text-center max-w-xs leading-relaxed">
          By using this site, you agree to receive order and reward updates. Message and data rates may apply.
        </p>
      </div>
    </div>
  );
}
