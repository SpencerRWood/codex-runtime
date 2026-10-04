"""Consumer contract regressions for every required capacity outcome."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from codex_runtime import (
    LimitScope,
    Reason,
    check_availability,
    normalize_rate_limits,
)

NOW = datetime(2026, 10, 3, 19, 30, tzinfo=UTC)
FIVE_RESET = int((NOW + timedelta(hours=2)).timestamp())
WEEK_RESET = int((NOW + timedelta(days=3)).timestamp())


def window(minutes: int, used: object, reset: object) -> dict[str, object]:
    return {"windowDurationMins": minutes, "usedPercent": used, "resetsAt": reset}


def payload(five: object = 20, weekly: object = 40) -> dict[str, object]:
    return {
        "rateLimits": {
            "limitId": "codex",
            "primary": window(300, five, FIVE_RESET),
            "secondary": window(10080, weekly, WEEK_RESET),
        }
    }


@pytest.mark.parametrize(
    ("five", "weekly", "scopes", "reset"),
    [
        (20, 40, (), None),
        (100, 40, (LimitScope.FIVE_HOUR,), FIVE_RESET),
        (20, 100, (LimitScope.WEEKLY,), WEEK_RESET),
        (100, 100, (LimitScope.FIVE_HOUR, LimitScope.WEEKLY), WEEK_RESET),
    ],
)
def test_required_capacity_outcomes(
    five: int, weekly: int, scopes: tuple[LimitScope, ...], reset: int | None
) -> None:
    result = normalize_rate_limits(payload(five, weekly), checked_at=NOW)
    assert result.available is (not scopes)
    assert result.five_hour.available is (five < 100)
    assert result.weekly.available is (weekly < 100)
    assert result.blocking_scopes == scopes
    assert result.reason == (Reason.EXHAUSTED if scopes else Reason.AVAILABLE)
    assert result.checked_at == NOW
    assert result.provider_resets_at == (
        datetime.fromtimestamp(reset, UTC) if reset else None
    )
    assert result.five_hour.provider_resets_at == datetime.fromtimestamp(
        FIVE_RESET, UTC
    )
    assert result.weekly.provider_resets_at == datetime.fromtimestamp(WEEK_RESET, UTC)


def test_latest_blocker_is_not_assumed_to_be_weekly() -> None:
    result = normalize_rate_limits(
        {
            "rateLimits": {
                "primary": window(10080, 100, FIVE_RESET),
                "secondary": window(300, 100, WEEK_RESET),
            }
        },
        checked_at=NOW,
    )
    assert result.provider_resets_at == datetime.fromtimestamp(WEEK_RESET, UTC)


@pytest.mark.parametrize(
    "used", [None, True, False, "20", -1, 101, 20.5, float("nan"), float("inf"), {}, []]
)
@pytest.mark.parametrize("scope", [LimitScope.FIVE_HOUR, LimitScope.WEEKLY])
def test_bad_percent_fails_closed(used: object, scope: LimitScope) -> None:
    result = normalize_rate_limits(
        payload(used, 40) if scope == LimitScope.FIVE_HOUR else payload(20, used),
        checked_at=NOW,
    )
    assert not result.available
    assert result.blocking_scopes == (scope,)
    assert result.reason == Reason.UNKNOWN_CAPACITY
    assert result.provider_resets_at is None


@pytest.mark.parametrize(
    "raw",
    [
        None,
        [],
        "bad",
        {},
        {"rateLimits": None},
        {"rateLimits": []},
        {"rateLimits": {"limitId": "other"}},
        {"rateLimitsByLimitId": {}},
        {"rateLimitsByLimitId": []},
    ],
)
def test_unknown_provider_shape_fails_closed(raw: object) -> None:
    result = normalize_rate_limits(raw, checked_at=NOW)
    assert not result.available
    assert result.five_hour.available is None
    assert result.weekly.available is None
    assert result.reason == Reason.UNKNOWN_CAPACITY


@pytest.mark.parametrize("minutes", [None, 15, 300.0, "300", True, 10080])
def test_missing_unknown_or_duplicate_window(minutes: object) -> None:
    result = normalize_rate_limits(
        {
            "rateLimits": {
                "primary": {"windowDurationMins": minutes, "usedPercent": 1},
                "secondary": window(10080, 40, WEEK_RESET),
            }
        },
        checked_at=NOW,
    )
    assert not result.available
    assert result.five_hour.reason == Reason.UNKNOWN_CAPACITY
    if minutes == 10080:
        assert result.weekly.reason == Reason.UNKNOWN_CAPACITY


@pytest.mark.parametrize(
    "reset",
    [
        True,
        "1800000000",
        0,
        -1,
        1e300,
        10**100,
        int(NOW.timestamp()),
        int(NOW.timestamp()) - 1,
    ],
)
@pytest.mark.parametrize("used", [20, 100])
def test_invalid_or_stale_reset_does_not_imply_recovery(
    reset: object, used: int
) -> None:
    result = normalize_rate_limits(
        {
            "rateLimits": {
                "primary": window(300, used, reset),
                "secondary": window(10080, 100, WEEK_RESET),
            }
        },
        checked_at=NOW,
    )
    assert not result.available
    assert result.reason == Reason.INVALID_RESET
    assert result.provider_resets_at is None
    assert result.five_hour.available is (False if used == 100 else None)


@pytest.mark.parametrize("weekly", [40, 100])
def test_exhausted_without_reset_does_not_return_partial_boundary(weekly: int) -> None:
    result = normalize_rate_limits(
        {
            "rateLimits": {
                "primary": window(300, 100, None),
                "secondary": window(10080, weekly, WEEK_RESET),
            }
        },
        checked_at=NOW,
    )
    assert result.five_hour.available is False
    assert result.reason == Reason.MISSING_RESET
    assert result.provider_resets_at is None


def test_available_windows_do_not_require_reset() -> None:
    result = normalize_rate_limits(
        {
            "rateLimits": {
                "primary": window(300, 0, None),
                "secondary": window(10080, 99, None),
            }
        },
        checked_at=NOW,
    )
    assert result.available
    assert result.provider_resets_at is None


def test_authoritative_codex_bucket_overrides_legacy_and_other_buckets() -> None:
    raw = payload(100, 100)
    raw["rateLimitsByLimitId"] = {
        "codex": payload()["rateLimits"],
        "other": payload(100, 100)["rateLimits"],
    }
    assert normalize_rate_limits(raw, checked_at=NOW).available
    raw["rateLimitsByLimitId"] = {"other": payload()["rateLimits"]}
    assert not normalize_rate_limits(raw, checked_at=NOW).available


@pytest.mark.parametrize("state", [False, None, "true", 1])
def test_explicit_permission_must_be_true(state: object) -> None:
    raw = payload()
    raw["ordinaryUsageAllowed"] = state
    result = normalize_rate_limits(raw, checked_at=NOW)
    assert not result.available
    assert result.reason == Reason.PROVIDER_BLOCKED
    assert result.provider_resets_at is None


@pytest.mark.parametrize("key", ["spendControlReached", "rateLimitReachedType"])
@pytest.mark.parametrize("state", [True, 0, "new_provider_denial", []])
def test_provider_denials_and_unknown_states_block(key: str, state: object) -> None:
    raw = {
        "rateLimits": {
            "primary": window(300, 20, FIVE_RESET),
            "secondary": window(10080, 40, WEEK_RESET),
            key: state,
        }
    }
    assert normalize_rate_limits(raw, checked_at=NOW).reason == Reason.PROVIDER_BLOCKED


def test_rate_limit_reached_agrees_with_window_exhaustion() -> None:
    raw = {
        "rateLimits": {
            "primary": window(300, 100, FIVE_RESET),
            "secondary": window(10080, 40, WEEK_RESET),
            "rateLimitReachedType": "rate_limit_reached",
        }
    }
    assert normalize_rate_limits(raw, checked_at=NOW).reason == Reason.EXHAUSTED
    raw["rateLimits"]["primary"] = window(300, 20, FIVE_RESET)
    assert normalize_rate_limits(raw, checked_at=NOW).reason == Reason.PROVIDER_BLOCKED


def test_timezone_normalization_and_naive_rejection() -> None:
    local = NOW.astimezone(timezone(timedelta(hours=-4)))
    assert normalize_rate_limits(payload(), checked_at=local).checked_at == NOW
    with pytest.raises(ValueError, match="timezone-aware"):
        normalize_rate_limits(payload(), checked_at=NOW.replace(tzinfo=None))


class StubProvider:
    def __init__(self, raw: object) -> None:
        self.raw = raw
        self.calls = 0

    def read_rate_limits(self) -> object:
        self.calls += 1
        if isinstance(self.raw, Exception):
            raise self.raw
        return self.raw


def test_provider_check_is_fresh_and_timestamped_after_read() -> None:
    provider = StubProvider(payload())

    def clock() -> datetime:
        assert provider.calls == 1
        return NOW

    result = check_availability(provider, clock=clock)
    assert result.available
    assert result.checked_at == NOW


def test_provider_failure_is_safe_and_blocks_both_windows() -> None:
    provider = StubProvider(RuntimeError("secret-token-example"))
    result = check_availability(provider)
    assert not result.available
    assert result.reason == Reason.PROVIDER_ERROR
    assert result.blocking_scopes == (LimitScope.FIVE_HOUR, LimitScope.WEEKLY)
    assert result.provider_resets_at is None
    assert "secret-token-example" not in repr(result)


@pytest.mark.parametrize("consumer", ["architecture-docs", "automerge-repair"])
def test_consumers_need_only_normalized_contract(consumer: str) -> None:
    result = check_availability(StubProvider(payload(100, 100)), clock=lambda: NOW)
    assert result.provider_resets_at is not None, consumer
    next_retry_at = result.provider_resets_at + timedelta(minutes=5)
    assert next_retry_at == datetime.fromtimestamp(WEEK_RESET, UTC) + timedelta(
        minutes=5
    )
