# Repository guidance

## Branching strategy

- This repository uses **trunk-based development**. Create short-lived change branches from current `main` and target PRs to `main`.
- Follow the [canonical branching and delivery policy](https://github.com/SpencerRWood/codex-config/blob/main/docs/branching-policy.md), available through the installed codex-config source path. Verify the strategy, release association, fetched base and PR target before implementation and record them in Story evidence. Story completion does not authorize publication or deployment; retain existing review, CI, security and rollback requirements.

- Use Wood Tools for Story, validation and delivery operations.
- This library owns Codex capacity inspection and reset normalization only.
- Unknown/malformed provider states fail closed. Do not infer recovery from time.
- Consumers own prompts, workflow state, durable deferral, buffers and attempts.
- Keep capacity imports independent of Dagster; preserve the valid code location.
- Tests must use offline providers/peers, without credentials or inference turns.
- Preserve the template's centralized validation, packaging and release contracts.
