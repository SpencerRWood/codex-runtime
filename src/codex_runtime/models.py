"""Immutable consumer-facing capacity observations; all timestamps are UTC."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class LimitScope(StrEnum):
    FIVE_HOUR = "five_hour"
    WEEKLY = "weekly"


class Reason(StrEnum):
    AVAILABLE = "available"
    EXHAUSTED = "exhausted"
    UNKNOWN_CAPACITY = "unknown_capacity"
    MISSING_RESET = "missing_reset"
    INVALID_RESET = "invalid_reset"
    PROVIDER_ERROR = "provider_error"
    PROVIDER_BLOCKED = "provider_blocked"


@dataclass(frozen=True)
class WindowAvailability:
    scope: LimitScope
    available: bool | None
    used_percent: int | None
    provider_resets_at: datetime | None
    reason: Reason


@dataclass(frozen=True)
class Availability:
    available: bool
    five_hour: WindowAvailability
    weekly: WindowAvailability
    blocking_scopes: tuple[LimitScope, ...]
    checked_at: datetime
    reason: Reason
    provider_resets_at: datetime | None
