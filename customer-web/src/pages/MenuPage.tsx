import { useState, useEffect, useRef } from "react";
import { categoryEmoji, formatPrice, type MenuItemType } from "../types";
import { useCart } from "../context/CartContext";
import { CartBar } from "../components/CartBar";

function QuickAddButton({ item, primaryColor }: { item: MenuItemType; primaryColor: string }) {
  const cart = useCart();
  const cartItem = cart.items.find((ci) => ci.item.id === item.id);
  const qty = cartItem?.quantity || 0;

  function handleAdd(e: React.MouseEvent) {
    e.stopPropagation();
    cart.addItem(item);
  }

  function handleRemove(e: React.MouseEvent) {
    e.stopPropagation();
    cart.updateQuantity(item.id, qty - 1);
  }

  if (qty > 0) {
    return (
      <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
        <button
          onClick={handleRemove}
          className="min-h-[32px] min-w-[32px] rounded-lg border border-gray-200 text-gray-500 font-bold text-sm flex items-center justify-center active:scale-90 transition-transform"
          aria-label={`Remove one ${item.name}`}>−</button>
        <span className="text-sm font-bold w-6 text-center">{qty}</span>
        <button
          onClick={handleAdd}
          className="min-h-[32px] min-w-[32px] rounded-lg border border-gray-200 text-gray-500 font-bold text-sm flex items-center justify-center active:scale-90 transition-transform"
          aria-label={`Add one ${item.name}`}>+</button>
      </div>
    );
  }

  return (
    <button
      onClick={handleAdd}
      className="min-h-[36px] px-3 py-1.5 rounded-xl flex items-center justify-center text-white font-semibold text-sm transition-all active:scale-90"
      style={{ backgroundColor: primaryColor }}
      aria-label={`Add ${item.name} to cart`}>
      Add
    </button>
  );
}

