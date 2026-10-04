"""Normalize the account/rateLimits/read result without consumer policy."""

from datetime import UTC, datetime

from codex_runtime.models import Availability, LimitScope, Reason, WindowAvailability
from codex_runtime.validation import parse_window


def normalize_rate_limits(payload: object, *, checked_at: datetime) -> Availability:
    """Require explicit 300/10080-minute Codex windows, independent of slot order.

    Unknown blockers invalidate the aggregate reset; a partial reset must never
    be advertised as the boundary at which *all* required capacity recovers.
    """
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        raise ValueError("checked_at must be timezone-aware")
    checked_at = checked_at.astimezone(UTC)
    bucket: object = None
    provider_blocked = False
    if isinstance(payload, dict):
        buckets = payload.get("rateLimitsByLimitId")
        if buckets is None:
            bucket = payload.get("rateLimits")
        elif isinstance(buckets, dict):
            bucket = buckets.get("codex")
        if "ordinaryUsageAllowed" in payload:
            provider_blocked = payload["ordinaryUsageAllowed"] is not True
    if not isinstance(bucket, dict) or bucket.get("limitId") not in (None, "codex"):
        bucket = {}
    reached = bucket.get("rateLimitReachedType")
    provider_blocked |= reached not in (None, "rate_limit_reached")
    spend_control = bucket.get("spendControlReached")
    provider_blocked |= spend_control is not None and spend_control is not False
    windows: list[WindowAvailability] = []
    for scope, minutes in ((LimitScope.FIVE_HOUR, 300), (LimitScope.WEEKLY, 10080)):
        candidates = [
            value
            for slot in ("primary", "secondary")
            if isinstance(value := bucket.get(slot), dict)
            and type(value.get("windowDurationMins")) is int
            and value["windowDurationMins"] == minutes
        ]
        windows.append(
            parse_window(
                scope, candidates[0] if len(candidates) == 1 else None, checked_at
            )
        )
    five_hour, weekly = windows
    blocking = tuple(window.scope for window in windows if window.available is not True)
    if reached == "rate_limit_reached" and not blocking:
        provider_blocked = True
    available = not blocking and not provider_blocked
    reason = Reason.AVAILABLE
    boundary = None
    if provider_blocked:
        reason = Reason.PROVIDER_BLOCKED
    elif blocking:
        failed = [
            window
            for window in windows
            if window.reason not in (Reason.AVAILABLE, Reason.EXHAUSTED)
        ]
        reason = failed[0].reason if failed else Reason.EXHAUSTED
        exhausted = [window for window in windows if window.available is False]
        if not failed and exhausted:
            boundary = max(
                window.provider_resets_at
                for window in exhausted
                if window.provider_resets_at is not None
            )
    return Availability(
        available, five_hour, weekly, blocking, checked_at, reason, boundary
    )
