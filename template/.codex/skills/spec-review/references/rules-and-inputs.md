# Rules and Inputs

## Rules to load

Load and apply where relevant:
- `.harness/rules/coding-style.md`
- `.harness/rules/security.md`
- `.claude/rules/common/development-workflow.md`

## Topic states and input sources

All topics — whether in backlog or active — are registered in `dev-context.json` from the moment
`/dev:spec` saves the draft. There is no distinction between "registered" and "unregistered" topics.

### Spec path resolution

Resolve spec path using priority order:

1. **Explicit argument** (preferred) — user provides the path directly
2. **Auto-resolution** — read from dev-context.json via CLI:
   ```bash
   node .harness/scripts/dev-context.js read --field=current_topic
   node .harness/scripts/dev-context.js read --topic=<current_topic> --field=spec
   ```
3. **User prompt** — if neither applies, ask for the spec path

### Expected dev-context.json shape

```json
{
  "current_topic": "<topic-name>",
  "topics": {
    "<topic-name>": {
      "phase": "spec",
      "status": "reviewing",
      "spec": "docs/_local/backlog/<topic-name>/spec.md",
      "specReview": null,
      "plan": null,
      "planReview": null,
      "currentStory": null,
      "createdAt": "<ISO 8601>",
      "updatedAt": "<ISO 8601>"
    }
  },
  "updatedAt": "<ISO 8601>"
}
```

Phase/status at review time is typically `spec:reviewing` (set by `/dev:spec` before invoking Codex).

### specReview update responsibility

After writing the report, Codex spec-review **owns** the `specReview` field update:

```bash
node .harness/scripts/dev-context.js set-field \
  --topic=<current_topic> \
  --field=specReview \
  --value=<report-path>
```

Do NOT set `specConfirmed` — that field no longer exists. State transitions are handled by
Claude `/dev:spec` via `update-state`, not by Codex.

### Report path

- Backlog topics: `docs/_local/backlog/<topic>/spec-review-<yymmddhhmmss>.md`
- Active topics: `docs/_local/active/<topic>/spec-review-<yymmddhhmmss>.md`

Where `<yymmddhhmmss>` is the current local datetime at review time.

## Suggested evidence sources

- The spec document itself (read in full)
- `docs/_local/dev-context.json` (for topic context)
- Related spec or design documents referenced in the spec's "관련 문서" section, if present
