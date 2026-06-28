import secrets

CROCKFORD_BASE32 = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_reward_code(prefix: str = "HS") -> str:
    """Generate a unique reward code: <PREFIX>-XXXXXX using Crockford Base32.

    The prefix comes from the reward template (per-restaurant code_prefix) so a
    clone's codes aren't branded "HS-"."""
    segment = "".join(secrets.choice(CROCKFORD_BASE32) for _ in range(6))
    return f"{prefix}-{segment}"


def calculate_discount(discount_type: str, discount_value: int, subtotal_cents: int) -> int:
    """Calculate discount in cents. Capped at subtotal for fixed discounts."""
    if discount_type == "percentage":
        return (subtotal_cents * discount_value) // 100
    elif discount_type == "fixed":
        return min(discount_value, subtotal_cents)
    return 0
