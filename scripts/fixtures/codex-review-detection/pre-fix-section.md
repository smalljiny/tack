## Parsing the Decision

codex exec 실행 전후로 파일 목록을 비교해 새로 생성된 리뷰 파일을 식별한다.
`-newer` 방식은 macOS에서 타임스탬프 해상도 문제로 신뢰할 수 없으므로 사용하지 않는다.

```bash
# Set pattern: spec-review → 'spec-review-*.md' / plan-review → 'plan-review-*.md'
PATTERN='spec-review-*.md'
REVIEW_DIR="$(dirname "$CANON_PATH")"   # canonicalized file path → its containing dir

# 1. 실행 전 파일 목록 기록
BEFORE_FILES=$(ls "$REVIEW_DIR"/$PATTERN 2>/dev/null | sort)

# 2. codex exec 실행
codex exec "spec-review 스킬로 ${CANON_PATH}를 리뷰해줘" < /dev/null
EXEC_EXIT=$?

# 3. 실행 후 파일 목록과 비교 → 새 파일 = after - before
AFTER_FILES=$(ls "$REVIEW_DIR"/$PATTERN 2>/dev/null | sort)
REVIEW_FILE=$(comm -13 <(echo "$BEFORE_FILES") <(echo "$AFTER_FILES") | tail -1)

# Guard: 새 파일이 없으면 실패
if [ -z "$REVIEW_FILE" ]; then
  echo "No new review file found after codex exec (exit=$EXEC_EXIT) — stale or missing" >&2
  exit 1
fi

# Parse the decision line (case-sensitive: READY / READY WITH NOTE / NOT READY)
grep -m1 "^- Decision:" "$REVIEW_FILE"
```

이 방식의 장점:
- `/proc` 없이 macOS에서 동작 (타임스탬프 해상도 무관)
- 파일 존재 여부 기반이므로 신뢰성 높음
- `comm -13` = before에 없고 after에 있는 파일 = 이번 실행으로 새로 생성된 파일

Decision line format (from existing review files): `- Decision: READY` / `- Decision: NOT READY` / `- Decision: READY WITH NOTE`
