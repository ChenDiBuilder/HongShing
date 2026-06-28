import secrets

CROCKFORD_BASE32 = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_reward_code(prefix: str = "HS") -> str:
    """Generate a unique reward code: <PREFIX>-XXXXXX using Crockford Base32.

    The prefix comes from the reward template (per-restaurant code_prefix) so a
    clone's codes aren't branded "HS-"."""
    segment = "".join(secrets.choice(CROCKFORD_BASE32) for _ in range(6))
    return f"{prefix}-{segment}"


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
