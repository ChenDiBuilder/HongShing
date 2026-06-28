import secrets

CROCKFORD_BASE32 = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_reward_code(prefix: str = "HS") -> str:
    """Generate a unique reward code: <PREFIX>-XXXXXX using Crockford Base32.

    The prefix comes from the reward template (per-restaurant code_prefix) so a
    clone's codes aren't branded "HS-"."""
    segment = "".join(secrets.choice(CROCKFORD_BASE32) for _ in range(6))
    return f"{prefix}-{segment}"


DEFAULT_REWARD_SMS_TEMPLATE = "{restaurant}: your reward is ready — {reward_code}. Order again: {ordering_url}"


def should_send_reward_sms(
    consent_opt_in: bool,
    mailing_address: str | None,
    template: str | None,
    phone: str | None,
) -> bool:
    """CASL gate (PRD-12 S7 / SCRUM-64): send a reward SMS ONLY when the customer
    has explicitly opted in to marketing SMS AND the restaurant has a configured
    mailing address (required in the message footer) AND there is a template and a
    destination phone. Strict by construction — any missing piece means no send."""
    return bool(consent_opt_in) and bool(mailing_address) and bool(template) and bool(phone)


def render_reward_sms(
    template: str | None,
    restaurant_name: str,
    reward_code: str,
    ordering_url: str,
    mailing_address: str,
) -> str:
    """Render the reward SMS body and append the CASL footer (sender mailing address
    + how to opt out). A malformed template falls back to the default so a send is
    never blocked by bad config."""
    tmpl = template or DEFAULT_REWARD_SMS_TEMPLATE
    try:
        body = tmpl.format(
            restaurant=restaurant_name, reward_code=reward_code, ordering_url=ordering_url
        )
    except (KeyError, IndexError, ValueError):
        body = DEFAULT_REWARD_SMS_TEMPLATE.format(
            restaurant=restaurant_name, reward_code=reward_code, ordering_url=ordering_url
        )
    return f"{body}\n{restaurant_name}, {mailing_address}. Reply STOP to opt out."


def calculate_discount(discount_type: str, discount_value: int, subtotal_cents: int) -> int:
    """Discount in cents, clamped to [0, subtotal].

    Accepts both "percent" (the Restaurant Profile / seeder value) and "percentage"
    so a percent reward actually discounts — they were mismatched before. "fixed" is
    a cents amount capped at the subtotal. Any other type (e.g. "freebie", handled
    elsewhere) yields no monetary discount."""
    if subtotal_cents <= 0 or discount_value <= 0:
        return 0
    if discount_type in ("percentage", "percent"):
        return min((subtotal_cents * discount_value) // 100, subtotal_cents)
    if discount_type == "fixed":
        return min(discount_value, subtotal_cents)
    return 0
