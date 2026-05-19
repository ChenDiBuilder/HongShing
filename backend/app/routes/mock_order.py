from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

router = APIRouter()

MOCK_ORDER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HongShing Ordering — Mock</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f5f5; padding: 20px; }
.container { max-width: 600px; margin: 0 auto; }
.header { background: #c41e3a; color: white; padding: 20px; border-radius: 12px 12px 0 0; text-align: center; }
.header h1 { font-size: 24px; }
.header p { font-size: 14px; opacity: 0.9; margin-top: 4px; }
.promo-banner { background: #fef3c7; border: 1px solid #f59e0b; padding: 12px 16px; margin: 12px 0; border-radius: 8px; display: none; }
.promo-banner.show { display: block; }
.promo-banner .code { font-weight: bold; font-family: monospace; font-size: 18px; }
.menu { background: white; border-radius: 0 0 12px 12px; padding: 16px; }
.menu-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #eee; }
.menu-item:last-child { border-bottom: none; }
.menu-item h3 { font-size: 16px; }
.menu-item .price { font-weight: bold; color: #c41e3a; }
.menu-item button { background: #c41e3a; color: white; border: none; padding: 6px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; }
.menu-item button:hover { opacity: 0.9; }
.cart { margin-top: 20px; background: white; border-radius: 12px; padding: 16px; }
.cart h2 { font-size: 18px; margin-bottom: 12px; }
.cart-item { display: flex; justify-content: space-between; padding: 6px 0; font-size: 14px; }
.cart-total { border-top: 2px solid #333; padding-top: 12px; margin-top: 12px; font-weight: bold; font-size: 16px; display: flex; justify-content: space-between; }
.cart-empty { color: #999; text-align: center; padding: 20px; }
.checkout-btn { width: 100%; background: #c41e3a; color: white; border: none; padding: 14px; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 12px; }
.checkout-btn:hover { opacity: 0.9; }
.checkout-btn:disabled { background: #ccc; cursor: not-allowed; }
.success { background: #d1fae5; border: 1px solid #059669; padding: 16px; border-radius: 8px; margin-top: 12px; text-align: center; display: none; }
.success.show { display: block; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🍜 HongShing</h1>
    <p>Mock Ordering Page — Pickup Only</p>
  </div>

  <div id="promoBanner" class="promo-banner">
    🎉 Promo code applied: <span class="code" id="promoCode"></span> — <span id="promoDiscount"></span>
  </div>

  <div class="menu">
    <div class="menu-item">
      <div><h3>Kung Pao Chicken</h3><p style="color:#666;font-size:13px">Spicy Szechuan stir-fry with peanuts</p></div>
      <div><span class="price">$14.99</span> <button onclick="addToCart('Kung Pao Chicken', 1499)">Add</button></div>
    </div>
    <div class="menu-item">
      <div><h3>Mapo Tofu</h3><p style="color:#666;font-size:13px">Silken tofu in spicy chili bean sauce</p></div>
      <div><span class="price">$12.99</span> <button onclick="addToCart('Mapo Tofu', 1299)">Add</button></div>
    </div>
    <div class="menu-item">
      <div><h3>Spring Rolls (4 pcs)</h3><p style="color:#666;font-size:13px">Crispy vegetable spring rolls</p></div>
      <div><span class="price">$6.99</span> <button onclick="addToCart('Spring Rolls', 699)">Add</button></div>
    </div>
    <div class="menu-item">
      <div><h3>Fried Rice</h3><p style="color:#666;font-size:13px">Egg fried rice with vegetables</p></div>
      <div><span class="price">$10.99</span> <button onclick="addToCart('Fried Rice', 1099)">Add</button></div>
    </div>
    <div class="menu-item">
      <div><h3>Wonton Soup</h3><p style="color:#666;font-size:13px">Handmade pork wontons in broth</p></div>
      <div><span class="price">$8.99</span> <button onclick="addToCart('Wonton Soup', 899)">Add</button></div>
    </div>
  </div>

  <div class="cart">
    <h2>Your Order</h2>
    <div id="cartItems"><p class="cart-empty">Cart is empty</p></div>
    <div id="cartSummary" style="display:none">
      <div class="cart-total">
        <span>Total</span>
        <span id="cartTotal">$0.00</span>
      </div>
      <div id="promoLine" style="display:none; color:#059669; font-size:13px; text-align:right; padding-top:4px">
        Promo discount: −<span id="promoAmount"></span>
      </div>
      <div id="finalLine" style="display:none; font-weight:bold; font-size:16px; display:flex; justify-content:space-between; padding-top:8px">
        <span>After discount</span>
        <span id="finalTotal"></span>
      </div>
      <button class="checkout-btn" onclick="checkout()">Place Pickup Order</button>
    </div>
  </div>

  <div id="successMsg" class="success">
    <h2>✅ Order Placed!</h2>
    <p>Your order will be ready for pickup in ~20 minutes.</p>
    <p style="font-size:13px;color:#666;margin-top:8px">This is a mock — no real order was created.</p>
  </div>
</div>

<script>
const params = new URLSearchParams(window.location.search);
const promo = params.get('promo');
let cart = [];
let promoDiscountCents = 0;
let activeRewards = [];

// Fetch user rewards from API (if logged in)
async function loadRewards() {
  try {
    const resp = await fetch('/api/customer/me/rewards', { credentials: 'include' });
    if (resp.ok) {
      const data = await resp.json();
      activeRewards = (data.data || []).filter(r => r.status === 'issued');
      if (activeRewards.length > 0) {
        document.getElementById('promoBanner').classList.add('show');
        document.getElementById('promoCode').textContent = activeRewards[0].code;
        promoDiscountCents = 500; // $5 off
        document.getElementById('promoDiscount').textContent = '−$5.00 off';
      }
    }
  } catch {}
}

// Fallback: if promo in URL params
if (promo && promo.startsWith('HS-')) {
  document.getElementById('promoBanner').classList.add('show');
  document.getElementById('promoCode').textContent = promo;
  promoDiscountCents = 500;
  document.getElementById('promoDiscount').textContent = '−$5.00 off';
}

loadRewards();

function addToCart(name, priceCents) {
  cart.push({ name, priceCents });
  renderCart();
}

function renderCart() {
  const el = document.getElementById('cartItems');
  const summary = document.getElementById('cartSummary');
  if (cart.length === 0) {
    el.innerHTML = '<p class="cart-empty">Cart is empty</p>';
    summary.style.display = 'none';
    return;
  }
  summary.style.display = 'block';
  el.innerHTML = cart.map((item, i) =>
    `<div class="cart-item"><span>${item.name}</span><span>$${(item.priceCents / 100).toFixed(2)} <button onclick="removeItem(${i})" style="background:none;border:none;cursor:pointer;color:#999;font-size:12px">✕</button></span></div>`
  ).join('');

  const subtotal = cart.reduce((s, i) => s + i.priceCents, 0);
  const hasPromo = promo || activeRewards.length > 0;
  const discount = hasPromo ? promoDiscountCents : 0;
  const total = Math.max(0, subtotal - discount);

  document.getElementById('cartTotal').textContent = `$${(subtotal / 100).toFixed(2)}`;

  const promoLine = document.getElementById('promoLine');
  const finalLine = document.getElementById('finalLine');
  if (hasPromo) {
    promoLine.style.display = 'block';
    document.getElementById('promoAmount').textContent = `$${(discount / 100).toFixed(2)}`;
    finalLine.style.display = 'flex';
    document.getElementById('finalTotal').textContent = `$${(total / 100).toFixed(2)}`;
  }
}

function removeItem(i) {
  cart.splice(i, 1);
  renderCart();
}

function checkout() {
  document.getElementById('successMsg').classList.add('show');
  document.getElementById('cartSummary').style.display = 'none';
  document.getElementById('cartItems').innerHTML = '<p class="cart-empty">Order placed!</p>';
  cart = [];
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
</script>
</body>
</html>"""


@router.get("/mock-order", response_class=HTMLResponse)
async def mock_order():
    return MOCK_ORDER_HTML
