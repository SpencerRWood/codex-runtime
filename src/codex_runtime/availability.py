"""Public read-only check; provider failures become safe normalized observations."""

from collections.abc import Callable
from datetime import UTC, datetime

from codex_runtime.io.readers import RateLimitProvider
from codex_runtime.models import Availability, Reason
from codex_runtime.transforms import normalize_rate_limits


def check_availability(
    provider: RateLimitProvider, *, clock: Callable[[], datetime] | None = None
) -> Availability:
    """Perform one fresh read; do not cache, retry, start turns, or spend credits."""
    failed = False
    try:
        payload = provider.read_rate_limits()
    except Exception:  # Provider exceptions may contain credentials; never expose them.
        payload = None
        failed = True
    checked_at = clock() if clock is not None else datetime.now(UTC)
    result = normalize_rate_limits(payload, checked_at=checked_at)
    if not failed:
        return result
    return Availability(
        False,
        result.five_hour,
        result.weekly,
        result.blocking_scopes,
        result.checked_at,
        Reason.PROVIDER_ERROR,
        None,
    )
