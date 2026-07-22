---
version: 2
name: eval-harness
description: >-
  Eval-Driven Development framework for Claude Code harness skills. Invoked as:
  codex "eval-harness 스킬로 <skill-name>을 eval해줘". Loads eval case from
  .claude/evals/<skill-name>.md, runs code-based graders in 3 trials, computes
  pass@3 and pass^3, appends a structured log to .claude/evals/<skill-name>.log,
  and updates .claude/evals/baseline.json on PASS. v1 scope: skills only.
---

# eval-harness

Eval-Driven Development(EDD) framework for Claude Code harness components.
v1: skill evaluation via code-based (Bash exit code) graders only.

## Overview

`eval-harness`는 하네스 스킬의 품질을 정량적으로 측정하고 회귀를 감지한다.

**호출 형식:**
```
codex "eval-harness 스킬로 <skill-name>을 eval해줘"
```

**동작 흐름:**
1. `<skill-name>`을 인자에서 추출
2. `.claude/evals/<skill-name>.md` eval 케이스 파일 로드
3. 각 eval 케이스에 대해 3 trials 실행 (code-based grader)
4. pass@3 / pass^3 계산 → skill-level 판정
5. `.claude/evals/<skill-name>.log`에 append
6. `Decision: PASS`이면 `.claude/evals/baseline.json` 갱신

**v2 범위 (out-of-scope for v1):**
- 커맨드·에이전트 eval
- LLM-as-judge grader
- CI/CD 자동 실행
- 프로덕션 모니터링
- eval 케이스 자동 생성

## Required Inputs

### 호출 인자 파싱

호출 문자열 `"eval-harness 스킬로 <skill-name>을 eval해줘"`에서 `<skill-name>`을 추출한다.

```bash
# 예: "eval-harness 스킬로 stack-exa를 eval해줘" → SKILL_NAME="stack-exa"
SKILL_NAME="<user가 지정한 스킬 이름>"

# 입력 검증: 영문자·숫자·하이픈·언더스코어만 허용 (경로 트라버설 차단)
if ! echo "$SKILL_NAME" | grep -qE '^[a-zA-Z0-9][a-zA-Z0-9_-]*$'; then
  echo "오류: 유효하지 않은 스킬 이름입니다: $SKILL_NAME"
  echo "스킬 이름은 영문자·숫자·하이픈·언더스코어만 사용할 수 있습니다."
  exit 1
fi

EVAL_CASE_FILE=".claude/evals/${SKILL_NAME}.md"
```

**에러 분기 — eval 케이스 파일 미존재:**
```
eval 케이스 파일을 찾을 수 없습니다: .claude/evals/<skill-name>.md
먼저 해당 스킬의 eval 케이스 파일을 작성하세요.
형식: .claude/evals/SKILL.md 파일의 ## EVAL: <skill-name> 섹션 참조
```

**에러 분기 — skill-name 인자 없음:**
```
스킬 이름을 지정하세요.
사용법: codex "eval-harness 스킬로 <skill-name>을 eval해줘"
예시: codex "eval-harness 스킬로 stack-exa를 eval해줘"
```

### Version 출처 (우선순위)

1. eval 케이스 파일의 `버전:` 필드 값
2. 없으면 해당 스킬의 `SKILL.md` frontmatter `version:` 필드

```bash
VERSION=$(grep -m1 "^버전:" "$EVAL_CASE_FILE" | sed 's/버전: //')
if [ -z "$VERSION" ]; then
  VERSION=$(grep -m1 "^version:" ".claude/skills/${SKILL_NAME}/SKILL.md" 2>/dev/null | sed 's/version: //')
fi
VERSION=${VERSION:-"unknown"}
```

## Eval Workflow

### 1. Eval 케이스 파싱

`.claude/evals/<skill-name>.md`에서 `[CAPABILITY]`·`[REGRESSION]` 태그로 케이스를 추출한다.

**태그 파싱 규칙:**
- `[CAPABILITY]` 접두 줄 → Capability eval (임계값: `pass@3 ≥ 0.9`)
- `[REGRESSION]` 접두 줄 → Regression eval (임계값: `pass^3 = YES`)

