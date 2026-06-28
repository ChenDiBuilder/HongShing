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
  pickup_estimate?: string;
  tax_rate?: number;
  currency_symbol?: string;
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
}

export function formatPrice(cents: number) {
  if (cents == null || isNaN(cents)) return `${currencySymbol}0.00`;
  return `${currencySymbol}${(cents / 100).toFixed(2)}`;
}
