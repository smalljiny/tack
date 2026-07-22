---
version: 4
name: stack-knip
description: Dead code analysis for JavaScript/TypeScript projects using knip. Detects unused files, exports, and npm dependencies. Activate when package.json exists and unused code or dependency cleanup is needed.
origin: SCE
capabilities: [analysis, typescript, knip]
---

# knip — Dead Code Analysis

Find unused files, exports, and npm dependencies in JS/TS projects.

## When to Activate

- `package.json` exists in the project root
- Need to find unused files or exports before refactoring
- Cleaning up unused npm dependencies
- Pre-commit dead code check

## Commands

```bash
pnpm knip                      # Default output
pnpm knip --reporter compact   # Compact format
pnpm knip --reporter json      # JSON for programmatic use
pnpm knip --no-exit-code       # CI warning-only mode
```

Generate report for refactor-cleaner agent:
```bash
pnpm knip --reporter json > .knip-report.json
```

## What knip Detects

- **Unused files**: Files not imported anywhere in the project
- **Unused exports**: Exported functions/types not consumed by other modules
- **Unused dependencies**: npm packages in `package.json` but never imported
- **Unused devDependencies**: Dev packages not referenced in config or code

## Output Interpretation

```
Unused files (5)
  src/old-helper.ts

Unused exports (3)
  src/utils.ts: unusedFunction, OldType

Unused dependencies (2)
  lodash  package.json:15
```

Each line is a safe removal candidate — verify before deleting.

## Configuration

Default behavior works for most projects. Customize in `knip.json` or `package.json`:

```json
{
  "knip": {
    "ignore": ["**/generated/**"],
    "ignoreDependencies": ["@types/*"]
  }
}
```

## Troubleshooting False Positives

Common causes:
- Dynamic imports (`import()`)
- Dependency injection containers
- Config files that load modules at runtime

Fix: add to `ignore` list or use `// knip-ignore` comment on the line.

## Usage Patterns

**Project health check:**
```bash
pnpm knip
```

**Pre-refactoring cleanup:**
```bash
pnpm knip --reporter compact
```

**CI pipeline (warning only):**
```bash
pnpm knip --no-exit-code
```

## Integration

After running knip, use the `refactor-cleaner` agent to safely remove identified dead code.
For circular dependency and architecture violations, use `stack-dependency-cruiser`.
The `adapter-dependency-analysis` skill orchestrates both tools for full project analysis.

## References

- [knip docs](https://knip.dev/)