**Command 필드 추출:**
각 케이스의 `- Command:` 줄에서 백틱으로 감싼 단일 Bash 명령을 추출한다.
파일에 여러 케이스가 있을 경우 케이스 단위로 반복 실행한다 (아래는 단일 케이스 추출 예시).

```bash
# 단일 케이스 Command 추출 예시 (실제 구현은 모든 케이스를 순회)
COMMAND=$(grep -A5 "\[CAPABILITY\]" "$EVAL_CASE_FILE" | grep "Command:" | head -1 | sed 's/.*`\(.*\)`.*/\1/')
```

**신뢰 모델 (중요)**: `.claude/evals/*.md`의 `Command:` 필드는 `bash -c`로 직접 실행된다.

> ⚠️ **eval 케이스 파일은 실행 코드다.** 추가·수정은 셸 스크립트 커밋과 동등한
> 코드 리뷰 대상이다. 검토되지 않은 eval 케이스 파일을 설치하지 말 것.
>
> eval-harness는 **프로덕션 API 키, 인증 토큰 등 민감 환경 변수가 있는 셸에서
> 실행하지 않는다.** 환경 격리가 필요하면 별도 셸에서 `env -i HOME="$HOME"
> PATH="$PATH" bash -c "..."` 패턴을 사용한다.

**baseline.json 미존재 처리 (부트스트랩):**
- `.claude/evals/baseline.json`이 없으면 Regression eval을 전부 스킵
- Capability eval만 실행
- 첫 `Decision: PASS` 후 baseline.json 신규 생성

### 2. 3-Trial 실행 루프

각 eval 케이스에 대해 동일 Bash 명령을 3회 독립 실행한다.
exit code 0 = PASS, 비-0 = FAIL.

```bash
PASS_COUNT=0
TRIAL_RESULTS=()

for trial in 1 2 3; do
  START_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  bash -c "$COMMAND" >/dev/null 2>&1
  EXIT_CODE=$?
  if [ "$EXIT_CODE" -eq 0 ]; then
    RESULT="PASS"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    RESULT="FAIL"
  fi
  TRIAL_RESULTS+=("Trial ${trial}: ${RESULT}")
done
```

### 3. pass@k 계산

| 메트릭 | 정의 | 산출 | 표기 |
|--------|------|------|------|
| `pass@3` | 3 trials 중 PASS 비율 | `PASS 횟수 / 3` | 소수점 (`0.67`, `1.0`) |
| `pass^3` | 3 trials 모두 PASS | `PASS 횟수 == 3` | `YES` / `NO` |

```bash
PASS_AT_3=$(printf "%.2f" "$(echo "scale=4; $PASS_COUNT / 3" | bc)")
if [ "$PASS_COUNT" -eq 3 ]; then
  PASS_POW_3="YES"
else
  PASS_POW_3="NO"
fi
```

**v1 주의**: `pass@3 ≥ 0.9` 임계값은 3 trials에서 실질적으로 `3/3`(`1.00`)과 동치이다.

### 4. 케이스별 판정

| Eval 유형 | 판정 메트릭 | 임계값 |
|----------|------------|--------|
| Capability | pass@3 | ≥ 0.9 (실질 3/3) |
| Regression | pass^3 | = YES |

```bash
if [ "$EVAL_TYPE" = "CAPABILITY" ]; then
  # pass@3 >= 0.9: 소수점 비교
  CASE_PASS=$(echo "$PASS_AT_3 >= 0.9" | bc)
  [ "$CASE_PASS" -eq 1 ] && CASE_DECISION="PASS" || CASE_DECISION="FAIL"
elif [ "$EVAL_TYPE" = "REGRESSION" ]; then
  [ "$PASS_POW_3" = "YES" ] && CASE_DECISION="PASS" || CASE_DECISION="FAIL"
fi
```

### 5. Skill-level 집계

모든 케이스가 각자 임계값을 충족해야 `Decision: PASS`. 하나라도 미달 시 `FAIL`.

```bash
SKILL_DECISION="PASS"
for case_result in "${CASE_DECISIONS[@]}"; do
  if [ "$case_result" = "FAIL" ]; then
    SKILL_DECISION="FAIL"
    break
  fi
done
```

