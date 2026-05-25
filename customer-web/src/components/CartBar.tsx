import { useCart } from "../context/CartContext";
import { formatPrice } from "../types";

interface Props {
  primaryColor: string;
  setPage: (p: any) => void;
}

export function CartBar({ primaryColor, setPage }: Props) {
  const cart = useCart();

  if (cart.itemCount === 0) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 px-3 pb-3 pointer-events-none">
      <div className="max-w-3xl mx-auto">
        <button
          onClick={() => setPage("cart")}
          className="w-full flex items-center justify-between px-5 py-4 rounded-2xl text-white font-semibold shadow-xl pointer-events-auto active:scale-[0.98] transition-transform"
          style={{ backgroundColor: primaryColor }}>
          <span className="text-base">{cart.itemCount} {cart.itemCount === 1 ? "item" : "items"} · {formatPrice(cart.subtotalCents)}</span>
          <span className="text-base">View Cart →</span>
        </button>
      </div>
    </div>
  );
}
