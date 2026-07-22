---
version: 7
name: adapter-exa
description: Search-adapter skill that calls Exa REST API via Bash curl. Loaded by skill-registry with [search-adapter, exa] tags. Requires $EXA_API_KEY. Provides /search, /contents, /answer, and /findSimilar operations.
origin: harness
capabilities: [search-adapter, exa]
---

# adapter-exa

Targets Exa REST API at `https://api.exa.ai`.

## When to Activate

**Activate when:**
- `$EXA_API_KEY` environment variable is set
- skill-registry query `[search-adapter, exa]` requests this adapter
- Web search or grounded LLM answers are needed and Exa API access is available

**Do NOT activate when:**
- `$EXA_API_KEY` is unset or empty — see Rate Limits & Error Handling
- MCP Exa tool is already configured — use existing MCP path instead
- SSE streaming is required — outside this skill's scope

**`search-adapter` contract scope:** `/search`, `/contents`, and `/findSimilar` conform to the standard `search-adapter` response schema (`query/results[]/source/operation`). `/answer` uses a separate Answer schema (see `## Response Format`) and is NOT interchangeable with other `search-adapter` outputs. Use `/answer` only when the caller explicitly handles the Answer schema.

## Search Procedure

All requests use base URL `https://api.exa.ai`, authentication header `x-api-key: $EXA_API_KEY`, and default timeout `--max-time 30`. Timeout overrides are noted per-operation below.

> **Security note:** `$EXA_API_KEY` appears as a `-H` argument in curl command lines. On shared systems, other users may see it via `ps aux`. In single-user developer environments this risk is acceptable (same pattern as `adapter-firecrawl`). On shared servers, prefer injecting the key via `curl -K -`.

Use `jq -cn --arg val "$VALUE" '{field: $val}'` to safely escape user input before passing to curl.

### /search — Web Search

**Input parameters:**
- `QUERY` (string, required): search query
- `TYPE` (string, required): Exa search type (`neural`, `keyword`, `auto`, `deep`, `deep-reasoning`)
- `NUM_RESULTS` (integer, optional, default 10): number of results to return

**Timeout:** `--max-time 30` for standard types; `--max-time 90` for `deep` and `deep-reasoning`.

**curl template (with 429 retry loop):**
```bash
case "$TYPE" in deep|deep-reasoning) TIMEOUT=90 ;; *) TIMEOUT=30 ;; esac

RESP_FILE=$(mktemp)
trap 'rm -f "$RESP_FILE"' EXIT
for attempt in 1 2 3; do
  HTTP_CODE=$(curl -s --max-time "$TIMEOUT" -X POST https://api.exa.ai/search \
    -H "x-api-key: $EXA_API_KEY" \
    -H "Content-Type: application/json" \
    -o "$RESP_FILE" -w "%{http_code}" \
    -d "$(jq -cn --arg q "$QUERY" --arg t "$TYPE" --argjson n "${NUM_RESULTS:-10}" \
          '{query: $q, type: $t, numResults: $n,
            contents: {text: true, highlights: {numSentences: 3, highlightsPerUrl: 3}, summary: true}}')")
  RESPONSE=$(cat "$RESP_FILE")
  if [ "$HTTP_CODE" != "429" ]; then break; fi
  if [ "$attempt" -lt 3 ]; then sleep $((2 ** attempt)); fi
done
# $RESPONSE and $HTTP_CODE are available after the loop
```

**Raw response fields:**
- `results[].title` — page title
- `results[].url` — page URL
- `results[].highlights[]` — extracted relevant text snippets
- `results[].text` — full page text
- `results[].summary` — LLM-generated summary

**Field mapping:**

| Normalized field | Source field | Rule |
|------------------|--------------|------|
| `title` | `results[].title` | Fallback: extract domain from URL |
| `url` | `results[].url` | As-is |
| `snippet` | `results[].highlights[0]` | Fallback: first 300 chars of `text`; then `summary` |

---

### /contents — URL Content Extraction

**Input parameters:**
- `URLS_JSON` (JSON array string, required): JSON array of URLs to fetch. Single URL must be wrapped in an array: `'["https://example.com"]'`

**Note:** The normalized `query` field in the Standard schema is populated with the first URL in the batch (`URLS_JSON[0]`).

