export type Page =
  | "home" | "landing" | "otp" | "reward" | "profile"
  | "menu" | "product-detail" | "cart" | "order-confirmation"
  | "order-tracking" | "terms" | "privacy" | "reservations";

export interface LandingConfig {
  restaurant_name: string;
  primary_color: string;
  secondary_color?: string;
  logo_url?: string;
  campaign?: { id: string; source_code: string; landing_headline?: string; landing_subtitle?: string };
  allow_order_without_signup: boolean;
  external_ordering_url?: string;
  // Customer-facing storefront/location display (PRD-12 S8). Optional; the app
  // falls back to neutral defaults so a clone never shows another restaurant's info.
  address?: string;
  contact_phone?: string;
  hours_display?: Record<string, string>;
  // Server-computed open/closed state (evaluated in the restaurant's timezone) so
  // the UI can show a "currently closed" banner that tracks real operating hours
  // even while the box is up. Undefined when hours are unset/unparseable.
  is_open?: boolean;
  hours_today?: string;
  pickup_estimate?: string;
  tax_rate?: number;
  currency_symbol?: string;
  // Profile-driven copy + legal/locale (PRD-12 S3/S9). Optional; neutral fallbacks
  // keep a clone free of another restaurant's wording.
  tagline?: string;
  reward_success_copy?: string;
  legal_name?: string;
  languages?: string[];
  storefront_enabled?: boolean;
}

export interface UserReward {
  id: string;
  code: string;
  status: string;
  reward_type?: string;
  reward_value?: number;
  issued_at: string;
  expires_at?: string;
}

// Signed-in customer as returned by /api/customer/me and the OTP verify flow.
export interface CustomerProfile {
  id: string;
  phone?: string | null;
  name?: string | null;
  email?: string | null;
  role?: string;
  created_at?: string;
  rewards?: UserReward[];
}

export interface MenuItemType {
  id: string;
  category_id: string;
  name: string;
  description: string | null;
  price_cents: number;
  image_url: string | null;
  tags: string[];
  popular?: boolean;
}

// Category with its items as returned by /api/menu/full.
export interface MenuCategory {
  id?: string;
  slug: string;
  name: string;
  image_url?: string | null;
  items?: MenuItemType[];
}

// Cart line as returned by GET /api/cart for signed-in customers.
export interface ApiCartLine {
  id: string;
  menu_item_id: string | null;
  name: string;
  price_cents: number;
  image_url?: string | null;
  quantity: number;
  tags?: string[];
}

// Line on an order (checkout confirmation / order history). History lines
// only carry name/price/quantity, so the ids are optional.
export interface OrderLineItem {
  id?: string;
  menu_item_id?: string | null;
  name: string;
  price_cents: number;
  quantity: number;
}

// Checkout response from POST /api/cart/checkout (order-placed event detail).
export interface OrderConfirmationData {
  order_id?: string;
  status?: string;
  total_cents: number;
  items?: OrderLineItem[];
}

// Order as returned by /api/customer/me/orders.
export interface CustomerOrder {
  id: string;
  status: string;
  total_cents: number;
  created_at: string;
  items?: OrderLineItem[];
}

// Availability slot from /api/reservations/slots.
export interface ReservationSlot {
  id: string;
  start_time: string | null;
  end_time: string | null;
  available_spots: number;
  max_party_size?: number;
  max_reservations?: number;
}

// Reservation as returned by /api/customer/me/reservations.
export interface Reservation {
  id: string;
  date: string;
  start_time: string | null;
  end_time?: string | null;
  party_size: number;
  status: string;
  notes?: string | null;
}

export interface CartItem {
  item: MenuItemType;
  quantity: number;
  cartItemId?: string;
}

export interface CartContextType {
  items: CartItem[];
  addItem: (item: MenuItemType) => void;
  removeItem: (itemId: string) => void;
  updateQuantity: (itemId: string, qty: number) => void;
  clearCart: () => void;
  subtotalCents: number;
  itemCount: number;
  loadCart: () => void;
}

export const CATEGORY_EMOJI: Record<string, string> = {
  "new-dishes": "🆕",
  "starters": "🥟",
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

export function categoryEmoji(slug: string) {
  return CATEGORY_EMOJI[slug] || "🍽️";
}

// Runtime restaurant info, hydrated from /api/public/landing-config at startup
// (see applyRestaurantConfig). Defaults are neutral/empty so nothing
// HongShing-specific is hardcoded — a clone shows only its own configured values.
export const RESTAURANT_INFO: {
  address: string;
  phone: string;
  hours: Record<string, string>;
  pickupEstimate: string;
} = {
  address: "",
  phone: "",
  hours: {},
  pickupEstimate: "",
};

// Currency + tax are configurable per restaurant; defaults match a Canadian
// dollar / Ontario HST clone and are overridden by the profile when set.
let currencySymbol = "$";
let taxRateValue = 0.13;

export function taxRate() {
  return taxRateValue;
}

// Apply the restaurant's landing-config to the module-level display state. Call
// once after fetching landing-config, before the first render that reads it.
export function applyRestaurantConfig(cfg: LandingConfig) {
  RESTAURANT_INFO.address = cfg.address || "";
  RESTAURANT_INFO.phone = cfg.contact_phone || "";
  RESTAURANT_INFO.hours = cfg.hours_display || {};
  RESTAURANT_INFO.pickupEstimate = cfg.pickup_estimate || "";
  if (cfg.currency_symbol) currencySymbol = cfg.currency_symbol;
  if (typeof cfg.tax_rate === "number") taxRateValue = cfg.tax_rate;
  // Locale seam (PRD-12 S9): reflect the restaurant's primary language on <html lang>
  // so assistive tech / browsers get the right hint. Plumbing only — no translation.
  if (cfg.languages && cfg.languages.length > 0) {
    document.documentElement.lang = cfg.languages[0];
  }
}

export function formatPrice(cents: number) {
  if (cents == null || isNaN(cents)) return `${currencySymbol}0.00`;
  return `${currencySymbol}${(cents / 100).toFixed(2)}`;
}

// Mirror of the backend reward_service.calculate_discount, for a live cart preview.
// The server re-computes authoritatively at checkout; this only previews the line.
// (Lives here rather than in CartPage so component files only export components.)
export function estimateDiscount(reward: UserReward | undefined, subtotalCents: number): number {
  if (!reward) return 0;
  const v = reward.reward_value ?? 0;
  if (subtotalCents <= 0 || v <= 0) return 0;
  if (reward.reward_type === "percent" || reward.reward_type === "percentage") {
    return Math.min(Math.floor((subtotalCents * v) / 100), subtotalCents);
  }
  if (reward.reward_type === "fixed") return Math.min(v, subtotalCents);
  return 0;
}
