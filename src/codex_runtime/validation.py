"""Strict parsing of capacity and provider reset boundaries."""

from contextlib import suppress
from datetime import UTC, datetime

from codex_runtime.models import LimitScope, Reason, WindowAvailability


def parse_window(
    scope: LimitScope, value: object, checked_at: datetime
) -> WindowAvailability:
    """Missing/ambiguous windows never confirm capacity."""
    if not isinstance(value, dict):
        return WindowAvailability(scope, None, None, None, Reason.UNKNOWN_CAPACITY)
    used = value.get("usedPercent")
    if type(used) is not int or not 0 <= used <= 100:
        return WindowAvailability(scope, None, None, None, Reason.UNKNOWN_CAPACITY)
    available = used < 100
    reset = value.get("resetsAt")
    if reset is None:
        reason = Reason.AVAILABLE if available else Reason.MISSING_RESET
        return WindowAvailability(scope, available, used, None, reason)
    boundary = None
    if type(reset) is int and reset > 0:
        with suppress(OverflowError, OSError, ValueError):
            boundary = datetime.fromtimestamp(reset, UTC)
    if boundary is None or boundary <= checked_at:
        return WindowAvailability(
            scope, None if available else False, used, None, Reason.INVALID_RESET
        )
    reason = Reason.AVAILABLE if available else Reason.EXHAUSTED
    return WindowAvailability(scope, available, used, boundary, reason)