function PopularBanner({ popular, primaryColor, setSelectedProduct, setPage }: {
  popular: MenuItemType[]; primaryColor: string; setSelectedProduct: (i: MenuItemType) => void; setPage: (p: any) => void;
}) {
  if (!popular.length) return null;
  return (
    <div className="mb-6">
      <p className="text-xs text-gray-400 uppercase tracking-wider font-semibold mb-3 px-1">Popular Items</p>
      <div className="flex gap-3 overflow-x-auto hide-scrollbar pb-1">
        {popular.slice(0, 6).map((item) => (
          <button key={item.id}
            onClick={() => { setSelectedProduct(item); setPage("product-detail"); }}
            className="flex-shrink-0 w-36 bg-white rounded-2xl shadow-sm border border-gray-100 p-3 text-left active:scale-[0.98] transition-transform">
            <div className="w-full h-24 bg-gray-100 rounded-xl mb-2 flex items-center justify-center text-2xl overflow-hidden">
              {item.image_url
                ? <img src={item.image_url} alt={item.name} width={144} height={96} loading="lazy" decoding="async" className="w-full h-full object-cover rounded-xl" />
                : <span className="text-2xl">🍽️</span>}
            </div>
            <p className="text-sm font-semibold text-gray-800 truncate">{item.name}</p>
            <p className="text-sm font-bold" style={{ color: primaryColor }}>{formatPrice(item.price_cents)}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

export function MenuPage({ menu, activeCategory, setActiveCategory, setSelectedProduct, setPage, primaryColor }: {
  menu: any[]; activeCategory: string; setActiveCategory: (slug: string) => void;
  setSelectedProduct: (item: MenuItemType) => void; setPage: (p: any) => void; primaryColor: string;
}) {
  const sectionRefs = useRef<Record<string, HTMLDivElement | null>>({});
  // When the user taps a category chip we scroll programmatically; suppress the
  // scroll-spy observer briefly so it doesn't fight the animation or flicker the
  // highlighted chip through intermediate categories on the way there.
  const programmaticScrollUntil = useRef(0);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (menu.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        // Ignore observer updates while a tap-driven smooth scroll is animating.
        if (Date.now() < programmaticScrollUntil.current) return;
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const slug = entry.target.getAttribute("data-slug");
            if (slug) setActiveCategory(slug);
          }
        }
      },
      { rootMargin: "-100px 0px -50% 0px", threshold: 0.1 }
    );
    for (const cat of filteredMenu.length ? filteredMenu : menu) {
      const el = sectionRefs.current[cat.slug];
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [menu, setActiveCategory]);

  const allItems: MenuItemType[] = menu.flatMap((c: any) => c.items || []);
  const popular = allItems.filter((i) => i.popular);
  const query = search.toLowerCase().trim();
  const [activeTag, setActiveTag] = useState("");

  const allTags = [...new Set(allItems.flatMap(i => i.tags || []))].sort();

  const filteredMenu = (() => {
    let result = menu;
    if (activeTag) {
      result = menu.map((cat: any) => ({
        ...cat,
        items: (cat.items || []).filter((i: MenuItemType) => (i.tags || []).includes(activeTag)),
      })).filter((cat: any) => cat.items.length > 0);
    }
    if (query) {
      result = result.map((cat: any) => ({
        ...cat,
        items: (cat.items || []).filter((i: MenuItemType) =>
          i.name.toLowerCase().includes(query) || (i.description || "").toLowerCase().includes(query)
        ),
      })).filter((cat: any) => cat.items.length > 0);
    }
    return result;
  })();

  return (
    <div className="pb-24">
      <div className="mb-4">
        <div className="relative">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search menu..."
            className="w-full px-4 py-3 pl-10 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:border-transparent"
            style={{ "--tw-ring-color": primaryColor } as any}
            aria-label="Search menu items"
          />
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          {search && (
            <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-sm" aria-label="Clear search">✕</button>
          )}
        </div>
      </div>

      {allTags.length > 0 && !query && (
        <div className="flex gap-2 overflow-x-auto hide-scrollbar pb-1 mb-2">
          {allTags.map((tag) => (
            <button
              key={tag}
              onClick={() => setActiveTag(activeTag === tag ? "" : tag)}
              className={`flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold transition-colors ${
                activeTag === tag
                  ? "text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
              style={activeTag === tag ? { backgroundColor: primaryColor } : {}}
            >
              {tag}
            </button>
          ))}
        </div>
      )}

      {query ? null : (
        <PopularBanner popular={popular} primaryColor={primaryColor} setSelectedProduct={setSelectedProduct} setPage={setPage} />
      )}

      {!query && (
        <div className="sticky top-0 z-30 bg-gray-50 -mx-4 px-4 pt-1 pb-3">
          <div className="flex gap-2 overflow-x-auto hide-scrollbar">
            {menu.map((cat: any) => (
              <button key={cat.slug}
                onClick={() => {
                  // Tap-to-jump: scroll here only on an explicit tap, and suppress
                  // the observer while it animates so it can't fight the scroll.
                  programmaticScrollUntil.current = Date.now() + 700;
                  setActiveCategory(cat.slug);
                  sectionRefs.current[cat.slug]?.scrollIntoView({ behavior: "smooth", block: "start" });
                }}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors flex-shrink-0 ${activeCategory === cat.slug ? "text-white" : "bg-white text-gray-600 border border-gray-200"}`}
                style={activeCategory === cat.slug ? { backgroundColor: primaryColor } : {}}>
                <span>{categoryEmoji(cat.slug)}</span>
                <span>{cat.name}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-8 mt-2">
        {filteredMenu.map((cat: any) => (
          <div key={cat.slug} ref={(el) => { sectionRefs.current[cat.slug] = el; }} data-slug={cat.slug}>
            <h2 className="text-lg font-bold text-gray-800 mb-3 flex items-center gap-2">
              <span>{categoryEmoji(cat.slug)}</span>
              <span>{cat.name}</span>
            </h2>
            <div className="space-y-3">
              {cat.items?.map((item: MenuItemType) => (
                <button key={item.id}
                  onClick={() => { setSelectedProduct(item); setPage("product-detail"); }}
                  className="w-full flex items-center gap-3 bg-white rounded-2xl p-3 shadow-sm border border-gray-100 text-left active:scale-[0.99] transition-transform">
                  <div className="w-16 h-16 bg-gray-100 rounded-xl flex-shrink-0 flex items-center justify-center text-xl overflow-hidden">
                    {item.image_url
                      ? <img src={item.image_url} alt={item.name} width={64} height={64} loading="lazy" decoding="async" className="w-full h-full object-cover" />
                      : <span className="text-xl">🍽️</span>}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-800 text-sm truncate">{item.name}</p>
                    {item.description && <p className="text-xs text-gray-400 mt-0.5 truncate">{item.description}</p>}
                    <p className="text-sm font-bold mt-1" style={{ color: primaryColor }}>{formatPrice(item.price_cents)}</p>
                  </div>
                  <QuickAddButton item={item} primaryColor={primaryColor} />
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {filteredMenu.length === 0 && (
        <div className="text-center py-20 text-gray-400">
          <p className="text-4xl mb-3">🔍</p>
          <p className="text-lg font-medium text-gray-500">{query ? "No items match your search" : "Menu loading..."}</p>
          {query && <button onClick={() => setSearch("")} className="mt-2 text-sm font-medium" style={{ color: primaryColor }}>Clear search</button>}
        </div>
      )}

      <CartBar primaryColor={primaryColor} setPage={setPage} />
    </div>
  );
}

export function ProductDetailPage({ product, setPage, primaryColor }: {
  product: MenuItemType; setPage: (p: any) => void; primaryColor: string;
}) {
  const cart = useCart();
  const cartItem = cart.items.find((ci) => ci.item.id === product.id);
  const inCart = cartItem?.quantity || 0;
  const [added, setAdded] = useState(false);

  function handleAdd() {
    cart.addItem(product);
    setAdded(true);
    setTimeout(() => setAdded(false), 1500);
  }

  function handleRemove() {
    cart.updateQuantity(product.id, inCart - 1);
  }

  return (
    <div className="pb-28">
      <button onClick={() => setPage("menu")} className="text-sm text-gray-500 mb-3 hover:underline">← Back to Menu</button>
      <div className="w-full h-56 bg-gray-100 rounded-2xl flex items-center justify-center text-5xl overflow-hidden mb-4">
        {product.image_url
          ? <img src={product.image_url} alt={product.name} className="w-full h-full object-cover" />
          : <span className="text-5xl">🍽️</span>}
      </div>
      <h1 className="text-xl font-bold text-gray-800 mb-1">{product.name}</h1>
      {product.description && <p className="text-sm text-gray-500 mb-3">{product.description}</p>}
      <p className="text-2xl font-bold mb-6" style={{ color: primaryColor }}>{formatPrice(product.price_cents)}</p>

      <div className="flex items-center gap-4 mb-6">
        <span className="text-sm text-gray-500">In cart</span>
        <button onClick={handleRemove}
          className="w-10 h-10 rounded-xl border border-gray-300 text-gray-600 font-bold text-lg">−</button>
        <span className="text-lg font-bold w-6 text-center">{inCart}</span>
        <button onClick={handleAdd}
          className="w-10 h-10 rounded-xl border border-gray-300 text-gray-600 font-bold text-lg">+</button>
      </div>

      <div className="fixed bottom-0 left-0 right-0 px-3 pb-4 bg-white/80 backdrop-blur">
        <div className="max-w-3xl mx-auto space-y-2">
          {added && <p className="text-center text-green-600 text-sm font-medium">Added to cart!</p>}
          <button onClick={handleAdd}
            className="w-full py-4 text-white font-bold rounded-2xl text-lg shadow-lg active:scale-[0.98] transition-transform"
            style={{ backgroundColor: primaryColor }}>
            Add to Cart · {formatPrice(product.price_cents)}
          </button>
        </div>
      </div>

      <CartBar primaryColor={primaryColor} setPage={setPage} />
    </div>
  );
}
