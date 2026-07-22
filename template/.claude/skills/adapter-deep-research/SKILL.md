---
version: 2
name: adapter-deep-research
description: >
  Multi-source deep research workflow using skill-registry search adapters.
  Searches the web via installed search-adapter skills (adapter-firecrawl, adapter-exa, etc.),
  synthesizes findings, and delivers cited reports with source attribution.
  Use when the user wants thorough research on any topic with evidence and citations.
  Does NOT require MCP configuration — uses skill-registry [search-adapter] discovery.
origin: harness
---

# adapter-deep-research

Produce thorough, cited research reports from multiple web sources using skill-registry
search-adapter skills. No MCP configuration required.

## When to Activate

- User asks to research any topic in depth
- Competitive analysis, technology evaluation, or market sizing
- Due diligence on companies, investors, or technologies
- Any question requiring synthesis from multiple sources
- User says "research", "deep dive", "investigate", or "what's the current state of"

**Prerequisites:**
- At least one search-adapter skill installed (adapter-firecrawl or adapter-exa)
- Corresponding API key set (`$FIRECRAWL_API_KEY` or `$EXA_API_KEY`)

## Workflow

### Step 0: Adapter Discovery

Load `.claude/skills/skill-registry/SKILL.md` and run its Discovery Procedure with
capability query `[search-adapter]`.

The registry returns a list of matching skills. Each entry contains:
- `name` — skill identifier (e.g. `adapter-exa`, `adapter-firecrawl`)
- `path` — path to the skill's `SKILL.md` (e.g. `.claude/skills/adapter-exa/SKILL.md`)
- `capabilities` — capability tags array

Read each matched skill's `SKILL.md` to load its Search Procedure before Step 3.

**Adapter Trust Model**: skill-registry는 `.claude/skills/*/SKILL.md`에서 `capabilities: [search-adapter]`로 등록된 스킬만 반환한다. 새 search-adapter 스킬을 추가하려면 코드 리뷰가 필요하며, 외부 API 키에 접근하는 커맨드를 실행한다. 신뢰할 수 없는 출처에서 받은 스킬 파일을 설치하지 말 것.

**Adapter Selection Policy**

| Adapters Found | Action |
|----------------|--------|
| 0 | Stop immediately: `search-adapter 스킬이 없습니다. adapter-firecrawl 또는 adapter-exa를 설치하세요.` |
| 1 | Use that adapter only |
| 2 or more | Use all adapters sequentially per sub-question; merge results and deduplicate |

**Deep-Read Adapter Selection** (used in Step 4)

Select the representative adapter from the **adapters that succeeded in Step 3**
(i.e., returned at least one result without a fatal error), using priority order:
`adapter-exa` > `adapter-firecrawl` > other adapters in discovery order.

If the top-priority adapter fails during content fetching (Step 4), fall back to the
next healthy adapter. If all healthy adapters fail content fetching, report the gap and
proceed with snippet-only content for those URLs.

**Sub-agent Delegation**

When sub-agents are used (Step 3 parallelism), the main session passes the adapter list
(name + SKILL.md path) explicitly in each sub-agent prompt. Sub-agents do **not**
re-query skill-registry.

**Partial Failure Policy**

| Failure Type | Action |
|--------------|--------|
| API key missing (`$KEY` unset) | Skip adapter, continue with others. Mark in report: `⚠️ <adapter>: API key not set` |
| HTTP 401 / 403 | Skip adapter, continue with others. Mark in report: `⚠️ <adapter>: authentication failed (HTTP 4xx)` |
| HTTP 429 (after adapter-level 3 retries) | Skip adapter, continue with others. Mark in report: `⚠️ <adapter>: rate limit exceeded` |
| Network timeout | Skip adapter, continue with others. Mark in report: `⚠️ <adapter>: request timed out` |
| HTTP 5xx / server error | Skip adapter, continue with others. Mark in report: `⚠️ <adapter>: server error (HTTP 5xx)` |
| Malformed / unparseable response | Skip adapter, continue with others. Mark in report: `⚠️ <adapter>: unexpected response format` |
| All adapters failed | Stop: `모든 search-adapter 호출이 실패했습니다. API 키와 네트워크를 확인하세요.` |

Failed adapter warnings appear in both the Methodology section and the report meta line.

### Step 1: Understand the Goal

Ask 1-2 quick clarifying questions:
- "What's your goal — learning, making a decision, or writing something?"
- "Any specific angle or depth you want?"

If the user says "just research it" — skip ahead with reasonable defaults.

### Step 2: Plan Research

Break the topic into 3-5 research sub-questions. Example:
- Topic: "Impact of AI on healthcare"
  - What are the main AI applications in healthcare today?
  - What clinical outcomes have been measured?
  - What are the regulatory challenges?
  - What companies are leading this space?
  - What's the market size and growth trajectory?

### Step 3: Execute Multi-Source Search

For EACH sub-question, call all discovered adapters sequentially. Follow each adapter's
**Search Procedure** section exactly (curl templates, error handling, retry logic).

**Adapter operation mapping:**

