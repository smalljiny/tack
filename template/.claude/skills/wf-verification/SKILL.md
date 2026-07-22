---
version: 4
name: wf-verification
description: Pass code quality gates in sequence before a PR or after feature completion. Used with the /flow-verify command.
origin: harness
category: dev-process
---

## When to Activate

- When running the `/flow-verify` command
- Before opening a PR
- When a feature implementation is deemed complete
- For local pre-check of CI/CD pipeline

## Verification Gate Sequence

Gates run in order. If any gate fails, do not proceed to the next.

```
[1] build → [2] type-check → [3] lint → [4] test → [5] security
```

### Gate 1: Build

```bash
pnpm build
```

On failure: call the `build-error-resolver` agent

### Gate 2: Type Check

```bash
pnpm tsc --noEmit
```

On failure: call the `build-error-resolver` agent

Do not bypass with `any` types. Resolve the root cause.

### Gate 3: Lint

```bash
pnpm lint
```

Fix auto-fixable errors first:
```bash
pnpm lint --fix
```

### Gate 4: Tests and Coverage

```bash
pnpm test
pnpm test:coverage
```

- All tests must pass
- Coverage must be 80% or higher

If coverage is below threshold: add missing tests and re-run

### Gate 5: Security Scan

```bash
pnpm audit
```

If CRITICAL or HIGH vulnerabilities are found: call the `security-reviewer` agent

## Output Format

```
Verification Results
━━━━━━━━━━━━━━━━━━━━━━━━━
✅ build        passed
✅ type-check   passed
✅ lint         passed
✅ test         passed (coverage: 87%)
✅ security     passed (vulnerabilities: 0)
━━━━━━━━━━━━━━━━━━━━━━━━━
All gates passed — ready to open a PR.
```

Or:

```
Verification Results
━━━━━━━━━━━━━━━━━━━━━━━━━
✅ build        passed
❌ type-check   failed
━━━━━━━━━━━━━━━━━━━━━━━━━
Errors:
  src/user.ts:34 - Type 'string' is not assignable to type 'number'

Calling build-error-resolver agent...
```

## Principles

1. **Respect the order**: run build → type → lint → test → security in sequence
2. **No bypassing**: do not ignore or skip gate failures
3. **Resolve root causes**: do not suppress with `any` types or `eslint-disable` comments
4. **PR only after full pass**: open a PR only when all gates have passed
