---
version: 4
name: stack-dependency-cruiser
description: Architecture and dependency analysis for JavaScript/TypeScript projects using dependency-cruiser. Detects circular dependencies, layer violations, orphan modules, and generates dependency graphs. Activate when package.json exists and circular deps or architecture validation is needed.
origin: SCE
capabilities: [analysis, typescript, dependency-cruiser]
---

# dependency-cruiser — Architecture & Dependency Analysis

Detect circular dependencies, architecture violations, and orphan modules in JS/TS projects.

## When to Activate

- `package.json` exists in the project root
- Investigating circular dependency errors or build issues
- Validating architecture layer rules before/after refactoring
- Generating dependency graphs for documentation or impact analysis

## Commands

```bash
pnpm deps:check           # Validate all dependency rules
pnpm deps:check:ci        # CI mode — detailed error output, exit 1 on violations
pnpm deps:graph           # Generate dependency-graph.svg (module level)
pnpm deps:graph:archi     # Generate architecture-graph.svg (package level)
pnpm deps:report          # Generate dependency-report.html (interactive)
pnpm deps:focus -- <path> # Analyze deps to/from a specific module
```

Generate report for refactor-cleaner agent:
```bash
pnpm deps:check 2>&1 | tee .deps-report.txt
```

## What dependency-cruiser Detects

- **Circular dependencies**: A → B → A chains that cause build/runtime issues
- **Architecture violations**: Layer rules (e.g. types → utils → domain), app-to-app deps
- **Orphan modules**: Files with no imports and no importers
- **devDependency leaks**: Dev packages imported in production code
- **Test code in production**: Test file imports in non-test code

## Output Interpretation

```
error no-circular: src/a.ts → src/b.ts → src/a.ts
```
- `error` / `warn` / `info`: Severity level
- `no-circular`: Rule name from `.dependency-cruiser.cjs`
- Path shows the full violation chain

Exit code 1 if any `error`-level violations found, 0 if clean.

## Architecture Rules

Define rules in `.dependency-cruiser.cjs`:

```javascript
// Example layer rules
forbidden: [
  { name: 'no-circular', severity: 'error', from: {}, to: { circular: true } },
  { name: 'no-app-to-app', severity: 'error',
    from: { path: '^apps/' }, to: { path: '^apps/', pathNot: '^$FROM' } },
]
```

### Common Layer Patterns

```
types-* packages  →  No internal package dependencies
utils-* packages  →  No domain package dependencies
apps/*            →  No direct dependencies on other apps
```

## Usage Patterns

**Full project health check:**
```bash
pnpm deps:check
pnpm deps:graph:archi
```

**Pre-refactoring impact analysis:**
```bash
pnpm deps:focus -- packages/utils/src/format.ts
pnpm deps:check
```

**CI pipeline:**
```bash
pnpm deps:check:ci   # Fails build on violations
```

## Performance

Typical run time ~2s with caching enabled. Enable in `.dependency-cruiser.cjs`:

```javascript
options: {
  cache: {
    folder: 'node_modules/.cache/dependency-cruiser',
    strategy: 'content'
  }
}
```

If `deps:check` is slow, verify caching is configured.

## Troubleshooting

**"No circular dependencies found" but build fails:**
```bash
# Check for dynamic imports not detected by static analysis
grep -r "import(" apps/ packages/ --include="*.ts"
```

## Integration

After running, use the `refactor-cleaner` agent to safely fix violations.
For unused files and exports, use `stack-knip`.
The `adapter-dependency-analysis` skill orchestrates both tools for full project analysis.

## References

- [dependency-cruiser docs](https://github.com/sverweij/dependency-cruiser)
- Project config: `.dependency-cruiser.cjs`