**curl template (with 429 retry loop):**
```bash
RESP_FILE=$(mktemp)
trap 'rm -f "$RESP_FILE"' EXIT
for attempt in 1 2 3; do
  HTTP_CODE=$(curl -s --max-time 30 -X POST https://api.exa.ai/contents \
    -H "x-api-key: $EXA_API_KEY" \
    -H "Content-Type: application/json" \
    -o "$RESP_FILE" -w "%{http_code}" \
    -d "$(jq -cn --argjson ids "$URLS_JSON" \
          '{ids: $ids, contents: {text: true, highlights: {numSentences: 3}, summary: true}}')")
  RESPONSE=$(cat "$RESP_FILE")
  if [ "$HTTP_CODE" != "429" ]; then break; fi
  if [ "$attempt" -lt 3 ]; then sleep $((2 ** attempt)); fi
done
# $RESPONSE and $HTTP_CODE are available after the loop
```

**Raw response fields:**
- `results[].title` — page title
- `results[].url` — page URL
- `results[].text` — full extracted page text
- `results[].summary` — LLM-generated summary

**Field mapping:**

| Normalized field | Source field | Rule |
|------------------|--------------|------|
| `title` | `results[].title` | Fallback: extract domain from URL |
| `url` | `results[].url` | As-is |
| `snippet` | `results[].text` | First 300 chars (same pattern as firecrawl `/scrape`); fallback: `summary` |

---

### /answer — Grounded LLM Answer

**Input parameters:**
- `QUERY` (string, required): question or search query

**Not supported in V1:** `outputSchema`, `systemPrompt` — outside scope; submit plain queries only.

**curl template (with 429 retry loop):**
```bash
RESP_FILE=$(mktemp)
trap 'rm -f "$RESP_FILE"' EXIT
for attempt in 1 2 3; do
  HTTP_CODE=$(curl -s --max-time 30 -X POST https://api.exa.ai/answer \
    -H "x-api-key: $EXA_API_KEY" \
    -H "Content-Type: application/json" \
    -o "$RESP_FILE" -w "%{http_code}" \
    -d "$(jq -cn --arg q "$QUERY" '{query: $q}')")
  RESPONSE=$(cat "$RESP_FILE")
  if [ "$HTTP_CODE" != "429" ]; then break; fi
  if [ "$attempt" -lt 3 ]; then sleep $((2 ** attempt)); fi
done
# $RESPONSE and $HTTP_CODE are available after the loop
```

**Raw response fields:**
- `answer` — LLM-generated answer text
- `citations[].title` — source page title
- `citations[].url` — source page URL
- `citations[].text` — source excerpt text
- `citations[].highlights[]` — extracted highlight snippets from source

**Normalize using the Answer schema (see `## Response Format`). Field mapping:**

| Normalized field | Source field | Rule |
|------------------|--------------|------|
| `answer` | `answer` | Fallback: `""` (empty string) |
| `citations[].title` | `citations[].title` | Fallback: extract domain from URL |
| `citations[].url` | `citations[].url` | As-is |
| `citations[].snippet` | `citations[].text` | First 300 chars; fallback: `citations[].highlights[0]` |

---

### /findSimilar — Similar Page Discovery

**Input parameters:**
- `SEED_URL` (string, required): URL of the seed page to find similar content for
- `NUM_RESULTS` (integer, optional, default 10): number of results to return

**Note:** The normalized `query` field in the Standard schema is populated with the seed URL.

**curl template (with 429 retry loop):**
```bash
RESP_FILE=$(mktemp)
trap 'rm -f "$RESP_FILE"' EXIT
for attempt in 1 2 3; do
  HTTP_CODE=$(curl -s --max-time 30 -X POST https://api.exa.ai/findSimilar \
    -H "x-api-key: $EXA_API_KEY" \
    -H "Content-Type: application/json" \
    -o "$RESP_FILE" -w "%{http_code}" \
    -d "$(jq -cn --arg u "$SEED_URL" --argjson n "${NUM_RESULTS:-10}" \
          '{url: $u, numResults: $n,
            contents: {text: true, highlights: {numSentences: 3, highlightsPerUrl: 3}, summary: true}}')")
  RESPONSE=$(cat "$RESP_FILE")
  if [ "$HTTP_CODE" != "429" ]; then break; fi
  if [ "$attempt" -lt 3 ]; then sleep $((2 ** attempt)); fi
done
# $RESPONSE and $HTTP_CODE are available after the loop
```

**Raw response fields:**
- `results[].title` — page title
- `results[].url` — page URL
- `results[].highlights[]` — extracted relevant text snippets
- `results[].text` — full page text
- `results[].summary` — LLM-generated summary

