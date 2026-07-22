---
version: 2
name: stack-nextjs
description: Next.js 16+ and Turbopack patterns — incremental bundling, FS caching, dev speed, and when to use Turbopack vs webpack. Use when developing, debugging, or optimizing Next.js 16+ applications.
origin: ECC
capabilities: [language-patterns, typescript, nextjs]
---

# Next.js and Turbopack

Next.js 16+ uses Turbopack by default for local development: an incremental bundler written in Rust that significantly speeds up dev startup and hot updates.

> ECC 원본 스킬명: `nextjs-turbopack`. 하네스 컨벤션에 맞게 `stack-nextjs`로 명명.

## When to Activate

- Developing or debugging Next.js 16+ applications
- Diagnosing slow dev startup or HMR (Hot Module Replacement)
- Optimizing production bundles
- Evaluating Turbopack vs webpack trade-offs

## How It Works

- **Turbopack**: Incremental bundler for Next.js dev. Uses file-system caching so restarts are much faster (e.g. 5–14x on large projects).
- **Default in dev**: From Next.js 16, `next dev` runs with Turbopack unless disabled.
- **File-system caching**: Restarts reuse previous work; cache is typically under `.next`; no extra config needed for basic use.
- **Bundle Analyzer (Next.js 16.1+)**: Experimental Bundle Analyzer to inspect output and find heavy dependencies; enable via config or experimental flag (see Next.js docs for your version).

## Turbopack vs Webpack

| Mode | When to Use |
|------|------------|
| **Turbopack (default dev)** | Day-to-day development — faster cold start and HMR, especially in large apps |
| **Webpack (legacy dev)** | Only if you hit a Turbopack bug or rely on a webpack-only plugin in dev. Disable with `--webpack` or `--no-turbopack` (check your Next.js version) |
| **Production** | `next build` behavior depends on Next.js version — check official docs |

## Commands

```bash
next dev          # Dev server (Turbopack by default in Next.js 16+)
next build        # Production build
next start        # Production server
```

## Best Practices

- Stay on a recent Next.js 16.x for stable Turbopack and caching behavior.
- If dev is slow, verify you're on Turbopack (default) and the cache isn't being cleared unnecessarily.
- For production bundle size issues, use the official Next.js bundle analysis tooling for your version.
- Prefer App Router and server components where possible.

## References

- [Next.js docs](https://nextjs.org/docs)
- [Turbopack docs](https://turbo.build/pack/docs)
