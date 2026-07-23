# phase 상태 머신

> tack 워크플로우의 `phase:status` 상태 모델을 I/O·CLI 없는 순수 Python 모듈로 정본화한다.

## 개요

story의 라이프사이클 상태는 `phase:status` 문자열로 표현한다. `state_machine.py`는 이 상태 모델의 정본 순수 구현으로, 전환 유효성 테이블(`VALID_TRANSITIONS`)·선형 순서(`STATE_ORDER`)·순방향 점프 판정을 상수와 순수 함수로만 노출한다. 레퍼런스 하네스 `dev-context.js`가 검증한 상태 모델을 변경 없이 승계한다.

이 모듈은 dev-context 엔진과의 깨끗한 seam이다 — E2-S2 엔진(CLI·`dev-context.json` I/O·config·force-state 플래그)이 `from state_machine import ...`로 이 모듈을 소비해 `update-state`·`force-state` 검증을 수행한다. 상태 로직(데이터 + 판정)과 정책 집행(I/O·차단·경고)이 파일 경계로 분리된다.

## 구조 / 스키마

### 위치

- 모듈: `template/.tack/scripts/state_machine.py`
- 테스트: `template/.tack/scripts/test_state_machine.py` (co-located)

`template/.tack/scripts/`는 authoring source 경로이고, `.tack/scripts/`는 deploy destination이다. dev-context.js와 sibling으로 co-locate돼 import seam이 성립한다.

### 전환표 (VALID_TRANSITIONS)

`phase:status → 허용 다음 상태 목록`. 14 directed edges (9 순방향 + 5 롤백):

| from | allowed to |
|------|-----------|
| `spec:drafting` | `spec:reviewing` |
| `spec:reviewing` | `spec:confirmed`, `spec:drafting` |
| `spec:confirmed` | `plan:ready` |
| `plan:ready` | `plan:reviewing` |
| `plan:reviewing` | `plan:confirmed`, `plan:ready` |
| `plan:confirmed` | `impl:in-progress` |
| `impl:in-progress` | `review:in-progress` |
| `review:in-progress` | `impl:in-progress`, `docs:generated` |
| `docs:generated` | `pr:created`, `review:in-progress` |
| `pr:created` | `docs:generated` |

5개 롤백 edge(`spec:reviewing→spec:drafting`, `plan:reviewing→plan:ready`, `review:in-progress→impl:in-progress`, `docs:generated→review:in-progress`, `pr:created→docs:generated`)는 리뷰 실패·수정·재push 루프를 표현한다.

### 상태 순서 (STATE_ORDER)

10 states의 선형 진행 순서다:

```
spec:drafting → spec:reviewing → spec:confirmed →
plan:ready → plan:reviewing → plan:confirmed →
impl:in-progress → review:in-progress → docs:generated → pr:created
```

전환 그래프가 back-edge/cycle을 포함해 선형 순서를 `VALID_TRANSITIONS`에서 파생할 수 없으므로, `STATE_ORDER`는 독립 상수로 유지한다. 두 상수의 state 집합 일치(`set(VALID_TRANSITIONS.keys()) == set(STATE_ORDER)`)는 테스트로 방어한다.

`done`은 상태 머신이 저장하는 상태가 아니다 — 워크플로우 7단계의 마지막 `done`은 `/flow-done`의 토픽 제거(remove-topic) 동작이며 `phase:status` 값으로 존재하지 않는다. 전환표·`STATE_ORDER`는 `pr:created`에서 끝나는 10 states만 관리한다.

### 공개 API

상태는 `'phase:status'` 문자열을 계약으로 받고 반환한다. E2-S2 엔진은 `dev-context.json`에 phase·status를 별도 필드로 저장하되 전환 검증 시 `f"{phase}:{status}"`로 조합해 이 API를 호출한다.

| 심볼 | 종류 | 반환 | 용도 |
|------|------|------|------|
| `VALID_TRANSITIONS` | 상수 | `dict[str, list[str]]` | 전환 유효성 테이블 |
| `STATE_ORDER` | 상수 | `list[str]` | 선형 순서 (순방향 판정 기준) |
| `is_valid_transition(frm, to)` | 함수 | `bool` | `to ∈ VALID_TRANSITIONS[frm]` |
| `allowed_transitions(frm)` | 함수 | `list[str]` | 허용 목록 복사본 (에러 메시지·힌트) |
| `is_known_state(state)` | 함수 | `bool` | `state ∈ STATE_ORDER` |
| `is_forward_jump(frm, to)` | 함수 | `bool` | `STATE_ORDER` 인덱스 비교 |

## 동작

- **`is_valid_transition(frm, to)`** — `to`가 `frm`의 허용 다음 상태 목록에 있으면 `True`. unknown `frm`은 빈 목록으로 처리해 `False`.
- **`allowed_transitions(frm)`** — `frm`의 허용 목록 **복사본**을 반환한다(`list(...)`). 호출자의 mutate가 상수를 오염시키지 않는다. unknown `frm`은 빈 목록.
- **`is_known_state(state)`** — `state`가 `STATE_ORDER`의 10개 known 상태 중 하나면 `True`.
- **`is_forward_jump(frm, to)`** — 두 상태가 모두 known일 때만 `STATE_ORDER.index(to) > STATE_ORDER.index(frm)`이면 `True`. 순방향 점프는 아티팩트 검증 없이 후기 상태로 진입해 게이트를 우회하는 신호다.

`is_forward_jump`는 `is_valid_transition`과 직교한다 — 무효 전환도 순방향일 수 있고(`spec:drafting→pr:created`는 무효지만 순방향), 유효 전환도 역방향일 수 있다(`review:in-progress→impl:in-progress`는 유효한 롤백이지만 역방향). 순방향 판정 자체가 유효성을 함의하지 않는다.

known 가드는 `.index()` 호출에 선행한다. JS `indexOf()`는 미발견 시 `-1`을 반환하지만 Python `list.index()`는 `ValueError`를 raise하므로, unknown state가 섞인 입력은 예외 없이 `False`로 처리된다.

## 제약사항

- **순수성** — 모듈은 module-level 상수·순수 함수만 노출한다. I/O·CLI·argparse·부작용 없음. `dev-context.json` 읽기/쓰기, CLI 서브커맨드 배선은 E2-S2 범위.
- **판정만, 집행 없음** — `is_forward_jump`는 순방향 여부 술어만 제공한다. 실제 차단(`--allow-unsafe-force` 요구)·stderr 경고 출력은 E2-S2 force-state가 배선한다.
- **문자열 계약** — 상태는 `'phase:status'` 문자열로 표현한다(enum/tuple 미채택). 레퍼런스 승계이며 E2-S2의 `dev-context.json` 별도 필드 저장과 정합한다.
- **전환표 preserve** — 14 edges·10 states는 레퍼런스 `dev-context.js`에서 변경 없이 승계한다. edge 추가·삭제·변경은 상태 모델 재설계이므로 이 모듈의 범위 밖이다.
- **툴링 무의존 테스트** — pytest가 `test_*.py`를 자동 발견하고 파일 디렉토리를 `sys.path`에 prepend하므로 `pyproject.toml`·`conftest.py` 없이 `from state_machine import ...`가 동작한다. 실행은 `uv run --with pytest python -m pytest test_state_machine.py`.