**Field mapping:**

| Normalized field | Source field | Rule |
|------------------|--------------|------|
| `title` | `results[].title` | Fallback: extract domain from URL |
| `url` | `results[].url` | As-is |
| `snippet` | `results[].highlights[0]` | Fallback: first 300 chars of `text`; then `summary` |

---

## Response Format

Normalize results into one of the following two standard schemas.

### Standard schema (search / contents / findSimilar)

```json
{
  "query": "<original query or seed URL>",
  "results": [
    {
      "title": "<page title>",
      "url": "<page URL>",
      "snippet": "<summary text>"
    }
  ],
  "source": "exa",
  "operation": "search"
}
```

`operation` is one of `"search"`, `"contents"`, or `"findSimilar"`.

### Answer schema (/answer)

```json
{
  "query": "<original query>",
  "answer": "<LLM-generated answer>",
  "citations": [
    {
      "title": "<source title>",
      "url": "<source URL>",
      "snippet": "<source excerpt>"
    }
  ],
  "source": "exa",
  "operation": "answer"
}
```

### Snippet extraction priority

Snippet extraction priority differs by operation, reflecting each endpoint's response shape:

| Operation | Primary | Fallback chain | Design rationale |
|-----------|---------|---------------|-----------------|
| `/search` | `highlights[0]` | `text[:300]` → `summary` | Relevance-ranked highlights are preferable for search results |
| `/contents` | `text[:300]` | `summary` | No `highlights` in `/contents` response; raw text is the primary output |
| `/answer` citations | `text[:300]` | `highlights[0]` | Verbatim excerpt provides grounding; highlights are secondary |
| `/findSimilar` | `highlights[0]` | `text[:300]` → `summary` | Same shape as `/search`; highlights preferred |

### Title fallback rule

When `title` is missing or empty, extract the domain from the URL:

```bash
# Preserves subdomains, strips scheme / port / path
jq -r '.url | capture("^[a-z]+://(?<host>[^/:]+)").host'
```

Example: `https://docs.example.com/guide` → `docs.example.com`

## Rate Limits & Error Handling

### Missing $EXA_API_KEY

Abort immediately and return an error message to the caller:

```
Error: $EXA_API_KEY environment variable is not set.
Run: export EXA_API_KEY="your-api-key"  or add it to your .env file.
```

### HTTP 401 / 403 (Authentication error)

The API key is invalid or lacks permission. Do not retry — abort immediately:

```
Error: Exa API authentication failed (HTTP <401|403>).
Check $EXA_API_KEY and replace with a valid key.
```

### HTTP 429 (Rate limit exceeded)

Up to 3 attempts total (1 initial + 2 retries). Wait before each retry using exponential backoff: 2s before attempt 2, 4s before attempt 3.  
If attempt 3 still returns 429, propagate the error to the caller.

Apply this reusable pattern to any operation (example shown for `/search` with deep-type timeout branching):

```bash
case "$TYPE" in deep|deep-reasoning) TIMEOUT=90 ;; *) TIMEOUT=30 ;; esac

RESP_FILE=$(mktemp)
trap 'rm -f "$RESP_FILE"' EXIT
RESPONSE=""
for attempt in 1 2 3; do
  HTTP_CODE=$(curl -s --max-time "$TIMEOUT" -X POST https://api.exa.ai/search \
    -H "x-api-key: $EXA_API_KEY" \
    -H "Content-Type: application/json" \
    -o "$RESP_FILE" -w "%{http_code}" \
    -d "$(jq -cn --arg q "$QUERY" --arg t "$TYPE" --argjson n "${NUM_RESULTS:-10}" \
          '{query: $q, type: $t, numResults: $n}')")
  RESPONSE=$(cat "$RESP_FILE")
  if [ "$HTTP_CODE" != "429" ]; then break; fi
  if [ "$attempt" -lt 3 ]; then sleep $((2 ** attempt)); fi
done
# $RESPONSE and $HTTP_CODE are available after the loop
# Caller MUST inspect $HTTP_CODE: 401/403 → auth error (abort), 5xx → propagate, 2xx → proceed
```

### HTTP 5xx (Server error)

Do not retry — propagate the error immediately to the caller.

### Network timeout

`--max-time 30` is set on all curl calls (except `deep`/`deep-reasoning` searches which use `--max-time 90`). On timeout, return an error without retrying.