## Output Contract

### `.claude/evals/<skill-name>.log` 레코드 형식

실행마다 파일 끝에 **append** (기존 레코드 비파괴).
경로는 repo root 기준. Codex sandbox는 `workspace-write` 모드 필요.

```
## Run: <ISO 8601 타임스탬프> | Skill: <name> | Version: <n> | git: <short SHA>

### Case: <eval case id 1> [CAPABILITY]
- Trial 1: PASS/FAIL
- Trial 2: PASS/FAIL
- Trial 3: PASS/FAIL
- pass@3: 1.00 | pass^3: YES | 판정: PASS (기준: pass@3 ≥ 0.9)

### Case: <eval case id 2> [REGRESSION]
- Trial 1: PASS/FAIL
- Trial 2: PASS/FAIL
- Trial 3: PASS/FAIL
- pass@3: 1.00 | pass^3: YES | 판정: PASS (기준: pass^3 = YES)

### Skill 집계
- Decision: PASS
```

**파일 쓰기 실패 시 fallback:**
```
경고: .claude/evals/<skill-name>.log에 쓸 수 없습니다.
로그 내용을 표준 출력으로 출력합니다. 수동으로 파일에 저장하세요.
```

### `.claude/evals/baseline.json` 갱신 규칙

`Decision: PASS`인 실행이 완료되면 해당 스킬 키를 현재 git short SHA + ISO 타임스탬프로 갱신.
파일이 없으면 신규 생성.

```json
{
  "stack-exa": {
    "lastPass": "2026-04-24T19:09:39Z",
    "gitSHA": "abc1234"
  },
  "stack-firecrawl": {
    "lastPass": "2026-04-24T19:15:00Z",
    "gitSHA": "abc1234"
  }
}
```

```bash
GIT_SHA=$(git rev-parse --short HEAD)
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
BASELINE=".claude/evals/baseline.json"
# baseline.json 없으면 신규 생성, 있으면 해당 키만 갱신 (jq 사용)
if [ ! -f "$BASELINE" ]; then echo '{}' > "$BASELINE"; fi
# 원자적 쓰기: jq 실패 시 기존 파일 보존
jq --arg skill "$SKILL_NAME" --arg ts "$NOW" --arg sha "$GIT_SHA" \
  '.[$skill] = {"lastPass": $ts, "gitSHA": $sha}' "$BASELINE" > "${BASELINE}.tmp" \
  && mv "${BASELINE}.tmp" "$BASELINE"
```

**baseline.json 쓰기 실패 시:**
```
경고: .claude/evals/baseline.json을 갱신할 수 없습니다.
수동으로 아래 내용을 추가하세요:
  "<skill-name>": {"lastPass": "<ISO timestamp>", "gitSHA": "<short SHA>"}
```

## Resources

- `docs/_local/active/eval-harness/spec.md` — 스펙 (설계 결정 근거)
- `references/everything-claude-code/skills/eval-harness/SKILL.md` — ECC 원본 참조
- `.codex/skills/spec-review/SKILL.md` — Codex 스킬 형식 참조
- `.claude/evals/` — eval 케이스 파일 및 실행 이력 저장 디렉토리

## E2E 검증 결과 (2026-04-24)

레퍼런스 eval 케이스 2건에 대해 Codex CLI end-to-end 검증 완료:

```
codex "eval-harness 스킬로 stack-exa를 eval해줘"
→ Decision: PASS (git: 1b180bc)

codex "eval-harness 스킬로 stack-firecrawl를 eval해줘"
→ Decision: PASS (git: 1b180bc)
```

**Open Question #3 (Codex sandbox 쓰기 권한) 결과:**
- `workspace-write` 모드(workdir 포함)에서 `.claude/evals/*.log`와 `baseline.json` 쓰기 모두 성공
- 별도 sandbox 설정 변경 없이 정상 작동 확인

**레퍼런스 eval 케이스 형식 주의:**
- Response schema 필드 검증 시 JSON 형식(`"query"`, `"results"` 등 큰따옴표 포함)으로 확인해야 함
- `:` 없는 필드명 검색은 false negative 발생 가능
