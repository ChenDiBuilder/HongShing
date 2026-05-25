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

export function formatPrice(cents: number) {
  if (cents == null || isNaN(cents)) return "$0.00";
  return `$${(cents / 100).toFixed(2)}`;
}

export const RESTAURANT_INFO = {
  cuisine: "Cantonese & Chinese",
  address: "195 Dundas St W, Toronto, ON M5G 1C7",
  phone: "+14169773338",
  hours: {
    "Mon": "11:30 AM – 9:00 PM",
    "Tue": "Closed",
    "Wed": "11:30 AM – 9:00 PM",
    "Thu": "11:30 AM – 9:00 PM",
    "Fri": "11:30 AM – 10:00 PM",
    "Sat": "11:30 AM – 10:00 PM",
    "Sun": "11:30 AM – 9:00 PM",
  },
  pickupEstimate: "20–30 minutes",
};
