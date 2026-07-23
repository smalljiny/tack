---
version: 5
name: skill-registry
description: >
  Use this skill whenever a command or skill needs to dynamically discover which
  skill to load based on one or more capability tags rather than a hardcoded name.
  Load it when a user asks Claude to "find the right skill for X", when a command
  needs to select among multiple candidate skills at runtime, or when implementing
  a new search-adapter skill that must conform to the adapter pattern contract.
  Do NOT load for direct skill lookups (name already known) or for wf-* / meta-*
  skills that follow the direct-load pattern.
origin: harness
---

# skill-registry

A standard procedure for capability-based skill discovery. Commands and skills call
this registry when they need to find the right skill dynamically rather than hardcoding
a skill name.

## When to Activate

Load this skill when:

- A command must select a skill at runtime based on what the user needs (e.g. "search the web" could resolve to `firecrawl-search` or `exa-search`)
- A new skill must conform to the search-adapter pattern (see [Adapter Pattern](#adapter-pattern) below)
- You need to enumerate all skills registered for a given capability tag

Do **not** load this skill when:
- The skill name is already known and hardcoded in the calling command
- The skill is a `wf-*` or `meta-*` skill (those follow the direct-load pattern)

---

## Discovery Procedure

Execute the following 4 steps in order to resolve a capability query to a skill.

### Step 1 — Glob all SKILL.md files

```
Glob pattern: .claude/skills/*/SKILL.md
```

This returns a list of paths such as:
```
.claude/skills/stack-python/SKILL.md
.claude/skills/stack-fastify/SKILL.md
...
```

### Step 2 — Read frontmatter from each candidate

For each path returned by Step 1, Read the file and extract the YAML frontmatter block
(the content between the first pair of `---` delimiters). Parse the `capabilities:` field
as a YAML sequence. If the `capabilities:` key is absent, skip this skill silently
(see [Missing Capabilities Handling](#missing-capabilities-handling)).

Frontmatter fields of interest:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Skill identifier |
| `description` | string | Human-readable trigger description |
| `capabilities` | string[] | Capability tags (optional) |

### Step 3 — Filter by capabilities (AND logic)

A skill matches the query only if **all** requested capability tags are present in its
`capabilities` array.

```
query: [language-patterns, python]

stack-python capabilities: [language-patterns, python]      → MATCH
stack-fastify capabilities: [language-patterns, typescript, fastify] → NO MATCH (missing python)
stack-postgres capabilities: [database, postgres]           → NO MATCH
```

### Step 4 — Return matches

For each matching skill, return:

```
{
  name: string,           // from frontmatter
  path: string,           // SKILL.md file path
  description: string,    // from frontmatter
  capabilities: string[]  // from frontmatter
}
```

If zero matches are found, surface a clear message:
```
No skill found matching capabilities: [<tag>, <tag>].
Available tags: run Glob + Read pass to enumerate.
```

If multiple matches are found, return all and let the caller decide (priority policy is
out of scope for this registry — see Out of Scope).

---

## Capabilities Field Specification

The `capabilities:` field is an **optional** YAML sequence in a SKILL.md frontmatter.

```yaml
capabilities: [group-tag, specific-tag, ...]
```

### Rules

1. Values are lowercase kebab-case strings.
2. Every skill that declares capabilities **must** include at least one group tag from the taxonomy below.
3. Specific tags narrow the skill within its group — include as many as relevant.
4. Specific tags may appear in multiple groups (e.g. `typescript` in both `language-patterns` and `analysis`). Use the group tag in your query to disambiguate: `[language-patterns, typescript]` returns language skills; `[analysis, typescript]` returns analysis tools.
5. Order within the array does not matter.
6. `wf-*` and `meta-*` skills intentionally omit this field; they use the direct-load pattern.

### Taxonomy

| Group Tag | Meaning | Example Specific Tags |
|-----------|---------|----------------------|
| `language-patterns` | Language/framework implementation guidance | `python`, `typescript`, `fastify`, `react`, `nextjs`, `langchain`, `claude-api`, `backend` |
| `testing` | Test strategy, frameworks, TDD support | `python`, `playwright`, `jest`, `vitest` |
| `database` | Data storage, queries, schema, migrations | `postgres`, `mysql`, `migrations`, `redis` |
| `analysis` | Static analysis, dead-code detection, dependency graphs | `typescript`, `knip`, `dependency-cruiser` |
| `deployment` | CI/CD, containerization, infrastructure, release | `docker`, `kubernetes`, `github-actions` |
| `search-adapter` | Web/document search adapters (adapter pattern required — see below) | `firecrawl`, `exa`, `tavily` |

---

## Missing Capabilities Handling

When reading a SKILL.md whose frontmatter does **not** contain a `capabilities:` key:

- **Skip silently** — do not log, warn, or surface the skill to the caller.
- Continue to the next file in the Glob result set.

This allows `wf-*`, `meta-*`, and any other direct-load-only skills to coexist in
`.claude/skills/` without polluting registry queries.

---

## Query Patterns

### Pattern 1 — Language / framework lookup

```
Query capabilities: [language-patterns, fastify]

Resolves to: stack-fastify/SKILL.md
Use case: "I need Fastify implementation patterns"
```

Steps:
1. Glob `.claude/skills/*/SKILL.md`
2. Read each — extract `capabilities`
3. Filter: must contain both `language-patterns` AND `fastify`
4. Return `stack-fastify` (single match)

### Pattern 2 — Analysis tool lookup (specific tag)

```
Query capabilities: [analysis, knip]

Resolves to: stack-knip/SKILL.md
Use case: "Find the dead-code analysis skill"
```

Steps:
1. Glob `.claude/skills/*/SKILL.md`
2. Read each — extract `capabilities`
3. Filter: must contain both `analysis` AND `knip`
4. Return `stack-knip` (single match)

> Tip: `[analysis, typescript]` returns both `stack-knip` and `stack-dependency-cruiser`
> (multi-match). Add the tool-specific tag (`knip` or `dependency-cruiser`) to pin to one.

### Pattern 3 — Search adapter selection

```
Query capabilities: [search-adapter]

Resolves to: any installed search-adapter skill (e.g. firecrawl-search, exa-search)
Use case: A command needs to perform a web search without knowing which adapter is installed
```

Steps:
1. Glob `.claude/skills/*/SKILL.md`
2. Read each — extract `capabilities`
3. Filter: must contain `search-adapter`
4. Return all matches — the calling command picks one (e.g. first found, or user preference)

### Multi-match note

Some queries intentionally return multiple skills. For example:

- `[language-patterns, python]` matches both `stack-python` and `stack-claude-api`
  (the Claude API skill includes Python SDK patterns). Use `[language-patterns, python, claude-api]`
  to target the Claude API skill specifically, or `[language-patterns, python]` and pick the
  first non-claude-api result for general Python patterns.
- `[language-patterns, typescript]` matches 6+ skills. Add a framework tag to narrow:
  `[language-patterns, typescript, fastify]`, `[language-patterns, typescript, react]`, etc.

---

## Adapter Pattern

Skills that implement the `search-adapter` capability must follow this contract so that
any calling command can use them interchangeably.

### Required capabilities declaration

```yaml
capabilities: [search-adapter, <provider-tag>]
```

`<provider-tag>` is the provider name (e.g. `firecrawl`, `exa`, `tavily`).

### Required SKILL.md sections

Every search-adapter skill **must** include all of the following `##` sections:

| Section | Purpose |
|---------|---------|
| `## When to Activate` | Triggering conditions and prerequisites |
| `## Search Procedure` | Step-by-step instructions Claude follows to execute a search |
| `## Response Format` | Minimum required fields in the returned result (see below) |
| `## Rate Limits & Error Handling` | Quota, retry, and fallback behaviour |

### Minimum response format

The `## Response Format` section must define an output structure that includes at minimum:

```
{
  query: string,         // the search query submitted
  results: [
    {
      title: string,
      url: string,
      snippet: string    // brief excerpt or summary
    }
  ],
  source: string         // adapter name (e.g. "firecrawl", "exa")
}
```

Additional fields are allowed; removing required fields breaks calling commands.

### Implementation status

Two search-adapter skills are implemented and registered in this harness:
`adapter-firecrawl` (`capabilities: [search-adapter, firecrawl]`) and
`adapter-exa` (`capabilities: [search-adapter, exa]`). Additional providers (e.g. `tavily`)
follow the same adapter contract documented in this section as separate topics.

---

## Out of Scope

- **Priority policy for multiple matches** — when >1 skill matches a query, the registry
  returns all matches. Selection logic belongs in the calling command, not the registry.
- **Node.js registry script** — `.tack/scripts/registry.js` is not part of this implementation.
- **wf-* / meta-* capability tagging** — these skill families use the direct-load pattern intentionally.
- **deep-research redesign** — separate topic.
