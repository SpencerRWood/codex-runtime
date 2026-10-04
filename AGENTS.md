# Repository guidance

- Use Wood Tools for Story, validation and delivery operations.
- This library owns Codex capacity inspection and reset normalization only.
- Unknown/malformed provider states fail closed. Do not infer recovery from time.
- Consumers own prompts, workflow state, durable deferral, buffers and attempts.
- Keep capacity imports independent of Dagster; preserve the valid code location.
- Tests must use offline providers/peers, without credentials or inference turns.
- Preserve the template's centralized validation, packaging and release contracts.
