---
version: 20
name: adapter-codex-review
description: Run a single Codex spec-review or plan-review via `codex exec` and return the parsed Decision. Phase auto-detected from `dev-context.json`. Loop control is owned by the calling command, not this skill.
origin: harness
---

# adapter-codex-review

## Non-Goals

The following are explicitly **out of scope** for this skill:

- Using `codex-companion.mjs` or adversarial-review infrastructure
- Calling any Codex skill other than `spec-review` and `plan-review`
- Automatically editing spec or plan documents based on review output
- 스킬 내부 루프 금지 (loop control stays in the calling command)

---

## Auto-Detect Entry Point

인자 없이 이 스킬이 로드되면, 사용자에게 묻지 않고 아래 순서로 자동 판단하여 즉시 실행한다.

### 1. 현재 토픽과 상태 읽기

```bash
TOPIC=$(python3 .tack/scripts/dev_context.py read --field=current_topic)
PHASE=$(python3 .tack/scripts/dev_context.py read --topic="$TOPIC" --field=phase)
STATUS=$(python3 .tack/scripts/dev_context.py read --topic="$TOPIC" --field=status)
```

### 2. phase:status → 실행 스킬 결정

| phase:status | 실행 스킬 | 경로 필드 |
|---|---|---|
| `spec:reviewing` | spec-review | `spec` |
| `plan:reviewing` | plan-review | `plan` |
| 기타 | 실행 불가 — 아래 메시지 출력 후 종료 |  |

표가 정한 실행 스킬 이름을 `REVIEW_KIND`에 바인딩한다. `Parsing the Decision`의 `PATTERN`과 `codex exec` 대상이 이 값에서 파생되므로, 두 phase가 같은 블록을 그대로 쓴다.

```bash
case "$PHASE:$STATUS" in
  spec:reviewing) REVIEW_KIND=spec-review ;;
  plan:reviewing) REVIEW_KIND=plan-review ;;
esac
```

해당하지 않는 상태일 경우:
```
현재 상태 (<phase>:<status>)에서 adapter-codex-review를 실행할 수 없습니다.
spec-review: /flow-spec에서 spec:reviewing 상태로 전환 후 실행하세요.
plan-review: /flow-plan에서 plan:reviewing 상태로 전환 후 실행하세요.
```

### 3. 경로 읽기·검증·정규화

```bash
# spec-review인 경우
CANON_PATH=$(node .tack/scripts/validate-path.js --topic="$TOPIC" --field=spec)

# plan-review인 경우
CANON_PATH=$(node .tack/scripts/validate-path.js --topic="$TOPIC" --field=plan)
```

실패(비-0 exit) 시 즉시 중단. 성공 시 **사용자 확인 없이** Availability Gate → Invocation Pattern 순으로 바로 진행한다.

---

## Prerequisites

- **`gtimeout`** (GNU `timeout` 대안): `brew install coreutils` 로 설치 가능.
  미설치 시 `timeout`(Linux 기본) 또는 no-op 폴백으로 자동 선택된다.
  timeout 없이 실행하면 Codex 자체 실행 제한에 의존한다.

---

## Availability Gate

Before invoking `codex exec`, verify Codex is available and authenticated:

```bash
python3 .tack/scripts/dev_context.py read --field=config.codex.available
python3 .tack/scripts/dev_context.py read --field=config.codex.authenticated
```

If either returns a value other than `"true"`:
1. Print a warning: `Codex not available or not authenticated — adapter-codex-review cannot proceed.`
2. Show the manual fallback command (see "Fallback" section below)
3. Exit the skill without invoking `codex exec`

---

## Path Validation (Required Before Invocation)

`.tack/scripts/validate-path.js`가 경로 읽기·검증·정규화를 단일 호출로 처리한다.

내부 동작:
- `dev-context.json`에서 경로 읽기
- 빈값·절대경로(`/`)·leading dash(`-`)·경로 탐색(`..`)·제어 문자 거부
- `fs.realpathSync()`로 정규화 (파일 미존재 시 `path.resolve()` 폴백)
- 리포지터리 루트 내부 경로 확인

