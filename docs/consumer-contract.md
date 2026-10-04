# Shared capacity integration contract

Story 470 / AD-R1-01 establishes one provider checker for architecture-docs and
automerge-repair. Consumer runtime integration belongs to their later Stories;
this contract adds no execution or scheduling to either consumer.

Both consumers import `AppServerProvider` and `check_availability` from
`codex_runtime`, pin a delivered library release/revision and lockfile, and use
the same authenticated account/runtime as their later Codex execution. They
must not parse quota responses, CLI status text, error prose or session logs.
They consume only the normalized fields and recheck before execution.

| Consumer | Available | Exhausted with known aggregate reset | Unknown/reset unavailable/error |
| --- | --- | --- | --- |
| architecture-docs | May run optional narrative enrichment; deterministic collection/reconciliation remains independent. | Persist deferred narrative work with `next_retry_at = provider_resets_at + five minutes`. | Keep enrichment deferred with the failure reason; deterministic work continues. |
| automerge-repair | May proceed through its own policy/approval gates. | Persist incident deferral with the same five-minute buffer; consume no repair attempt. | Remain deferred under consumer policy and approval gates; consume no repair attempt. |

Example consumer-owned calculation:

```python
from datetime import timedelta
from codex_runtime import AppServerProvider, check_availability

capacity = check_availability(AppServerProvider())
next_retry_at = None
if not capacity.available and capacity.provider_resets_at is not None:
    next_retry_at = capacity.provider_resets_at + timedelta(minutes=5)
```

The caller persists deferral before ending the current work unit. A None
`next_retry_at` is not immediate execution permission. At the boundary, reread
capacity and preserve deferral if availability remains false. Workflow state,
retry scheduling/backoff for unknown failures, repair attempts, prompts, account
provisioning and human approvals stay in the consumer. The library never sleeps
until a quota reset or creates Dagster runs.

The offline contract tests demonstrate identical normalized observations for
these two consumers. They do not claim live consumer deployment or live provider
access. architecture-docs has no local checkout in this implementation batch;
its integration contract is maintained here for its foundation Story.
