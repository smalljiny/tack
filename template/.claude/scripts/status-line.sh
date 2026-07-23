#!/bin/bash

# Claude Code status line script for harness
# Output: <model> | 📌<current_topic> | <bar> <pct>%
#
# Context calculation:
#   - max_context defaults to 1M (Opus 4.x with 1M window).
#     Override with STATUSLINE_MAX_CONTEXT env var for other models.
#   - sums input_tokens + cache_read_input_tokens + cache_creation_input_tokens
#     from the last usage entry in the transcript

input=$(cat)

# Resolve project root from this script's location (cwd-independent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# --- Model extraction ---
if command -v jq &>/dev/null; then
    model=$(printf '%s' "$input" | jq -r '.model.display_name // .model.id // "?"' 2>/dev/null)
else
    # jq not available — fallback: try python3, then grep/sed, then "?"
    model=$(printf '%s' "$input" | python3 -c \
        'import json,sys; m=json.load(sys.stdin).get("model",{}); print(m.get("display_name") or m.get("id") or "?")' \
        2>/dev/null)
    if [ -z "$model" ]; then
        model=$(printf '%s' "$input" | grep -o '"display_name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 \
            | sed 's/.*"display_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
    fi
fi
# fallback applies regardless of jq availability
[ -z "$model" ] && model="?"

# --- Current topic (cwd-independent path) ---
topic=$(python3 "$PROJECT_ROOT/.tack/scripts/dev_context.py" read --field=current_topic 2>/dev/null)
topic="${topic%$'\n'}"   # strip trailing newline only (preserves spaces in topic names)
[ -z "$topic" ] && topic="(no topic)"

# --- jq fallback: output simple line and exit ---
if ! command -v jq &>/dev/null; then
    echo "${model} | 📌${topic}"
    exit 0
fi

# --- Transcript path ---
transcript_path=$(printf '%s' "$input" | jq -r '.transcript_path // empty' 2>/dev/null)

# --- Context bar ---
# max_context: 1M default (Opus 4.x). Set STATUSLINE_MAX_CONTEXT for other models.
max_context="${STATUSLINE_MAX_CONTEXT:-1000000}"
# Validate: must be a positive integer (rejects 0 to prevent division by zero,
# and non-numeric strings to prevent bash arithmetic injection)
[[ "$max_context" =~ ^[1-9][0-9]*$ ]] || max_context=1000000
bar_width=10

if [[ -n "$transcript_path" && -f "$transcript_path" ]]; then
    # Scan only the last 200 lines to bound parsing cost on long sessions.
    # Usage entries appear frequently, so the tail reliably contains a recent one.
    context_length=$(tail -200 "$transcript_path" 2>/dev/null | jq -s '
        map(select(.message.usage and .isSidechain != true and .isApiErrorMessage != true)) |
        last |
        if . then
            (.message.usage.input_tokens // 0) +
            (.message.usage.cache_read_input_tokens // 0) +
            (.message.usage.cache_creation_input_tokens // 0)
        else 0 end
    ' 2>/dev/null)

    context_length="${context_length:-0}"
    # Validate integer to prevent bash arithmetic injection
    [[ "$context_length" =~ ^[0-9]+$ ]] || context_length=0
    if [[ "$context_length" -gt 0 ]]; then
        pct=$((context_length * 100 / max_context))
    else
        pct=0
    fi
else
    pct=0
fi

[[ $pct -gt 100 ]] && pct=100

bar=""
for ((i=0; i<bar_width; i++)); do
    bar_start=$((i * 10))
    progress=$((pct - bar_start))
    if [[ $progress -ge 8 ]]; then
        bar+="█"
    elif [[ $progress -ge 3 ]]; then
        bar+="▄"
    else
        bar+="░"
    fi
done

echo "${model} | 📌${topic} | ${bar} ${pct}%"