```bash
# <field>: spec-review → spec / plan-review → plan
CANON_PATH=$(node .tack/scripts/validate-path.js --topic="$TOPIC" --field=<field>)
# 오류 시 비-0 exit + stderr 출력
```

`$CANON_PATH`를 이후 `codex exec` 호출과 `Parsing the Decision`의 `REVIEW_DIR` 계산에 사용한다.

**Security scope**: 경로를 리포지터리 로컬로 제한. `workspace-write` 샌드박스가 `codex exec` 작업 범위를 추가로 제한한다.

---

## Invocation Pattern

### spec-review

```bash
# Path Validation → CANON_PATH 획득 (단일 node 호출, Bash(node:*) 허용)
CANON_PATH=$(node .tack/scripts/validate-path.js --topic="$TOPIC" --field=spec)

# -s workspace-write: 리뷰 파일을 workdir 내에 쓸 수 있도록 명시적으로 허용.
# 프로젝트 codex.toml에 workspace-write가 없어도 동작하도록 항상 붙인다.
# macOS: gtimeout (brew coreutils) preferred; falls back to timeout (Linux); no-op if absent
# < /dev/null: bash 복합 명령 안에서 실행 시 codex가 stdin을 읽으려 대기하는 문제 방지.
TIMEOUT_BIN=$(command -v gtimeout 2>/dev/null || command -v timeout 2>/dev/null || true)
if [ -n "$TIMEOUT_BIN" ]; then
  "$TIMEOUT_BIN" 120 codex exec -s workspace-write "spec-review 스킬로 ${CANON_PATH}를 리뷰해줘" < /dev/null
else
  codex exec -s workspace-write "spec-review 스킬로 ${CANON_PATH}를 리뷰해줘" < /dev/null
fi
```

### plan-review

```bash
# Path Validation → CANON_PATH 획득 (단일 node 호출, Bash(node:*) 허용)
CANON_PATH=$(node .tack/scripts/validate-path.js --topic="$TOPIC" --field=plan)

# < /dev/null: bash 복합 명령 안에서 실행 시 codex가 stdin을 읽으려 대기하는 문제 방지.
TIMEOUT_BIN=$(command -v gtimeout 2>/dev/null || command -v timeout 2>/dev/null || true)
if [ -n "$TIMEOUT_BIN" ]; then
  "$TIMEOUT_BIN" 120 codex exec -s workspace-write "plan-review 스킬로 ${CANON_PATH}를 리뷰해줘" < /dev/null
else
  codex exec -s workspace-write "plan-review 스킬로 ${CANON_PATH}를 리뷰해줘" < /dev/null
fi
```

`$CANON_PATH`를 이후 `Parsing the Decision`의 `REVIEW_DIR` 계산에 사용한다.

### Isolation via DEV_CONTEXT_PATH

To run experiments without mutating the active development topic, point `DEV_CONTEXT_PATH`
to a fixture dev-context file inside the repo (e.g. `.tack/local/.../fixture/`):

```bash
# Validate fixture path before use
DEV_CONTEXT_PATH=".tack/local/active/codex-skill-bridge/fixture/fixture-dev-context.json"
TIMEOUT_BIN="$(command -v gtimeout 2>/dev/null || command -v timeout 2>/dev/null)"
if [ -n "$TIMEOUT_BIN" ]; then
  DEV_CONTEXT_PATH="$DEV_CONTEXT_PATH" "$TIMEOUT_BIN" 120 codex exec "..." < /dev/null
else
  DEV_CONTEXT_PATH="$DEV_CONTEXT_PATH" codex exec "..." < /dev/null
fi
```

The fixture `dev-context.json` must contain:
- `current_topic` set to a fixture topic name (e.g. `"test-fixture"`)
- `topics["test-fixture"].spec` — full repo-relative path to a fixture spec file
- `topics["test-fixture"].plan` — full repo-relative path to a fixture plan file
- `topics["test-fixture"].phase: "plan"`, `status: "reviewing"` (for plan-review to safely
  transition to either `plan:confirmed` or `plan:ready`)

