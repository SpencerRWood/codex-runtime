## Development lifecycle

Use root [tool.wood.branching]: feature branches and Story PRs start from and target development. Development validates without publication/deployment. Main requires a separately approved release PR and pinned release workflow. Emergency hotfixes require incident/approval references and reconciliation into development.

# Repository guidance

- Use Wood Tools for Story, validation and delivery operations.
- This library owns Codex capacity inspection and reset normalization only.
- Unknown/malformed provider states fail closed. Do not infer recovery from time.
- Consumers own prompts, workflow state, durable deferral, buffers and attempts.
- Keep capacity imports independent of Dagster; preserve the valid code location.
- Tests must use offline providers/peers, without credentials or inference turns.
- Preserve the template's centralized validation, packaging and release contracts.
