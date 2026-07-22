---
version: 2
name: flow-verify
description: Run the full verification gate before generating the reference document. Checks build, type-check, lint, test, and security in order.
origin: harness
user-invocable: true
---

# /flow-verify

All verification gates must pass before `/flow-docs` generates the reference document.

## Execution Flow

Load `.claude/skills/wf-verification/SKILL.md` and follow its process.

## Next Steps

After all gates pass: run `/flow-docs` to generate the reference document and commit, then `/flow-pr` and `/flow-done`.
