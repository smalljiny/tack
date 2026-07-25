# 배포 훅 세트 (Claude Code hooks)

> tack이 배포하는 하네스의 Claude Code 훅 8종. stdlib-only Python(`python3` 드롭인)으로 구현하고, `hooks.json`·`settings.json` 이중 배선으로 트리거한다.

## 개요

훅은 Claude Code 세션의 특정 이벤트(세션 시작·도구 사용 전후·세션 종료)에 반응해 컨텍스트 복원·품질 게이트·로깅·상태 저장을 자동화하는 스크립트다. 배포 소스는 `template/.claude/scripts/hooks/`이며, Copier 렌더 시 consuming 프로젝트 루트의 `.claude/scripts/hooks/`로 배포된다.

각 훅은 `#!/usr/bin/env python3` 셔뱅을 가진 stdlib-only Python 스크립트다 — `json`·`os`·`subprocess`·`sys` 등 표준 라이브러리만 사용하며 3rd-party 의존이 없다. `venv`·`uv` 부트스트랩 없이 시스템 `python3`로 직접 실행된다. 트리거 인자는 위치 인자(`sys.argv`)와 `PWD`로 전달되며, stdin JSON은 소비하지 않는다.

## 구조 / 스키마

### 훅 목록

| 훅 파일 | 트리거 | 인자 | 동작 |
|---------|--------|------|------|
| `session-start.py` | `SessionStart` | — | `.tack/local/dev-context.json`을 읽어 이전 작업 컨텍스트를 복원하고, codex 상태 감지를 `node .claude/scripts/codex/detect-and-cache.js`에 위임 |
| `suggest-compact.py` | `Edit`·`Write` (pre) | — | 도구 호출 횟수를 임시 카운터 파일로 추적하고 임계값 도달 시 compaction 시점을 제안 |
| `type-check.py` | `Edit` (post) | `${CLAUDE_TOOL_INPUT_FILE_PATH}` | `.ts` 파일 편집 후 `npx tsc --noEmit`로 타입 체크 |
| `prettier-format.py` | `Edit` (post) | `${CLAUDE_TOOL_INPUT_FILE_PATH}` | JS/TS 파일 편집 후 `npx prettier`로 자동 포맷 |
| `session-logger.py` | `*` (post, async) | `${CLAUDE_TOOL_NAME}` `${CLAUDE_TOOL_INPUT_FILE_PATH}` | 모든 도구 사용을 `.claude/sessions/<date>.jsonl`에 append |
| `git-push-review.py` | `Bash` (pre) | `${CLAUDE_TOOL_INPUT_COMMAND}` | 명령이 `git push`로 시작하면 검토 체크리스트를 안내 (명령 실행 없음) |
| `console-log-audit.py` | `Stop` | — | `git diff`로 수정된 JS/TS 파일에서 `console.log`를 감사 |
| `memory-persist.py` | `Stop` | — | 세션 종료 시 현재 상태를 `.tack/local/dev-context.json`에 저장 |

`suggest-compact.py`는 `Edit`·`Write` 양쪽에 등록되므로 `hooks.json`의 등록 수는 9(훅 파일 8 + suggest-compact 중복 1)다.

### 이중 배선

트리거는 두 파일에 동일하게 등록된다.

- `template/.claude/hooks/hooks.json` — `id`·`description`·`matcher`·`hooks[]` 구조의 9개 등록.
- `template/.claude/settings.json` — `SessionStart`·`PreToolUse`·`PostToolUse`·`Stop` 이벤트별 `hooks[]`.

양쪽 모두 `command`를 다음 형태로 배선한다:

```
python3 "${CLAUDE_PROJECT_DIR}/.claude/scripts/hooks/<name>.py" [args]
```

`session-logger`는 `timeout: 10000`·`async: true`로 등록돼 도구 사용을 논블로킹으로 기록한다.

## 동작

### dev-context.json 직접 읽기

`session-start.py`·`session-logger.py`·`memory-persist.py`는 `.tack/local/dev-context.json`을 **직접 파싱**한다 — `dev_context.py`/`dev-context.js` CLI를 경유하지 않는다. 읽기 실패(파일 부재·JSON 손상)는 조용히 삼켜 exit 0으로 종료해 세션을 방해하지 않는다.

### 외부 도구 shell-out

- `type-check.py`·`console-log-audit.py`는 고정 리터럴 명령(`npx tsc --noEmit 2>&1`, `git diff --name-only HEAD 2>/dev/null`)을 `subprocess.run(..., shell=True)`로 호출한다 — 보간되는 인자가 없다.
- `prettier-format.py`와 `console-log-audit.py`의 per-file `grep`, `session-start.py`의 `node detect-and-cache.js` 호출은 list-form `subprocess.run([...])`(no shell)로 실행해 파일 경로가 셸 구문으로 재해석되지 않는다.
- `git-push-review.py`는 명령 문자열에 `startswith("git push")` 검사만 수행하고 아무것도 실행하지 않는다.

### 종료 코드·출력 규약

각 훅은 Node 원본의 관찰 가능한 동작을 보존한다 — stdout/stderr 매핑(`console.log`→stdout, `console.warn`→stderr), 종료 코드 분기, JSON 직렬화(무공백·비ASCII 미이스케이프), 부작용(파일 쓰기·로그·subprocess 호출)을 동일하게 재현한다.

### 패리티 검증 하네스

훅 동작 패리티는 pytest로 검증한다 — `template/.claude/scripts/hooks/`에 `conftest.py` + 훅별 `test_<name>.py` 8개가 co-locate된다. `conftest.py`는 fixture dev-context.json 작성기와 임시 프로젝트 디렉토리를 제공하고, 테스트는 subprocess(tsc·prettier·git·node)를 mocking하며 stdout·종료 코드·파일 부작용을 검사한다.

```
python3 -m pytest
```

### harness-audit 인식

`template/.claude/scripts/harness-audit.js`의 hooks 스코프 감사는 Python 훅 계약을 인식한다 — `.claude/scripts/hooks` 아래 `.py` 파일 수를 세고, `session-start.py`·`session-logger.py`·`console-log-audit.py`의 존재를 확인한다.

## 제약사항

- **stdlib-only**: 3rd-party 의존을 추가하지 않는다. 훅은 시스템 `python3`로 직접 실행된다.
- **동작 패리티 우선**: 트리거·부작용·출력을 레퍼런스 Node 훅과 동일하게 유지한다. 기능 확장·훅 동작 변경은 범위 밖이다.
- **잔여 Node**: `detect-and-cache.js`(codex 감지)는 Node로 남으며 `session-start.py`가 `node`로 계속 호출한다. `dev-context.js`(Node 엔진)는 `.codex/skills` 3파일이 참조하므로 유지된다. 두 잔여는 후속 토픽 소관이다.
- **세션 로그 경로**: `session-logger.py`는 레퍼런스와 동일하게 `.claude/sessions/<date>.jsonl`에 기록한다. `base-layout.md` §6이 정의하는 `.tack/local/sessions/`로의 이관은 이 훅 세트에서 수행하지 않는다(후속 이연).
- **dogfood 허브 격리**: 이 배포 훅 세트는 tack 저장소 루트의 레퍼런스 Node 훅(`.claude/scripts/hooks/*.js`)과 별개다. 허브는 레퍼런스 Node 훅을 계속 실행한다.
