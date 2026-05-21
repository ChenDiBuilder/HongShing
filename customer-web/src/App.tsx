import { useState, useEffect, useRef, createContext } from "react";

// ------------------ Types ------------------
type Page = "landing" | "otp" | "reward" | "profile" | "menu" | "product-detail" | "cart" | "order-confirmation" | "terms" | "privacy";

interface LandingConfig {
  restaurant_name: string;
  primary_color: string;
  campaign?: { id: string; source_code: string; landing_headline?: string; landing_subtitle?: string };
  allow_order_without_signup: boolean;
  external_ordering_url?: string;
}

interface UserReward {
  id: string;
  code: string;
  status: string;
  issued_at: string;
  expires_at?: string;
}

interface MenuItemType {
  id: string;
  category_id: string;
  name: string;
  description: string | null;
  price_cents: number;
  image_url: string | null;
}

interface CartItem {
  item: MenuItemType;
  quantity: number;
}

interface CartContextType {
  items: CartItem[];
  addItem: (item: MenuItemType) => void;
  removeItem: (itemId: string) => void;
  updateQuantity: (itemId: string, qty: number) => void;
  clearCart: () => void;
  subtotalCents: number;
  itemCount: number;
}

const CartContext = createContext<CartContextType>({
  items: [],
  addItem: () => {},
  removeItem: () => {},
  updateQuantity: () => {},
  clearCart: () => {},
  subtotalCents: 0,
  itemCount: 0,
});

// ------------------ Utility ------------------
const apiBase = import.meta.env.DEV ? "" : "/product-demo/hongshing";
function api(path: string) { return `${apiBase}${path}`; }

function formatPrice(cents: number) {
  return `$${(cents / 100).toFixed(2)}`;
}

const CATEGORY_EMOJI: Record<string, string> = {
  "new-dishes": "🆕",
  "starters": "🍗",
  "soup": "🍜",
  "seafood": "🦞",
  "poultry": "🍗",
  "beef": "🥩",
  "vegetables": "🥬",
  "noodles": "🍝",
  "rice": "🍚",
  "refreshments": "🥤",
  "dim-sum": "🥟",
  "additional-sauces": "🫙",
};

function categoryEmoji(slug: string) {
  return CATEGORY_EMOJI[slug] || "🍽️";
}

