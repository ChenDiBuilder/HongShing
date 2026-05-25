import { useState, useEffect, useCallback, useRef } from "react";
import { CartContext, createCartState } from "./context/CartContext";
import { api } from "./context/api";
import { Header, Footer } from "./components/Header";
import { HomePage } from "./pages/HomePage";
import { MenuPage, ProductDetailPage } from "./pages/MenuPage";
import { CartPage } from "./pages/CartPage";
import { LandingPage, OtpPage, RewardPage } from "./pages/AuthPages";
import { OrderConfirmation, OrderTracking, ProfileRewards } from "./pages/OrderPages";
import { ReservationPage, TermsPage, PrivacyPage } from "./pages/ReservationPage";
import type { Page, LandingConfig, MenuItemType, UserReward } from "./types";

const HARDCODED_OTP = "111111";

export default function App() {
  const [page, setPage] = useState<Page>("menu");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [profile, setProfile] = useState<any>(null);
  const [rewards, setRewards] = useState<UserReward[]>([]);
  const [config, setConfig] = useState<LandingConfig>({ restaurant_name: "Hong Shing", primary_color: "#C41E3A", allow_order_without_signup: true });
  const [menu, setMenu] = useState<any[]>([]);
  const [activeCategory, setActiveCategory] = useState("");
  const [selectedProduct, setSelectedProduct] = useState<MenuItemType | null>(null);
  const [orderConfirmation, setOrderConfirmation] = useState<any>(null);
  const [customerOrders, setCustomerOrders] = useState<any[]>([]);

  const cart = createCartState(profile);

  const sourceRef = useRef<string | undefined>(undefined);
  const autoVerifyRef = useRef(false);
  const returnPageRef = useRef<Page>("menu");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    sourceRef.current = params.get("source") || undefined;
  }, []);

  useEffect(() => {
    fetch(api("/api/customer/me"), { credentials: "include" })
      .then((r) => r.json())
      .then((u) => { if (u.id) { setProfile(u); cart.loadCart(); } })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetch(api(`/api/public/landing-config${sourceRef.current ? `?source=${sourceRef.current}` : ""}`))
      .then((r) => r.json()).then(setConfig).catch(() => {});
  }, []);

  const loadMenu = useCallback(async () => {
    fetch(api("/api/menu/full"))
      .then((r) => r.json()).then((data: any[]) => {
        setMenu(data);
        if (!activeCategory) setActiveCategory(data[0]?.slug || "");
      }).catch(() => {});
  }, []);

  useEffect(() => { loadMenu(); }, [loadMenu]);

  const loadRewards = useCallback(async () => {
    if (!profile) return;
    fetch(api("/api/customer/me/rewards"), { credentials: "include" })
      .then((r) => r.json()).then((d) => setRewards(d.rewards || [])).catch(() => {});
  }, [profile]);

  useEffect(() => { loadRewards(); }, [loadRewards]);

  useEffect(() => {
    const onOrderPlaced = (e: Event) => {
      const d = (e as CustomEvent).detail;
      setOrderConfirmation(d);
      setPage("order-confirmation");
    };
    const onSignIn = () => { returnPageRef.current = page as Page; setPage("landing"); };
    window.addEventListener("order-placed", onOrderPlaced);
    window.addEventListener("signin-required", onSignIn);
    return () => {
      window.removeEventListener("order-placed", onOrderPlaced);
      window.removeEventListener("signin-required", onSignIn);
    };
  }, []);

  const verifyCode = useCallback(async (code: string) => {
    setLoading(true); setError("");
    try {
      const res = await fetch(api("/api/auth/verify-otp"), {
        method: "POST", headers: { "Content-Type": "application/json" },
        credentials: "include", body: JSON.stringify({ phone, code, source_code: sourceRef.current }),
      });
      if (!res.ok) throw new Error("Invalid code");
      const d = await res.json();
      setProfile(d.user);
      cart.loadCart();
      try {
        await fetch(api("/api/rewards/claim"), {
          method: "POST", headers: { "Content-Type": "application/json" },
          credentials: "include", body: JSON.stringify({ source_code: sourceRef.current }),
        });
      } catch {}
      loadRewards();
      await loadMenu();
      const goTo = returnPageRef.current === "otp" || returnPageRef.current === "landing" ? "menu" : returnPageRef.current;
      returnPageRef.current = "menu";
      setPage(goTo);
    } catch { setError("Invalid or expired code."); }
    finally { setLoading(false); }
  }, [phone, loadRewards, loadMenu, cart]);

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault();
    await verifyCode(otp);
  }

  useEffect(() => {
    if (page === "otp" && phone && !autoVerifyRef.current) {
      autoVerifyRef.current = true;
      setOtp(HARDCODED_OTP);
      const timer = setTimeout(() => verifyCode(HARDCODED_OTP), 600);
      return () => clearTimeout(timer);
    }
    if (page !== "otp") {
      autoVerifyRef.current = false;
    }
  }, [page, phone, verifyCode]);

  const loadCustomerOrders = useCallback(() => {
    if (!profile) return;
    fetch(api("/api/customer/me/orders"), { credentials: "include" })
      .then((r) => r.json()).then((d) => setCustomerOrders(d.orders || [])).catch(() => {});
  }, [profile]);

  const handleLogout = useCallback(async () => {
    if (profile) {
      await fetch(api("/api/cart"), { method: "DELETE", credentials: "include" });
    }
    await fetch(api("/api/auth/logout"), { method: "POST", credentials: "include" });
    setProfile(null);
    setCustomerOrders([]);
    setRewards([]);
    cart.clearCart();
    setPage("home");
  }, [cart, profile]);

  const showHeader = !["home", "landing", "otp", "reward"].includes(page);
  const showFooter = !["home", "landing", "otp", "reward"].includes(page);

  const header = showHeader ? (
    <Header config={config} profile={profile} itemCount={cart.itemCount} subtotalCents={cart.subtotalCents} setPage={setPage}
      loadMenu={loadMenu} loadRewards={loadRewards} loadReservationSlots={() => {}}
      loadMyReservations={() => {}} loadCustomerOrders={loadCustomerOrders} handleLogout={handleLogout}
      onSignIn={() => { returnPageRef.current = page as Page; setPage("landing"); }} />
  ) : null;
  const footer = showFooter ? <Footer setPage={setPage} /> : null;

  const wrap = (children: React.ReactNode) => (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-3xl mx-auto p-4 mt-4">{children}</div>
      {footer}
    </div>
  );

  let content: React.ReactNode;

  if (page === "home") {
    content = (
      <HomePage primaryColor={config.primary_color} logoUrl={config.logo_url}
        secondaryColor={config.secondary_color} campaign={config.campaign}
        setPage={setPage} loadMenu={loadMenu}
        onClaimReward={() => { returnPageRef.current = "reward"; setPage("landing"); }} />
    );
    content = <>{content}<Footer setPage={setPage} /></>;
  } else if (page === "landing") {
    content = (
      <LandingPage primaryColor={config.primary_color} setPage={setPage} setProfile={setProfile}
        loadCart={cart.loadCart} loadRewards={loadRewards} setPhone={setPhone} phone={phone}
        source={sourceRef.current} />
    );
  } else if (page === "otp") {
    content = (
      <OtpPage phone={phone} otp={otp} setOtp={setOtp} loading={loading} error={error}
        handleVerify={handleVerify} setPage={setPage} primaryColor={config.primary_color} />
    );
  } else if (page === "reward") {
    content = (
      <RewardPage rewardCode={""} setPage={setPage} primaryColor={config.primary_color}
        loadMenu={loadMenu} loadRewards={loadRewards} profile={profile} handleLogout={handleLogout} />
    );
  } else if (page === "profile") {
    content = <>{header}{wrap(<ProfileRewards rewards={rewards} primaryColor={config.primary_color} setPage={setPage} loadRewards={loadRewards} />)}</>;
  } else if (page === "menu") {
    content = <>{header}{wrap(<MenuPage menu={menu} activeCategory={activeCategory} setActiveCategory={setActiveCategory} setSelectedProduct={setSelectedProduct} setPage={setPage} primaryColor={config.primary_color} />)}</>;
  } else if (page === "product-detail" && selectedProduct) {
    content = <>{header}{wrap(<ProductDetailPage product={selectedProduct} setPage={setPage} primaryColor={config.primary_color} />)}</>;
  } else if (page === "cart") {
    content = <>{header}{wrap(<CartPage primaryColor={config.primary_color} profile={profile} setPage={setPage} />)}</>;
  } else if (page === "order-confirmation" && orderConfirmation) {
    content = <>{header}{wrap(<OrderConfirmation order={orderConfirmation} primaryColor={config.primary_color} setPage={setPage} loadMenu={loadMenu} />)}</>;
  } else if (page === "order-tracking") {
    content = <>{header}{wrap(<OrderTracking orders={customerOrders} setPage={setPage} loadMenu={loadMenu} primaryColor={config.primary_color} />)}</>;
  } else if (page === "reservations") {
    content = <>{header}{wrap(<ReservationPage primaryColor={config.primary_color} setPage={setPage} profile={profile} />)}</>;
  } else if (page === "terms") {
    content = <>{header}{wrap(<TermsPage />)}</>;
  } else if (page === "privacy") {
    content = <>{header}{wrap(<PrivacyPage />)}</>;
  } else {
    content = null;
  }

  return <CartContext.Provider value={cart}>{content}</CartContext.Provider>;
}
