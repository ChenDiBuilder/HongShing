import { createContext, useState, useCallback, useContext, useEffect, useRef, useMemo } from "react";
import type { CartItem, CartContextType, MenuItemType } from "../types";
import { api } from "./api";

const CartContext = createContext<CartContextType>({
  items: [],
  addItem: () => {},
  removeItem: () => {},
  updateQuantity: () => {},
  clearCart: () => {},
  subtotalCents: 0,
  itemCount: 0,
  loadCart: () => {},
});

export function createCartState(profile: any, onLoadCart?: () => void) {
  const [items, setItems] = useState<CartItem[]>([]);
  const subtotalCents = items.reduce((s, ci) => s + ci.item.price_cents * ci.quantity, 0);
  const itemCount = items.reduce((s, ci) => s + ci.quantity, 0);
  const prevProfile = useRef<any>(null);

  const loadCart = useCallback(async () => {
    if (!profile) return;
    try {
      const r = await fetch(api("/api/cart"), { credentials: "include" });
      const d = await r.json();
      const dbItems = d.cart?.items || [];
      setItems(dbItems.map((i: any) => ({
        item: { id: i.menu_item_id || i.id, category_id: "", name: i.name, description: null, price_cents: i.price_cents, image_url: null, tags: i.tags || [] },
        quantity: i.quantity,
        cartItemId: i.id,
      })));
      onLoadCart?.();
    } catch {}
  }, [profile]);

  useEffect(() => {
    if (profile && !prevProfile.current) {
      setItems((prev) => {
        for (const ci of prev) {
          if (!ci.cartItemId) {
            fetch(api("/api/cart/items"), {
              method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include",
              body: JSON.stringify({ menu_item_id: ci.item.id, name: ci.item.name, price_cents: ci.item.price_cents, quantity: ci.quantity }),
            }).catch(() => {});
          }
        }
        return prev;
      });
      loadCart();
    }
    prevProfile.current = profile;
  }, [profile, loadCart]);

  const addItem = useCallback(async (item: MenuItemType) => {
    setItems((prev) => {
      const existing = prev.find((ci) => ci.item.id === item.id);
      if (existing) return prev.map((ci) => ci.item.id === item.id ? { ...ci, quantity: ci.quantity + 1 } : ci);
      return [...prev, { item, quantity: 1 }];
    });
    if (profile) {
      try {
        await fetch(api("/api/cart/items"), {
          method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include",
          body: JSON.stringify({ menu_item_id: item.id, name: item.name, price_cents: item.price_cents, quantity: 1 }),
        });
      } catch {}
    }
  }, [profile]);

  const removeItem = useCallback((itemId: string) => {
    setItems((prev) => {
      const ci = prev.find((i) => i.item.id === itemId || i.cartItemId === itemId);
      if (ci?.cartItemId && profile) {
        fetch(api(`/api/cart/items/${ci.cartItemId}`), { method: "DELETE", credentials: "include" }).catch(() => {});
      }
      return prev.filter((i) => i.item.id !== itemId && i.cartItemId !== itemId);
    });
  }, [profile]);

  const updateQuantity = useCallback((itemId: string, qty: number) => {
    if (qty <= 0) { removeItem(itemId); return; }
    setItems((prev) => {
      const ci = prev.find((i) => i.item.id === itemId || i.cartItemId === itemId);
      if (ci?.cartItemId && profile) {
        fetch(api(`/api/cart/items/${ci.cartItemId}`), {
          method: "PATCH", headers: { "Content-Type": "application/json" }, credentials: "include",
          body: JSON.stringify({ quantity: qty }),
        }).catch(() => {});
      }
      return prev.map((i) => i.item.id === itemId || i.cartItemId === itemId ? { ...i, quantity: qty } : i);
    });
  }, [profile, removeItem]);

  const clearCart = useCallback(() => setItems([]), []);

  // Memoize the context value so a parent re-render (e.g. the menu scroll-spy
  // updating activeCategory in App) doesn't hand every useCart() consumer a new
  // object identity and re-render all ~78 menu rows on each scroll tick. The
  // callbacks are already useCallback-stable; subtotalCents/itemCount derive from
  // items, so [items] covers them.
  return useMemo(
    () => ({ items, addItem, removeItem, updateQuantity, clearCart, subtotalCents, itemCount, loadCart }),
    [items, addItem, removeItem, updateQuantity, clearCart, loadCart]
  );
}

export function useCart() {
  return useContext(CartContext);
}

export { CartContext };
export type { CartContextType };