// ------------------ App ------------------
export default function App() {
  const [page, setPage] = useState<Page>("landing");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [rewardCode, setRewardCode] = useState("");
  const [rewardLink, setRewardLink] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [profile, setProfile] = useState<any>(null);
  const [rewards, setRewards] = useState<UserReward[]>([]);
  const [config, setConfig] = useState<LandingConfig>({
    restaurant_name: "Hong Shing",
    primary_color: "#C41E3A",
    allow_order_without_signup: true,
  });
  const [menu, setMenu] = useState<{ id: string; name: string; slug: string; image_url: string | null; items: MenuItemType[] }[]>([]);
  const [activeCategory, setActiveCategory] = useState<string>("");
  const [selectedProduct, setSelectedProduct] = useState<MenuItemType | null>(null);
  const [orderConfirmation, setOrderConfirmation] = useState<{ order_id: string; total_cents: number; item_count: number } | null>(null);

  // Cart state
  const [cartItems, setCartItems] = useState<CartItem[]>([]);

  const subtotalCents = cartItems.reduce((sum, ci) => sum + ci.item.price_cents * ci.quantity, 0);
  const itemCount = cartItems.reduce((sum, ci) => sum + ci.quantity, 0);

  function addItem(item: MenuItemType) {
    setCartItems((prev) => {
      const existing = prev.find((ci) => ci.item.id === item.id);
      if (existing) {
        return prev.map((ci) => (ci.item.id === item.id ? { ...ci, quantity: ci.quantity + 1 } : ci));
      }
      return [...prev, { item, quantity: 1 }];
    });
  }

  function removeItem(itemId: string) {
    setCartItems((prev) => prev.filter((ci) => ci.item.id !== itemId));
  }

  function updateQuantity(itemId: string, qty: number) {
    if (qty <= 0) {
      removeItem(itemId);
      return;
    }
    setCartItems((prev) => prev.map((ci) => (ci.item.id === itemId ? { ...ci, quantity: qty } : ci)));
  }

  function clearCart() {
    setCartItems([]);
  }

  const cartContext: CartContextType = { items: cartItems, addItem, removeItem, updateQuantity, clearCart, subtotalCents, itemCount };

  const params = new URLSearchParams(window.location.search);
  const source = params.get("source") || "";

  useEffect(() => {
    fetch(api(`/api/public/landing-config?source=${source}`))
      .then((r) => r.json())
      .then((d) => setConfig(d))
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetch(api("/api/customer/me"), { credentials: "include" })
      .then((r) => {
        if (r.ok) return r.json();
        throw new Error("not logged in");
      })
      .then((user) => {
        setProfile(user);
        loadRewards();
        setPage("profile");
      })
      .catch(() => {});
  }, []);

  async function loadRewards() {
    try {
      const r = await fetch(api("/api/customer/me/rewards"), { credentials: "include" });
      if (r.ok) {
        const d = await r.json();
        setRewards(d.data || []);
      }
    } catch {}
  }

  async function loadMenu() {
    try {
      const r = await fetch(api("/api/menu/full"));
      if (r.ok) {
        const data = await r.json();
        setMenu(data);
        if (data.length > 0) setActiveCategory(data[0].slug);
      }
    } catch {}
  }

  async function handleSendOTP(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetch(api("/api/auth/send-otp"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, source_code: source || undefined }),
      });
      if (!res.ok) throw new Error("Failed to send code");
      setPage("otp");
    } catch {
      setError("Could not send code. Try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyOTP(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetch(api("/api/auth/verify-otp"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ phone, code: otp }),
      });
      if (!res.ok) throw new Error("Invalid code");
      const userData = await res.json();
      setProfile(userData.user);

      let code = "HS-A7K9P2";
      try {
        const claimRes = await fetch(api("/api/rewards/claim"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(source ? { source_code: source } : {}),
        });
        if (claimRes.ok) {
          const claimData = await claimRes.json();
          code = claimData.reward?.code || code;
          setRewardLink(claimData.short_link || "");
        }
      } catch {}
      setRewardCode(code);
      await loadRewards();
      setPage("reward");
    } catch {
      setError("Invalid or expired code.");
    } finally {
      setLoading(false);
    }
  }

  async function handleOrderNow() {
    setPage("menu");
    await loadMenu();
  }

  async function handleOrderWithoutReward() {
    setPage("menu");
    await loadMenu();
  }

  async function handlePlaceOrder() {
    if (!profile) { setPage("landing"); return; }
    setLoading(true);
    try {
      const res = await fetch(api("/api/orders"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          items: cartItems.map((ci) => ({
            menu_item_id: ci.item.id,
            name: ci.item.name,
            price_cents: ci.item.price_cents,
            quantity: ci.quantity,
          })),
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setOrderConfirmation(data);
        clearCart();
        setPage("order-confirmation");
      }
    } catch {} finally {
      setLoading(false);
    }
  }

  function goToProfile() {
    loadRewards();
    setPage("profile");
  }

  // ------------------ Header ------------------
  const header = (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-20">
      <div className="max-w-6xl mx-auto px-3 sm:px-4 py-2.5 flex items-center justify-between">
        <button onClick={() => { setPage("menu"); loadMenu(); }} className="flex items-center gap-2 shrink-0">
          <span className="text-lg sm:text-xl font-bold" style={{ color: config.primary_color }}>
            {config.restaurant_name}
          </span>
        </button>
        <div className="flex items-center gap-2 sm:gap-3">
          <button onClick={() => setPage("menu")} className="text-xs sm:text-sm text-gray-700 hover:text-gray-900">
            Menu
          </button>
          <button onClick={() => setPage("cart")} className="relative text-xs sm:text-sm text-gray-700 hover:text-gray-900">
            Cart{!!itemCount && <span className="ml-1 bg-red-600 text-white text-[10px] sm:text-xs px-1.5 py-0.5 rounded-full">{itemCount}</span>}
          </button>
          {profile ? (
            <button onClick={goToProfile} className="text-xs sm:text-sm text-gray-700 hover:text-gray-900">
              Rewards
            </button>
          ) : (
            <button onClick={() => setPage("landing")} className="text-xs sm:text-sm font-medium" style={{ color: config.primary_color }}>
              Sign In
            </button>
          )}
        </div>
      </div>
    </header>
  );

  // ------------------ Footer ------------------
  const footer = (
    <footer className="border-t border-gray-200 mt-8 py-4 text-center text-xs text-gray-400">
      <div className="flex justify-center gap-4 mb-1">
        <button onClick={() => setPage("terms")} className="hover:underline">Terms and Conditions</button>
        <button onClick={() => setPage("privacy")} className="hover:underline">Privacy</button>
      </div>
      <p>© Copyright by Hong Shing 2022</p>
    </footer>
  );

  // ------------------ Content ------------------
  let content = <div />;

  // Modal overlay wrapper — backdrop + centered card
  const modalPage = (
    <div className="fixed inset-0 z-50 overflow-hidden" style={{ paddingTop: "max(0px, env(safe-area-inset-top))", paddingBottom: "max(0px, env(safe-area-inset-bottom))" }}>
      <div className="absolute inset-0 bg-gray-100" />
      <div className="absolute inset-0 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl max-h-[calc(100dvh-32px)] overflow-y-auto"
          style={{ width: "calc(100vw - 32px)" }}>
          {/* Landing page (sign up / sign in) */}
          {page === "landing" && (
            <div className="p-6 sm:p-8">
              <h1 className="text-2xl sm:text-3xl font-bold text-center mb-2" style={{ color: config.primary_color }}>
                {config.restaurant_name} Rewards
              </h1>
              <p className="text-gray-600 text-center mb-6 text-sm sm:text-base">
                {config.campaign?.landing_headline || "Order direct & earn rewards."}
                <br />
                {config.campaign?.landing_subtitle || "Get $5 off your next pickup order."}
              </p>
              <form onSubmit={handleSendOTP} className="space-y-4">
                <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
                  placeholder="647 555 1234"
                  className="w-full min-h-[48px] px-4 py-3 border border-gray-300 rounded-lg text-lg focus:outline-none focus:ring-2"
                  style={{ "--tw-ring-color": config.primary_color } as any} required />
                <button type="submit" disabled={loading}
                  className="w-full min-h-[48px] py-3 text-white font-semibold rounded-lg text-lg disabled:opacity-50"
                  style={{ backgroundColor: config.primary_color }}>
                  {loading ? "Sending..." : "Send Code"}
                </button>
              </form>
              {error && <p className="text-red-500 text-sm text-center mt-4">{error}</p>}
              {config.allow_order_without_signup && (
                <button onClick={handleOrderWithoutReward} className="w-full mt-3 py-2 text-gray-500 text-sm underline">
                  Browse menu without signing up
                </button>
              )}
            </div>
          )}

          {/* OTP verification */}
          {page === "otp" && (
            <div className="p-6 sm:p-8">
              <h2 className="text-xl sm:text-2xl font-bold text-center mb-4">Enter Code</h2>
              <p className="text-gray-600 text-center mb-6 text-sm sm:text-base">
                Enter the 6-digit code we sent to {phone}
              </p>
              <form onSubmit={handleVerifyOTP} className="space-y-4">
                <input type="text" inputMode="numeric" maxLength={6} value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))} placeholder="000000"
                  className="w-full min-h-[56px] px-4 py-3 border border-gray-300 rounded-lg text-center text-2xl tracking-widest focus:outline-none focus:ring-2" autoFocus required />
                <button type="submit" disabled={loading || otp.length !== 6}
                  className="w-full min-h-[48px] py-3 text-white font-semibold rounded-lg text-lg disabled:opacity-50"
                  style={{ backgroundColor: config.primary_color }}>
                  {loading ? "Verifying..." : "Verify"}
                </button>
              </form>
              {error && <p className="text-red-500 text-sm text-center mt-4">{error}</p>}
              <button onClick={() => setPage("landing")} className="w-full mt-4 py-2 text-gray-500 text-sm underline">
                Back
              </button>
            </div>
          )}

          {/* Reward page */}
          {page === "reward" && (
            <div className="p-6 sm:p-8">
              <div className="text-center mb-6">
                <div className="text-5xl mb-4">🎉</div>
                <h2 className="text-xl sm:text-2xl font-bold mb-2">You're in!</h2>
                <p className="text-gray-600 text-sm sm:text-base">Your reward code:</p>
                <div className="my-4">
                  <span className="text-2xl sm:text-3xl font-mono font-bold tracking-widest bg-gray-100 px-4 sm:px-6 py-3 rounded-lg inline-block break-all">
                    {rewardCode}
                  </span>
                </div>
                <p className="text-sm text-gray-500">Use this code on your next direct pickup order.</p>
                {rewardLink && <p className="text-xs text-gray-400 mt-2 break-all">{rewardLink}</p>}
              </div>
              <button onClick={handleOrderNow}
                className="w-full min-h-[48px] py-3 text-white font-semibold rounded-lg text-lg mb-3"
                style={{ backgroundColor: config.primary_color }}>
                Browse Menu
              </button>
              <button onClick={goToProfile}
                className="w-full min-h-[48px] py-3 border-2 font-semibold rounded-lg text-lg"
                style={{ borderColor: config.primary_color, color: config.primary_color }}>
                View My Rewards
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  // Landing page (sign up / sign in)
  if (page === "landing") {
    content = modalPage;
  }

  // OTP verification
  if (page === "otp") {
    content = modalPage;
  }

  // Reward page
  if (page === "reward") {
    content = modalPage;
  }

  // Profile / rewards page
  if (page === "profile") {
    content = (
      <div className="min-h-screen bg-gray-50">
        {header}
        <div className="max-w-md mx-auto p-4 mt-4">
          <div className="bg-white rounded-2xl shadow p-8">
            <h2 className="text-2xl font-bold mb-4">My Rewards</h2>
            {profile && <p className="text-gray-600 mb-4">{profile.phone} {profile.name ? `· ${profile.name}` : ""}</p>}
            {rewards.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-400 text-lg mb-4">No rewards yet</p>
                <button onClick={() => setPage("landing")}
                  className="px-6 py-3 text-white font-semibold rounded-lg"
                  style={{ backgroundColor: config.primary_color }}>
                  Claim a Reward
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {rewards.map((r) => (
                  <div key={r.id} className={`border rounded-xl p-4 ${r.status === "issued" ? "border-green-300 bg-green-50" : "border-gray-200 bg-gray-50"}`}>
                    <div className="flex justify-between items-center">
                      <span className="font-mono font-bold text-lg">{r.code}</span>
                      <span className={`text-sm px-2 py-1 rounded-full ${r.status === "issued" ? "bg-green-200 text-green-800" : "bg-gray-200 text-gray-600"}`}>{r.status}</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">Issued {new Date(r.issued_at).toLocaleDateString()}
                      {r.expires_at && ` · Expires ${new Date(r.expires_at).toLocaleDateString()}`}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        {footer}
      </div>
    );
  }

  // Menu page with scroll-synced tabs
  const sectionRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const isScrollingTo = useRef(false);

  useEffect(() => {
    if (page !== "menu" || menu.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (isScrollingTo.current) return;
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const slug = (entry.target as HTMLElement).dataset.categorySlug;
            if (slug) setActiveCategory(slug);
          }
        }
      },
      { rootMargin: "-140px 0px -60% 0px" },
    );
    sectionRefs.current.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [menu, page]);

  function scrollToCategory(slug: string) {
    isScrollingTo.current = true;
    setActiveCategory(slug);
    const el = sectionRefs.current.get(slug);
    if (el) {
      const top = el.getBoundingClientRect().top + window.scrollY - 140;
      window.scrollTo({ top, behavior: "smooth" });
    }
    setTimeout(() => { isScrollingTo.current = false; }, 600);
  }

  if (page === "menu" || page === "product-detail") {
    content = (
      <div className="min-h-screen bg-gray-50">
        {header}
        {/* Sticky category tabs */}
        <div className="sticky top-[48px] z-10 bg-white border-b border-gray-200">
          <div className="flex overflow-x-auto hide-scrollbar smooth-scroll px-2 sm:px-3 gap-0">
            {menu.map((cat) => (
              <button key={cat.slug} onClick={() => scrollToCategory(cat.slug)}
                className={`px-3 sm:px-4 py-2.5 sm:py-3 text-xs sm:text-sm font-medium whitespace-nowrap border-b-2 transition flex-shrink-0 ${activeCategory === cat.slug ? "" : "border-transparent text-gray-500 hover:text-gray-700"}`}
                style={activeCategory === cat.slug ? { borderColor: config.primary_color, color: config.primary_color } : {}}>
                {cat.name}
              </button>
            ))}
          </div>
        </div>

        {/* Menu content */}
        <div className="max-w-6xl mx-auto p-3 sm:p-4">
          {page === "product-detail" && selectedProduct ? (
            <div className="flex flex-col min-h-[calc(100dvh-96px)]">
              <button onClick={() => { setPage("menu"); setSelectedProduct(null); }} className="text-sm text-gray-500 mb-3 hover:underline py-1">
                ← Back to menu
              </button>
              <div className="bg-white rounded-2xl shadow-sm overflow-hidden flex-1">
                {selectedProduct.image_url ? (
                  <img src={selectedProduct.image_url} alt={selectedProduct.name}
                    className="w-full h-48 sm:h-56 md:h-64 object-cover object-center" />
                ) : (
                  <div className="w-full h-48 sm:h-56 md:h-64 bg-gray-100 flex items-center justify-center text-6xl">
                    {categoryEmoji(activeCategory)}
                  </div>
                )}
                <div className="p-4 sm:p-6 pb-24 sm:pb-6">
                  <h1 className="text-xl sm:text-2xl font-bold mb-1">{selectedProduct.name}</h1>
                  <p className="text-lg sm:text-xl font-bold mb-3" style={{ color: config.primary_color }}>
                    {formatPrice(selectedProduct.price_cents)}
                  </p>
                  {selectedProduct.description && (
                    <p className="text-sm sm:text-base text-gray-600 mb-4">{selectedProduct.description}</p>
                  )}
                  {/* Desktop/tablet Add to Cart — inside card */}
                  <button onClick={() => { addItem(selectedProduct); setPage("menu"); setSelectedProduct(null); }}
                    className="hidden sm:block w-full py-3 text-white font-semibold rounded-lg text-lg"
                    style={{ backgroundColor: config.primary_color }}>
                    Add to Cart · {formatPrice(selectedProduct.price_cents)}
                  </button>
                </div>
              </div>
              {/* Mobile sticky Add to Cart */}
              <div className="sm:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 px-3 py-3 z-30"
                style={{ paddingBottom: "max(12px, env(safe-area-inset-bottom))" }}>
                <button onClick={() => { addItem(selectedProduct); setPage("menu"); setSelectedProduct(null); }}
                  className="w-full py-3.5 text-white font-semibold rounded-xl text-base"
                  style={{ backgroundColor: config.primary_color }}>
                  Add to Cart · {formatPrice(selectedProduct.price_cents)}
                </button>
              </div>
            </div>
          ) : menu.length > 0 ? (
            <div>
              {menu.map((cat) => (
                <div key={cat.slug}
                  ref={(el) => { if (el) sectionRefs.current.set(cat.slug, el); }}
                  data-category-slug={cat.slug}
                  className="mb-6 sm:mb-8">
                  <h2 className="text-lg sm:text-xl font-bold mb-3 sm:mb-4 pt-1 sm:pt-2">{cat.name}</h2>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
                    {cat.items.map((item) => (
                      <button key={item.id}
                        onClick={() => { setSelectedProduct(item); setPage("product-detail"); }}
                        className="bg-white rounded-xl shadow-sm overflow-hidden hover:shadow-md transition text-left flex flex-row sm:flex-col">
                        {/* Image — side-by-side on mobile, top on tablet+ */}
                        <div className="w-24 h-24 sm:w-full sm:aspect-[4/3] flex-shrink-0 bg-gray-100 relative overflow-hidden">
                          {item.image_url ? (
                            <img src={item.image_url} alt={item.name}
                              className="w-full h-full object-cover object-center" loading="lazy" />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-4xl opacity-25">
                              {categoryEmoji(cat.slug)}
                            </div>
                          )}
                        </div>
                        {/* Text */}
                        <div className="flex-1 p-2.5 sm:p-3 flex flex-col justify-center min-w-0">
                          <h3 className="font-semibold text-[13px] sm:text-sm leading-tight line-clamp-2">
                            {item.name}
                          </h3>
                          <p className="mt-0.5 sm:mt-1 text-[13px] sm:text-sm font-bold" style={{ color: config.primary_color }}>
                            {formatPrice(item.price_cents)}
                          </p>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
              {/* Extra bottom padding for safe area */}
              <div className="pb-4" style={{ paddingBottom: "max(16px, env(safe-area-inset-bottom))" }} />
            </div>
          ) : (
            <div className="text-center py-16 text-gray-400">Loading menu...</div>
          )}
        </div>
        {footer}
      </div>
    );
  }

  // Cart page
  if (page === "cart") {
    content = (
      <div className="min-h-screen bg-gray-50">
        {header}
        <div className="max-w-md mx-auto p-4 mt-4">
          {!profile && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-4 text-center">
              <p className="text-amber-800 text-sm mb-2">Sign in to apply reward codes</p>
              <button onClick={() => setPage("landing")}
                className="text-sm font-semibold"
                style={{ color: config.primary_color }}>
                Sign in with phone number →
              </button>
            </div>
          )}
          <div className="bg-white rounded-2xl shadow p-6">
            <h2 className="text-xl font-bold mb-4">Your Order</h2>
            {cartItems.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-400 text-lg mb-4">Your cart is empty</p>
                <button onClick={() => { setPage("menu"); loadMenu(); }}
                  className="px-6 py-3 text-white font-semibold rounded-lg"
                  style={{ backgroundColor: config.primary_color }}>
                  Browse Menu
                </button>
              </div>
            ) : (
              <div>
                <div className="divide-y">
                  {cartItems.map((ci) => (
                    <div key={ci.item.id} className="py-3 flex items-center justify-between">
                      <div className="flex-1">
                        <p className="font-semibold text-sm">{ci.item.name}</p>
                        <p className="text-sm text-gray-500">{formatPrice(ci.item.price_cents)} each</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button onClick={() => updateQuantity(ci.item.id, ci.quantity - 1)}
                          className="w-8 h-8 rounded-full border border-gray-300 flex items-center justify-center text-gray-500 hover:bg-gray-100">−</button>
                        <span className="w-8 text-center font-semibold">{ci.quantity}</span>
                        <button onClick={() => updateQuantity(ci.item.id, ci.quantity + 1)}
                          className="w-8 h-8 rounded-full border border-gray-300 flex items-center justify-center text-gray-500 hover:bg-gray-100">+</button>
                        <span className="ml-3 font-semibold text-sm w-16 text-right">{formatPrice(ci.item.price_cents * ci.quantity)}</span>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="border-t mt-4 pt-4">
                  <div className="flex justify-between font-bold text-lg">
                    <span>Subtotal</span>
                    <span>{formatPrice(subtotalCents)}</span>
                  </div>
                  <div className="flex justify-between text-sm text-gray-500 mt-1 mb-4">
                    <span>{itemCount} item{itemCount !== 1 ? "s" : ""}</span>
                    <span>Pickup only</span>
                  </div>
                  <button onClick={handlePlaceOrder}
                    disabled={loading}
                    className="w-full py-3 text-white font-semibold rounded-lg text-lg disabled:opacity-50"
                    style={{ backgroundColor: config.primary_color }}>
                    {loading ? "Placing order..." : profile ? "Place Order" : "Sign in to Checkout"}
                  </button>
                  <button onClick={clearCart} className="w-full mt-2 py-2 text-sm text-gray-400 underline">Clear cart</button>
                </div>
              </div>
            )}
          </div>
        </div>
        {footer}
      </div>
    );
  }

  // Order confirmation page
  if (page === "order-confirmation" && orderConfirmation) {
    content = (
      <div className="min-h-screen bg-gray-50">
        {header}
        <div className="max-w-md mx-auto p-4 mt-4">
          <div className="bg-white rounded-2xl shadow p-8 text-center">
            <div className="text-5xl mb-4">✅</div>
            <h2 className="text-2xl font-bold mb-2">Order Confirmed!</h2>
            <p className="text-gray-600 mb-6">Your order has been placed for pickup.</p>
            <div className="bg-gray-50 rounded-xl p-4 mb-6 text-left">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Order ID</span>
                <span className="font-mono font-semibold text-xs">{orderConfirmation.order_id.slice(0, 8)}</span>
              </div>
              <div className="flex justify-between text-sm mt-2">
                <span className="text-gray-500">Items</span>
                <span>{orderConfirmation.item_count}</span>
              </div>
              <div className="flex justify-between text-sm mt-2">
                <span className="text-gray-500">Total</span>
                <span className="font-bold" style={{ color: config.primary_color }}>{formatPrice(orderConfirmation.total_cents)}</span>
              </div>
              <div className="flex justify-between text-sm mt-2">
                <span className="text-gray-500">Status</span>
                <span className="text-green-600 font-medium">Pickup pending</span>
              </div>
            </div>
            <button onClick={() => { setPage("menu"); setOrderConfirmation(null); loadMenu(); }}
              className="w-full py-3 text-white font-semibold rounded-lg text-lg mb-3"
              style={{ backgroundColor: config.primary_color }}>
              Back to Menu
            </button>
            <button onClick={goToProfile}
              className="w-full py-3 border-2 font-semibold rounded-lg text-lg"
              style={{ borderColor: config.primary_color, color: config.primary_color }}>
              View My Rewards
            </button>
          </div>
        </div>
        {footer}
      </div>
    );
  }

  // Terms and Conditions page
  if (page === "terms") {
    content = (
      <div className="min-h-screen bg-gray-50">
        {header}
        <div className="max-w-3xl mx-auto p-4 mt-4">
          <div className="bg-white rounded-2xl shadow p-8 prose prose-sm max-w-none">
            <h1 className="text-2xl font-bold mb-6">Terms and Conditions</h1>
            <p className="mb-4">This website is operated by Hong Shing Restaurant. Throughout the site, the terms "we", "us" and "our" refer to Hong Shing Restaurant. Hong Shing Restaurant offers this website, including all information, tools, and services available from this site to you, the user, conditioned upon your acceptance of all terms, conditions, policies, and notices stated here.</p>
            <p className="mb-4">By visiting our site and/ or purchasing something from us, you engage in our "Service" and agree to be bound by the following terms and conditions ("Terms of Service", "Terms"), including those additional terms and conditions and policies referenced herein and/or available by hyperlink. These Terms of Service apply to all users of the site, including without limitation users who are browsers, vendors, customers, merchants, and/ or contributors of content.</p>
            <p className="mb-4">Please read these Terms of Service carefully before accessing or using our website. By accessing or using any part of the site, you agree to be bound by these Terms of Service. If you do not agree to all the terms and conditions of this agreement, then you may not access the website or use any services. If these Terms of Service are considered an offer, acceptance is expressly limited to these Terms of Service.</p>
            <p className="mb-4">Any new features or tools which are added to the current store shall also be subject to the Terms of Service. You can review the most current version of the Terms of Service at any time on this page. We reserve the right to update, change or replace any part of these Terms of Service by posting updates and/or changes to our website. It is your responsibility to check this page periodically for changes. Your continued use of or access to the website following the posting of any changes constitutes acceptance of those changes.</p>

            <h3 className="font-bold mt-6 mb-2">SECTION 1 – ONLINE STORE TERMS</h3>
            <p className="mb-4">By agreeing to these Terms of Service, you represent that you are at least the age of majority in your state or province of residence, or that you are the age of majority in your state or province of residence and you have given us your consent to allow any of your minor dependents to use this site. You may not use our products for any illegal or unauthorized purpose nor may you, in the use of the Service, violate any laws in your jurisdiction (including but not limited to copyright laws). A breach or violation of any of the Terms will result in an immediate termination of your Services.</p>

            <h3 className="font-bold mt-6 mb-2">SECTION 2 – GENERAL CONDITIONS</h3>
            <p className="mb-4">We reserve the right to refuse service to anyone for any reason at any time. You understand that your content (not including credit card information), may be transferred unencrypted and involve (a) transmissions over various networks; and (b) changes to conform and adapt to technical requirements of connecting networks or devices. Credit card information is always encrypted during transfer over networks. You agree not to reproduce, duplicate, copy, sell, resell or exploit any portion of the Service, use of the Service, or access to the Service or any contact on the website through which the service is provided, without express written permission by us.</p>

            <h3 className="font-bold mt-6 mb-2">SECTION 3 – ACCURACY, COMPLETENESS, AND TIMELINESS OF INFORMATION</h3>
            <p className="mb-4">We are not responsible if information made available on this site is not accurate, complete or current. The material on this site is provided for general information only and should not be relied upon or used as the sole basis for making decisions without consulting primary, more accurate, more complete or more timely sources of information. Any reliance on the material on this site is at your own risk.</p>

            <h3 className="font-bold mt-6 mb-2">SECTION 4 – MODIFICATIONS TO THE SERVICE AND PRICES</h3>
            <p className="mb-4">Prices for our products are subject to change without notice. We reserve the right at any time to modify or discontinue the Service (or any part or content thereof) without notice at any time. We shall not be liable to you or to any third-party for any modification, price change, suspension or discontinuance of the Service.</p>

            <h3 className="font-bold mt-6 mb-2">SECTION 5 – PRODUCTS OR SERVICES</h3>
            <p className="mb-4">Certain products or services may be available exclusively online through the website. These products or services may have limited quantities and are subject to return or exchange only according to our Return Policy. We have made every effort to display as accurately as possible the colors and images of our products. We cannot guarantee that your computer monitor's display of any color will be accurate. We reserve the right to limit the quantities of any products or services that we offer. All descriptions of products or product pricing are subject to change at any time without notice. We reserve the right to discontinue any product at any time.</p>

            <h3 className="font-bold mt-6 mb-2">SECTION 6 – ACCURACY OF BILLING AND ACCOUNT INFORMATION</h3>
            <p className="mb-4">We reserve the right to refuse any order you place with us. We may, in our sole discretion, limit or cancel quantities purchased per person, per household or per order. These restrictions may include orders placed by or under the same customer account, the same credit card, and/or orders that use the same billing and/or shipping address. In the event that we make a change to or cancel an order, we may attempt to notify you by contacting the e-mail and/or billing address/phone number provided at the time the order was made.</p>

            <h3 className="font-bold mt-6 mb-2">SECTION 7 – THIRD-PARTY LINKS</h3>
            <p className="mb-4">Certain content, products, and services available via our Service may include materials from third-parties. Third-party links on this site may direct you to third-party websites that are not affiliated with us. We are not responsible for examining or evaluating the content or accuracy and we do not warrant and will not have any liability or responsibility for any third-party materials or websites, or for any other materials, products, or services of third-parties.</p>

            <h3 className="font-bold mt-6 mb-2">SECTION 8 – PERSONAL INFORMATION</h3>
            <p className="mb-4">Your submission of personal information through the store is governed by our Privacy Policy. Please refer to our Privacy Policy.</p>

            <h3 className="font-bold mt-6 mb-2">SECTION 9 – PROHIBITED USES</h3>
            <p className="mb-4">In addition to other prohibitions as set forth in the Terms of Service, you are prohibited from using the site or its content: (a) for any unlawful purpose; (b) to solicit others to perform or participate in any unlawful acts; (c) to violate any international, federal, provincial or state regulations, rules, laws, or local ordinances; (d) to infringe upon or violate our intellectual property rights or the intellectual property rights of others; (e) to harass, abuse, insult, harm, defame, slander, disparage, intimidate, or discriminate based on gender, sexual orientation, religion, ethnicity, race, age, national origin, or disability; (f) to submit false or misleading information; (g) to upload or transmit viruses or any other type of malicious code; (h) to collect or track the personal information of others; (i) to spam, phish, pharm, pretext, spider, crawl, or scrape; (j) for any obscene or immoral purpose; or (k) to interfere with or circumvent the security features of the Service. We reserve the right to terminate your use of the Service for violating any of the prohibited uses.</p>

            <h3 className="font-bold mt-6 mb-2">SECTION 10 – TERMINATION</h3>
            <p className="mb-4">The obligations and liabilities of the parties incurred prior to the termination date shall survive the termination of this agreement. These Terms of Service are effective unless and until terminated by either you or us. You may terminate these Terms of Service at any time by notifying us that you no longer wish to use our Services, or when you cease using our site. If in our sole judgment you fail, or we suspect that you have failed, to comply with any term or provision of these Terms of Service, we also may terminate this agreement at any time without notice.</p>

            <h3 className="font-bold mt-6 mb-2">SECTION 11 – CONTACT INFORMATION</h3>
            <p>For any questions or concerns regarding the Terms of Service, please contact us at <a href="tel:(416) 977-3338" className="underline">(416) 977-3338</a> or send us an email to <a href="mailto:info@hongshing.com" className="underline">info@hongshing.com</a>.</p>
          </div>
        </div>
        {footer}
      </div>
    );
  }

  // Privacy Policy page
  if (page === "privacy") {
    content = (
      <div className="min-h-screen bg-gray-50">
        {header}
        <div className="max-w-3xl mx-auto p-4 mt-4">
          <div className="bg-white rounded-2xl shadow p-8 prose prose-sm max-w-none">
            <h1 className="text-2xl font-bold mb-6">Privacy Policy</h1>
            <p className="mb-4">Hong Shing Restaurant takes your privacy seriously. To better protect your privacy we provide this privacy policy notice explaining the way your personal information is collected and used.</p>
            <p className="mb-4">This website tracks basic information about visitors or users. This information includes, but is not limited to, IP addresses, browser details, timestamps, and referring pages. None of this information can personally identify specific visitors or users to this website. The information is tracked for routine administration and maintenance purposes.</p>
            <p className="mb-4">Where necessary, this website uses cookies to store information about a visitor's preferences and history in order to better serve the visitor or user and/or present the visitor or user with customized content.</p>
            <p className="mb-4">Advertising partners and other third parties may use cookies, scripts and/or web beacons to track user activities on this website in order to display advertisements and other useful information. Such tracking is done directly by the third parties through their own servers and is subject to their own privacy policies. This website has no access or control over these cookies, scripts and/or web beacons that may be used by third parties.</p>
            <p className="mb-4">We have included links on this website for your use and reference. We are not responsible for the privacy policies on these websites. You should be aware that the privacy policies of these websites may differ from our own.</p>
            <p className="mb-4">The security of your personal information is important to us, but remember that no method of transmission over the Internet, or method of electronic storage, is 100% secure. While we strive to use commercially acceptable means to protect your personal information, we cannot guarantee its absolute security.</p>
            <p className="mb-4">This Privacy Policy is effective as of and will remain in effect except with respect to any changes in its provisions in the future, which will be in effect immediately after being posted on this page.</p>
            <p className="mb-4">We reserve the right to update or change our Privacy Policy at any time and you should check this Privacy Policy periodically. If we make any material changes to this Privacy Policy, we will notify you either through the email address you have provided us, or by placing a prominent notice on our website.</p>
            <p>For any questions or concerns regarding the privacy policy, please contact us at <a href="tel:(416) 977-3338" className="underline">(416) 977-3338</a> or send us an email to <a href="mailto:info@hongshing.com" className="underline">info@hongshing.com</a>.</p>
          </div>
        </div>
        {footer}
      </div>
    );
  }

  return (
    <CartContext.Provider value={cartContext}>
      {content}
    </CartContext.Provider>
  );
}
