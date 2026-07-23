---
version: 3
description: Scaffold language-specific rule files (coding-style/security/testing) under .tack/rules/<language>/. Generative, not template copy.
category: harness-management
---

# /add-language-rules

Add new language or framework rules to the harness by generating three rule files under `.tack/rules/<language>/`. Claude writes the files based on the language's idioms, security conventions, and testing practices — not from a fixed template.

> **Note**: Generated files go to `.tack/rules/<language>/` (shared Claude + Codex), not `.claude/rules/`.

## Usage

```
/add-language-rules <language>
```

**Examples:**
```
/add-language-rules rust
/add-language-rules react
/add-language-rules go
/add-language-rules python
```

If `$ARGUMENTS` is empty, use `AskUserQuestion` to ask "어떤 언어 또는 프레임워크의 규칙을 추가할까요?" with options such as:
- rust (Recommended) — Rust 규칙
- go — Go 규칙
- python — Python 규칙 (`stack-python` 스킬이 이미 있음)
- 직접 입력 — 다른 언어 이름 입력

## Execution Flow

### 1. Parse and Normalize Language Name

Read `$ARGUMENTS` and normalize to lowercase with hyphens:
- `React Native` → `react-native`
- `Go` → `go`
- `C++` → `cpp`

After normalization, verify the result contains only `[a-z0-9-]` characters.
If the result contains `.`, `/`, `\`, `..`, or any character outside `[a-z0-9-]`, stop immediately and report:
```
유효하지 않은 언어 이름입니다. 영문 소문자, 숫자, 하이픈만 허용됩니다.
```

### 2. Check for Existing Rules

Check if `.tack/rules/<language>/` already exists (substitute actual language name — e.g. `ls .tack/rules/rust/ 2>/dev/null`).

If the directory exists, use `AskUserQuestion` to ask:
- (Recommended) 건너뛰기 — 기존 규칙이 이미 있음
- 덮어쓰기 — 기존 파일을 새 초안으로 교체

If user selects 건너뛰기, stop. Otherwise proceed.

### 3. Load Reference Structure

Read the following common rule files as section-structure references:
- `.tack/rules/coding-style.md`
- `.tack/rules/security.md`
- `.tack/rules/testing.md`

Use these to understand the section headings and level of detail expected in each file type. Do not copy content — generate language-specific content.

### 4. Generate Rule Files

Create `.tack/rules/<language>/` and write three files. Each file must include `version: 1` frontmatter.

Claude writes each file based on the target language's characteristics:

**`coding-style.md`** — Naming conventions, idioms, formatting rules, and readability guidelines specific to this language's community standards (e.g., Rust's ownership conventions, Go's `gofmt` style, React's component naming).

**`security.md`** — Common vulnerability patterns and their mitigations specific to this language or framework (e.g., memory safety in Rust, SQL injection in ORM usage, XSS in React, dependency supply-chain risks).

**`testing.md`** — Testing conventions, framework choices, and patterns for this language (e.g., `cargo test` + property testing in Rust, `testing` package in Go, React Testing Library patterns, pytest fixtures in Python).

Each file must begin with:
```markdown
---
version: 1
---
```

### 5. Link to Related Skills

After generating the files, check if a relevant stack skill exists and suggest it:

| Language / Framework | Related skill |
|---------------------|---------------|
| Python | `stack-python`, `stack-python-test` |
| React / Next.js | `stack-frontend`, `stack-nextjs` |
| Node.js / Fastify | `stack-backend`, `stack-fastify` |
| TypeScript | `.tack/rules/typescript/` already exists |
| PostgreSQL | `stack-postgres`, `stack-db-migrations` |
| Docker | `stack-docker` |
| LangChain | `stack-langchain` |

If a matching skill exists, output:
```
관련 스킬이 있습니다: <skill-name>
SKILL.md를 참조하면 더 상세한 패턴을 확인할 수 있습니다.
```

### 6. Output Reload Guidance

After Step 5 (regardless of whether a related skill was found), print the following final line as the last output of this command:

```
CLAUDE.md에 자동 로드 적용은 /flow-init 재실행
```

This line is informational. Do not invoke `/flow-init` automatically, do not call the Bash or Task tools to run it, and do not load the flow-init skill — the user controls when to rerun `/flow-init` to refresh the CLAUDE.md `@import` block.

## Non-goals

- `hooks.md` and `patterns.md` are **not** generated — scope is intentionally limited to the three files above
- Codex-side synchronization is not triggered — `.tack/rules/<language>/` is already shared (Claude + Codex read from the same path)
- `.claude/rules/` is not modified — generated files go to `.tack/rules/` only