| Adapter | Search Operation | Params |
|---------|-----------------|--------|
| adapter-firecrawl | `/v1/search` | `query`, `limit: 8` |
| adapter-exa | `/search` | `query`, `numResults: 8`, `type: "auto"` (default; deep/deep-reasoning out of scope — 90s timeout) |

**Search strategy:**
- Use 2-3 different keyword variations per sub-question
- Mix general and news-focused queries
- Aim for 15-30 unique sources total across all adapters
- Prioritize: academic, official, reputable news > blogs > forums

**Parallelism decision:**

| Sub-questions | Execution |
|--------------|-----------|
| ≤ 3 | Main session: call adapters sequentially per sub-question |
| ≥ 4 OR broad topic | Sub-agents: group sub-questions, launch agents in parallel |

When using sub-agents: main session passes the adapter list (name + SKILL.md path) in each
agent's prompt. Sub-agents do not re-query skill-registry.

**Result merge and deduplication:**

1. Collect all results from all adapters into a single list using the standard schema
   (`query`, `results[]`, `source`, `operation`)
2. Deduplicate by normalized URL — when two entries share the same URL, keep the one with
   the longer snippet
3. Select top 5-8 URLs for Step 4 deep-reading:
   - Rank by snippet/summary relevance and length
   - Prefer academic, official, and reputable news sources
   - Blogs and forums as fallback

### Step 4: Deep-Read Key Sources

Fetch full content for the 5-8 selected URLs using the **representative adapter** selected
in Step 0 (priority: `adapter-exa` > `adapter-firecrawl` > other adapters in discovery order).

Follow the representative adapter's **Search Procedure** section for content fetching:

| Adapter | Content Operation |
|---------|-----------------|
| adapter-firecrawl | `/v1/scrape` | Single-URL — loop per URL |
| adapter-exa | `/contents` | JSON array input — batch all target URLs in one call |

Fetch all 5-8 selected URLs; read the 3-5 most relevant in depth, skim the rest.
Do not rely only on search snippets.

### Step 5: Synthesize

Write the research report using the template defined in **Output Contract** below.

Apply all Quality Rules (see below) when writing:
- Every claim must cite a source using inline markdown links `([Source Name](url))`
- Cross-reference key claims with multiple sources where possible
- Label estimates, projections, and opinions clearly

### Step 6: Deliver

Deliver the report using the file-save policy defined in **Output Contract** below:
- Short reports (≤ 3,000 chars): post full report in chat
- Long reports (> 3,000 chars): save to file, post executive summary + key takeaways in chat

If any adapters failed during Steps 3-4, include the failure warnings (`⚠️ <adapter>: <reason>`)
in both the report meta line and the Methodology section.

## Output Contract

### Report Template

```markdown
# [Topic]: Research Report
*Generated: YYYY-MM-DD | Sources: N | Adapters: [adapter1, adapter2] | Failed: [⚠️ adapter: reason]*

## Executive Summary
[3-5 sentence overview of key findings]

## 1. [First Major Theme]
[Findings with inline citations: ([Source Name](url))]

## 2. [Second Major Theme]
...

## Key Takeaways
- [Actionable insight 1]
- [Actionable insight 2]

## Sources
1. [Title](url) — one-line summary
2. ...

## Methodology
Searched [N] queries. Adapters used: [list]. Adapters failed: [⚠️ <adapter>: <reason>].
Sub-questions investigated: [list]. Sources analyzed: [M].
```

### Citation Format

Use inline markdown links: `([Source Name](url))`

Example: AI is transforming diagnostics ([Nature Medicine](https://...)).

### File-Save Policy

| Report length | Action |
|--------------|--------|
| ≤ 3,000 chars | Post full report in chat |
| > 3,000 chars | Save to `research-<topic>-<YYYYMMDDHHMMSS>.md`, post Executive Summary + Key Takeaways in chat |

**Default save directory**: current working directory (`./`).
Override with `$DEEP_RESEARCH_OUTPUT_DIR` environment variable.

**Topic sanitization** — normalize `<topic>` before constructing the filename:
replace `/`, `..`, and non-alphanumeric characters (except `-` and `_`) with `_`.
Example: `"AI/healthcare"` → `research-AI_healthcare-20260424.md`

### Search Scope Target

- Per sub-question per adapter: 8 results
- Total unique sources goal: 15-30

## Quality Rules

1. **Every claim needs a source.** No unsourced assertions.
2. **Cross-reference.** If only one source says it, flag it as unverified.
3. **Recency matters.** Prefer sources from the last 12 months.
4. **Acknowledge gaps.** If you couldn't find good info on a sub-question, say so.
5. **No hallucination.** If you don't know, say "insufficient data found."
6. **Separate fact from inference.** Label estimates, projections, and opinions clearly.

## Examples

```
"Research the current state of nuclear fusion energy"
"Deep dive into Rust vs Go for backend services in 2026"
"Research the best strategies for bootstrapping a SaaS business"
"What's happening with the US housing market right now?"
"Investigate the competitive landscape for AI code editors"
```