---

## Review File Location

After `codex exec` completes, the Codex review skill writes the review artifact:

| Skill | Path pattern |
|-------|-------------|
| spec-review | `<spec-file-dir>/spec-review-<YYMMDDHHmmss>.md` |
| plan-review | `<plan-file-dir>/plan-review-<YYMMDDHHmmss>.md` |

**Bridge is read-only**: The bridge skill never writes review files. Review artifact
persistence and `dev-context.json` field updates are owned exclusively by the Codex review
skills.

---

## Parsing the Decision

codex exec 실행 전후로 파일 목록을 비교해 새로 생성된 리뷰 파일을 식별한다.
`-newer` 방식은 macOS에서 타임스탬프 해상도 문제로 신뢰할 수 없으므로 사용하지 않는다.

```bash
# PATTERN은 Step 2가 바인딩한 REVIEW_KIND에서 파생된다
# (spec-review → 'spec-review-*.md' / plan-review → 'plan-review-*.md')
PATTERN="${REVIEW_KIND}-*.md"
REVIEW_DIR="$(dirname "$CANON_PATH")"   # canonicalized file path → its containing dir

# 1. 실행 전 파일 목록 기록
BEFORE_FILES=$(find "$REVIEW_DIR" -maxdepth 1 -name "$PATTERN" 2>/dev/null | sort)

# 2. codex exec 실행
codex exec "${REVIEW_KIND} 스킬로 ${CANON_PATH}를 리뷰해줘" < /dev/null
EXEC_EXIT=$?

# Guard: codex exec가 실패하면 리뷰 파일을 파싱하지 않는다.
# Failure Handling 표의 `codex exec ... exits non-zero` 행과 같은 정책 — 실패한 실행이
# 남긴 부분 파일에 `- Decision:` 줄이 있으면 그것이 유효한 판정으로 통과할 수 있다.
if [ "$EXEC_EXIT" -ne 0 ]; then
  echo "codex exec failed (exit=$EXEC_EXIT) — Manual fallback을 사용하세요" >&2
  exit 1
fi

# 3. 실행 후 파일 목록과 비교 → 새 파일 = after - before
AFTER_FILES=$(find "$REVIEW_DIR" -maxdepth 1 -name "$PATTERN" 2>/dev/null | sort)
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
- 셸 글롭에 의존하지 않음 — `find`가 패턴을 인자로 받아 자체 매칭하므로, 변수 치환 결과를 글롭 확장하지 않는 zsh의 동작과 무관하다

Decision line format (from existing review files): `- Decision: READY` / `- Decision: NOT READY` / `- Decision: READY WITH NOTE`

---

## Failure Handling

| Failure mode | Action |
|---|---|
| `config.codex.available != "true"` | Print warning, show manual fallback, exit |
| `config.codex.authenticated != "true"` | Print warning, show manual fallback, exit |
| `timeout` not found (macOS) | `TIMEOUT_BIN` 선택 로직이 자동 폴백 처리. `gtimeout`(brew coreutils) 또는 `timeout`(Linux) 순으로 탐색; 둘 다 없으면 timeout 없이 실행 |
| `codex exec ...` exits non-zero | Record exit code, show manual fallback |
| `codex exec` exits 0 but no review file generated | Record observation (sandbox policy may block write), show manual fallback |
| Timeout (120s elapsed) | Record timeout, consider increasing threshold or checking sandbox settings |

**Manual fallback** (interactive session — shown when bridge cannot proceed):

```bash
# Interactive Codex session (manual review, not automated)
codex "spec-review 스킬로 <spec-path>를 리뷰해줘"
# or
codex "plan-review 스킬을 실행해줘"
```

**⚠ `-a always` 사용 주의**: `codex exec -a always ...`는 모든 작업 승인을 자동화하며
sandbox 보호를 사실상 무력화합니다. 실험 목적 외 프로덕션 코드에 사용 금지.
문제 발생 시 먼저 stdout/stderr를 확인하고, 필요 최소 권한만 허용하세요.
