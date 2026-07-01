"""Business-hours open/closed computation.

The customer landing-config exposes a server-computed ``is_open`` so the SPA can
show a "currently closed" state that tracks the restaurant's real operating
hours — independent of whether the box happens to be running (it spins up ~30m
before open and stops ~15m before close). Evaluated in the restaurant's own
timezone so it is correct regardless of where the viewer is.
"""

from __future__ import annotations

import re
from datetime import datetime, time
from zoneinfo import ZoneInfo

# hours_display keys use these 3-letter day abbreviations (Mon..Sun); index by
# Python's Monday=0..Sunday=6 weekday().
_WEEKDAY_ABBR = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Accept en dash / em dash / hyphen (with optional surrounding spaces) as the
# open–close separator, matching the seeded display strings ("11:30 AM – 9:00 PM").
_RANGE_SEP = re.compile(r"\s*[–—-]\s*")


def _parse_clock(raw: str) -> time | None:
    s = raw.strip().upper().replace(".", "")
    for fmt in ("%I:%M %p", "%I %p", "%H:%M"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    return None


def compute_open_status(
    hours_display: dict[str, str] | None,
    tz_name: str | None,
    now: datetime | None = None,
) -> tuple[bool | None, str | None]:
    """Return ``(is_open, hours_today)`` for the restaurant's local "now".

    ``is_open`` is ``None`` when hours are missing or unparseable (fail open — the
    SPA then shows no closed banner rather than a wrong one). ``hours_today`` is
    the raw display string for the current day ("11:30 AM – 9:00 PM" or "Closed").
    """
    if not hours_display:
        return None, None
    try:
        tz = ZoneInfo(tz_name or "America/Toronto")
    except Exception:
        tz = ZoneInfo("America/Toronto")
    current = now.astimezone(tz) if now else datetime.now(tz)

    label = _WEEKDAY_ABBR[current.weekday()]
    today = hours_display.get(label)
    if today is None:
        return None, None
    if today.strip().lower() in {"closed", "close"}:
        return False, today

    parts = _RANGE_SEP.split(today.strip(), maxsplit=1)
    if len(parts) != 2:
        return None, today
    open_t, close_t = _parse_clock(parts[0]), _parse_clock(parts[1])
    if open_t is None or close_t is None:
        return None, today

    nt = current.time()
    if close_t <= open_t:
        # Overnight window (closes after midnight): open if now is past open OR before close.
        is_open = nt >= open_t or nt < close_t
    else:
        is_open = open_t <= nt < close_t
    return is_open, today
