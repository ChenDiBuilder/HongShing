import { formatPrice } from "../types";

interface HeaderProps {
  config: any;
  profile?: any;
  itemCount: number;
  subtotalCents: number;
  setPage: (p: any) => void;
  loadMenu: () => void;
  loadRewards: () => void;
  loadReservationSlots: () => void;
  loadMyReservations: () => void;
  loadCustomerOrders: () => void;
  handleLogout?: () => void;
  onSignIn?: () => void;
  onExternalOrder?: () => void;
}

export function Header({ config, profile, itemCount, subtotalCents, setPage, loadMenu, loadRewards, loadReservationSlots: _rs, loadMyReservations: _mr, loadCustomerOrders, handleLogout, onSignIn, onExternalOrder }: HeaderProps) {
  const primary = config?.primary_color || "#111827";
  // Only show the external "Order Online" CTA when a redirect URL is configured
  // (PRD-12 S10 / SCRUM-78) — never a hardcoded link.
  const showOrderOnline = !!config?.external_ordering_url && !!onExternalOrder;

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-gray-100">
      <div className="max-w-3xl mx-auto px-4 h-14 flex items-center justify-between">
        <button onClick={() => { loadMenu(); setPage("menu"); }}
          className="flex items-center gap-2">
          {config?.logo_url && <img src={config.logo_url} alt="" className="h-9 w-9 rounded-md object-contain" />}
          <span className="text-lg font-extrabold tracking-tight" style={{ color: primary }}>{config?.restaurant_name || "Restaurant"}</span>
        </button>
        <nav className="flex items-center gap-1">
          <NavBtn onClick={() => { loadMenu(); setPage("menu"); }}>Menu</NavBtn>
          {showOrderOnline && <NavBtn onClick={onExternalOrder!}>Order Online</NavBtn>}
          <CartBtn itemCount={itemCount} subtotalCents={subtotalCents} onClick={() => setPage("cart")} />
          {profile ? (
            <>
              <NavBtn onClick={() => { loadCustomerOrders(); setPage("order-tracking"); }}>Orders</NavBtn>
              <NavBtn onClick={() => { loadRewards(); setPage("profile"); }}>Rewards</NavBtn>
              <NavBtn onClick={() => { loadCustomerOrders(); setPage("order-tracking"); }} primary={primary}>Account</NavBtn>
              <NavBtn onClick={handleLogout || (() => {})}>Sign Out</NavBtn>
            </>
          ) : (
            <NavBtn onClick={onSignIn || (() => {})} primary={primary}>Sign In</NavBtn>
          )}
        </nav>
      </div>
    </header>
  );
}

function NavBtn({ onClick, children, primary }: { onClick: () => void; children: React.ReactNode; primary?: string }) {
  return (
    <button onClick={onClick}
      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${primary ? "text-white" : "text-gray-600 hover:bg-gray-100"}`}
      style={primary ? { backgroundColor: primary } : {}}>
      {children}
    </button>
  );
}

function CartBtn({ itemCount, subtotalCents, onClick }: { itemCount: number; subtotalCents: number; onClick: () => void }) {
  if (itemCount === 0) {
    return (
      <button onClick={onClick} className="relative px-3 py-1.5 rounded-full text-sm font-medium text-gray-600 hover:bg-gray-100">
        Cart
      </button>
    );
  }
  return (
    <button onClick={onClick} className="relative px-3 py-1.5 rounded-full text-sm font-medium text-gray-600 hover:bg-gray-100">
      Cart · {formatPrice(subtotalCents)}
    </button>
  );
}

export function Footer({ setPage, config }: { setPage: (p: any) => void; config?: any }) {
  return (
    <footer className="border-t border-gray-100 bg-white">
      <div className="max-w-3xl mx-auto px-4 py-6 flex items-center justify-between text-xs text-gray-400">
        {/* Prefer the registered legal name in the footer (PRD-12 S9); fall back to display name. */}
        <span>© {new Date().getFullYear()} {config?.legal_name || config?.restaurant_name}</span>
        <div className="flex gap-4">
          <button onClick={() => setPage("terms")} className="hover:text-gray-600">Terms</button>
          <button onClick={() => setPage("privacy")} className="hover:text-gray-600">Privacy</button>
        </div>
      </div>
    </footer>
  );
}
