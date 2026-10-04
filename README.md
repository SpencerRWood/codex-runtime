# codex-runtime

Shared, typed Python contract for Codex five-hour and weekly capacity. Execution
is permitted only when both windows are confirmed available. This library owns
capacity inspection and reset normalization; consumers own workflow state,
durable deferral, prompts, approvals and attempt accounting.

Created directly from the tracked files of
`SpencerRWood/template-python-dagster` at
`2b7d901e63095def72171397e3f5b99d457497d3`. The renamed `codex_runtime` package
retains the template's Python 3.14, Dagster, typed src layout, Hatch packaging,
Ruff, strict mypy, pytest, pre-commit and centralized validation/release callers.
Coverage validation is explicitly enabled in the shared release contract to
enforce the template's existing 90% floor on this fail-closed capability.
The unused example asset/job/schedule and placeholder transforms are replaced
by the library. `codex_runtime.dagster.definitions:defs` is a valid, empty code
location: this shared contract schedules no consumer workflows.

## Usage

Install the reviewed release of `codex-runtime` in each consumer. Before a
release exists, a local checkout can be installed for integration testing with
`uv pip install /path/to/codex-runtime`. Do not depend on an unreviewed branch
in deployment; pin the delivered release/revision in the consumer's lockfile.

```python
from codex_runtime import AppServerProvider, check_availability

capacity = check_availability(AppServerProvider(timeout_seconds=15))
if capacity.available:
    # Consumer may execute its own work.
    pass
elif capacity.provider_resets_at is not None:
    # Consumer durably defers until this provider boundary plus five minutes.
    pass
else:
    # Consumer remains deferred: no reliable all-windows reset is known.
    pass
```

`AppServerProvider` requires an installed Codex CLI and its existing authenticated
ChatGPT account in the runtime environment. It performs the stdio initialization
handshake and one `account/rateLimits/read`, with a total timeout, 64 KiB line
limit and 100-message response bound, then terminates/reaps its subprocess.
It starts no thread or inference turn, consumes no reset credit, retries nothing,
and does not read credentials itself or return raw errors. Synchronous API calls
belong in sync workers; async consumers can use `await asyncio.to_thread(...)`.
The Docker image is a Dagster code-location scaffold; it does not bundle Codex
or provision authentication. Consumers supply the execution runtime.

The transport follows the [official Codex app-server documentation](https://learn.chatgpt.com/docs/app-server).
The local CLI-generated `GetAccountRateLimitsResponse` schema was also inspected
for permission and spend-control fields. Windows are selected by explicit
`windowDurationMins` values 300 and 10080, independent of primary/secondary order.
Other durations, missing windows and duplicate durations fail closed. The
`codex` entry in `rateLimitsByLimitId` is authoritative when the map is present;
the legacy `rateLimits` view is used only when that map is absent/null. Other
metered buckets and purchased/unlimited credits cannot bypass either window.
Provider permission denials/unknown explicit permission, spend-control denials,
and inconsistent or unrecognized limit-reached states also block execution.

## Normalized result

| Field | Meaning |
| --- | --- |
| `available` | True only when both windows are confirmed available and no provider denial applies. |
| `five_hour`, `weekly` | Immutable `WindowAvailability` with scope, tri-state availability, usage percent, provider reset and reason. `None` availability means unknown, never permission. |
| `blocking_scopes` | Required windows that are exhausted or unconfirmed; provider-wide denials are reported separately in `reason`. |
| `checked_at` | Timezone-aware UTC observation time, recorded after the provider read. |
| `reason` | `available`, `exhausted`, `unknown_capacity`, `missing_reset`, `invalid_reset`, `provider_error`, or `provider_blocked`. |
| `provider_resets_at` | Latest blocking reset only when all blockers have reliable boundaries; otherwise None. |

Usage must be an integer in 0..100; 100 means exhausted. Resets are positive Unix
seconds normalized to UTC, with past/equal-time or malformed resets rejected.
An available window can omit its optional reset. An exhausted window without a
reset still blocks, but no aggregate recovery time can be claimed. Unknown data
or errors never imply recovery, even when another window has a known reset.
Recheck immediately before execution: this is an observation, not a capacity
reservation, and crossing a reset does not itself establish availability.

`RateLimitProvider` supports an injected provider for other transports and
offline tests. `normalize_rate_limits(payload, checked_at=...)` accepts the RPC
**result**, not its envelope. All provider-specific decoding stays here.

## Consumers

See [the shared consumer contract](docs/consumer-contract.md) for
architecture-docs and automerge-repair. Both compute `next_retry_at` as the latest
blocking provider reset plus five minutes and persist their own deferral.
Neither implements a duplicate provider checker. An unknown aggregate boundary
requires a consumer-owned failure/deferral policy, never an invented reset.

## Development and packaging

```sh
uv sync --frozen --group dev
wood repo validate --json
uv build
uv run dagster dev -m codex_runtime.dagster.definitions
```

Contract tests cover both available, each window exhausted, both exhausted with
different resets, malformed/unknown capacity, missing/stale/invalid resets,
provider denials/errors and offline app-server handshake/timeout/cleanup.
No test needs credentials, network capacity reads or Codex inference.

```sh
docker build -t codex-runtime .
docker run --rm -e DAGSTER_GRPC_PORT=4000 -p 4000:4000 codex-runtime
```

Infrastructure owns deployment, runtime secrets and workspace registration.
Semantic release owns versions/tags/releases using the existing
`SpencerRWood/workflows` v1 callers. Initial library delivery does not require
deploying a long-running code location.
