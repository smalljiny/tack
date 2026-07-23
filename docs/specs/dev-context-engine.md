# dev-context 엔진

> `dev-context.json` 토픽 라이프사이클 상태를 관리하는 6 서브커맨드 CLI 엔진. 상태 전환 검증은 순수 모듈 `state_machine.py`에 위임한다.

## 개요

`dev_context.py`는 tack 워크플로우의 상태 저장소 `dev-context.json`을 조작하는 정본 CLI 엔진이다. 토픽 등록·상태 전환·필드 읽기/쓰기·config 점경로 처리·토픽 삭제·강제 전환을 6개 서브커맨드로 제공한다. 레퍼런스 하네스 `dev-context.js`가 89-test로 검증한 동작·외부 계약(stdout 형식·종료 코드·JSON 직렬화·경로 해석)을 byte 단위로 보존하는 Python 패리티 포트다.

엔진은 상태 전환 로직을 소유하지 않는다 — `from state_machine import ...`로 [phase 상태 머신](phase-state-machine.md)의 전환표·상태 순서·판정 함수를 소비한다. 상태 로직(데이터 + 판정)과 정책 집행(I/O·차단·경고·CLI 배선)이 파일 경계로 분리되며, 엔진은 후자만 담당한다. `update-state`는 `is_valid_transition`/`allowed_transitions`로, `force-state`는 `is_known_state`/`is_forward_jump`/`STATE_ORDER`로 라우팅한다.

## 구조 / 스키마

### 위치

```
template/.tack/scripts/
├── state_machine.py       # import 대상 — 순수 상태 모듈 (별도 문서)
├── dev_context.py         # CLI 엔진
├── conftest.py            # pytest 픽스처 + 서브프로세스 커버리지 배선
├── _dc_helpers.py         # 공유 테스트 헬퍼
├── test_register_topic.py # 서브커맨드별 엔진 통합 pytest
├── test_update_state.py
├── test_set_field.py
├── test_read.py
├── test_config.py         # config 점경로
├── test_remove_topic.py
├── test_force_state.py
├── dev-context.js         # 레퍼런스 (승계 원천, 미삭제 — Node 훅층이 사용)
└── dev-context.test.js    # 레퍼런스 89-test (이식 spec)
```

`template/.tack/scripts/`는 authoring source 경로이고 `.tack/scripts/`는 deploy destination이다. 엔진은 `dev-context.js`·`state_machine.py`와 sibling으로 co-locate돼 import seam이 성립한다. 레퍼런스 `.js`는 삭제하지 않고 공존한다 — 배포 스킬층 콜러는 Python 엔진으로 전환됐으나(E2-S4) Node 훅층이 E7-S1 전까지 계속 `.js`를 호출하며, 두 엔진은 패리티 대조 근거로도 함께 유지된다.

### 상태 파일 경로 해석

`DEV_CONTEXT_PATH` 환경 변수가 있으면 그 값을, 없으면 스크립트 상대 기본 경로(`__file__` 기준 `../../.tack/local/dev-context.json`, `os.path.normpath` 정규화)를 사용한다. env override는 worktree 격리·테스트 격리 수단이다.

### dev-context.json 스키마

```json
{
  "current_topic": "<topic-name> | null",
  "topics": {
    "<topic-name>": {
      "phase": "spec", "status": "drafting",
      "spec": "<path>", "specReview": null,
      "plan": null, "planReview": null,
      "currentStory": null,
      "createdAt": "<ISO>", "updatedAt": "<ISO>"
    }
  },
  "config": { "<namespace>": { "<key>": "<value>" } },
  "updatedAt": "<ISO>"
}
```

토픽 dict의 키 삽입 순서(phase·status·spec·specReview·plan·planReview·currentStory·createdAt·updatedAt)는 레퍼런스와 일치한다. `read_context`는 로드 시 `topics`·`current_topic`·`config`를 정규화하고, 각 토픽의 `currentTask`→`currentStory` 필드 마이그레이션을 적용한다.

### 진입점·인자 파싱

- **진입점**: `#!/usr/bin/env python3` shebang + `python3 dev_context.py <subcommand> [--flag=value]` 직접 호출. uv 래핑·`.venv` 부트스트랩은 스크립트 밖 환경 관심사로 분리한다. 레퍼런스 `node dev-context.js` 직접 호출과 대칭이다.
- **인자 파싱**: 레퍼런스 `parseArgs`를 수동 파싱으로 이식한다(argparse 미채택). `--key=value` 정규식(`^--([^=]+)=(.*)\Z`)과 값 없는 boolean flag(`--allow-unsafe-force` → `True`)를 파싱한다. `\Z` 앵커 + DOTALL 미사용으로 JS `/^--([^=]+)=(.*)$/`(no `s` flag)의 개행 처리 동작을 재현한다.

## 동작

### 서브커맨드

| 서브커맨드 | 필수 인자 | 동작 |
|-----------|----------|------|
| `register-topic` | `--topic` `--spec` | 토픽을 `spec:drafting`으로 신규 등록. 중복 시 die(현재 상태 안내), 레거시 필드(`current_spec`·`specConfirmed`·`planConfirmed`) 정리, `current_topic` 설정 |
| `update-state` | `--topic` `--phase` `--status` | `is_valid_transition`으로 검증 후 전환. 동일 상태는 idempotent no-op(파일 미변경). 무효 전환은 die + `allowed_transitions` 안내 |
| `set-field` | `--field` (`--topic` `--value`) | 글로벌(`current_topic`·`config.<ns>.<key>`)/토픽 필드 분기. phase·status 차단, 예약 키 거부 |
| `remove-topic` | `--topic` | 토픽 삭제. `current_topic`이 삭제 대상이면 남은 토픽 중 첫 키 또는 null로 전환 |
| `read` | `--field` (`--topic`) | 글로벌/토픽 필드 조회. `--field` 없으면 사용법 die. config 배열은 `\n` join |
| `force-state` | `--topic` `--phase` `--status` | `is_known_state` 검증 후 전환표 우회 강제 전환. `is_forward_jump`이 순방향이면 `--allow-unsafe-force` 요구, 강제 시 stderr 경고 |

### config 점경로 처리

`parse_config_path`는 `config.<ns>.<key>` 깊이 2 고정 파싱(세그먼트 3개·`config` prefix·비어있지 않은 ns/key)을 수행하고 예약 키를 거부한다. `coerce_config_value`는 config 전용 타입 추론을 적용한다:

- `'true'`/`'false'` → bool
- `^-?[0-9]+$` → int
- `^\s*\[.*\]\s*$` → JSON 배열(문자열 원소만, 줄바꿈·비문자열 원소 위반 시 die)
- 그 외 → str

`[invalid`(닫히지 않음)·`[A-Z].*`(`]` 뒤 문자) 같은 스칼라는 배열 패턴에 미매치해 문자열로 보존된다. 토픽 필드 값은 타입 추론 없이 문자열 그대로 저장한다 — 타입 추론은 config 전용이다. **어떤 네임스페이스·키가 유효한지, 위험 tier 필드 스키마는 검증하지 않는다**(임의 `config.<ns>.<key>` plumbing만 제공).

### 읽기 출력 계약

- null/미설정 스칼라 → 빈 줄(`"\n"`)
- 스칼라 값 → `"<value>\n"` (bool은 `_js_string`으로 `true`/`false` 변환해 JS `String()` 재현)
- config 배열 → 원소를 `\n`으로 join + trailing `\n`
- 빈 배열 == 미설정 → 빈 줄(동일 출력)
- config read는 hasOwn 가드로 상속 속성을 차단한다. Python dict는 상속 데이터 키가 없어 `in` 검사가 곧 hasOwn 가드다.

### 방어·안전성

- **prototype-pollution 방어**: config 세그먼트·토픽 이름(`force-state`)·set-field 필드에서 예약 키(`__proto__`·`constructor`·`prototype`) 거부.
- **PROTECTED_FIELDS**: `set-field`의 phase·status는 `update-state` 전용으로 차단.
- **원자적 쓰기**: 임시 파일(`.tmp`) write → `os.replace` rename. `updatedAt` ISO 타임스탬프 갱신, 부모 디렉토리 자동 생성.
- **순방향 점프 차단**: `force-state`는 역방향 복구가 의도된 용도이므로, 순방향 점프에 `--allow-unsafe-force`를 요구해 아티팩트 검증 없는 게이트 우회를 막는다.

### 필드 마이그레이션

`read_context`는 각 토픽을 순회하며 `currentTask`가 있고 `currentStory`가 없을 때만 `currentStory`로 승격하고 `currentTask`를 제거한다. 두 필드가 동시 존재하면 no-op으로 `currentTask`를 보존한다(수동 정리 대상). CLI 플래그 `--topic`은 리네임하지 않는다 — 마이그레이션은 저장 필드에 한정된다.

## 제약사항

- **패리티 포트** — 레퍼런스 6 서브커맨드의 동작·외부 계약만 재구현한다. 신규 서브커맨드·동작 확장은 범위 밖이다.
- **전환표 미소유** — 전환표·`STATE_ORDER`를 엔진에 재정의하지 않는다. `state_machine.py`(E2-S1)가 정본을 소유하며 엔진은 import로만 소비한다.
- **config 스키마 미검증** — plumbing(파싱·타입 추론·읽기/쓰기)만 제공한다. 유효 네임스페이스·위험 tier 필드 검증은 config 스키마의 소관이다.
- **라이브 콜러 부분 전환** — 배포 스킬층 콜러(14 스킬 `.md` + 2 셸)는 Python 엔진 호출로 전환됐다(E2-S4). Node 훅층(`session-start.js` 등)은 `.tack/scripts/dev-context.js`를 계속 호출하며 그 재배선은 E7-S1(훅 Python port) 소관이고, dogfood 허브 SoT(`.harness/scripts/`)는 M1 별건이다. 엔진은 byte-identical 외부 계약을 보존해 콜러가 프리픽스 교체만으로 무전환 대체되도록 한다.
- **레퍼런스 `.js` 공존** — Node 훅층이 E7-S1 전까지 사용하므로 삭제하지 않는다(패리티 유지).
- **서브프로세스 테스트** — pytest는 CLI 계약(exit code·stdout·stderr) 검증을 위해 엔진을 `subprocess.run([sys.executable, SCRIPT, ...])`로 실행한다. `conftest.py`는 `--cov` 활성 시에만 `COVERAGE_PROCESS_START` + `sitecustomize`로 서브프로세스 커버리지를 배선한다. 실행은 `uv run --with pytest --with pytest-cov python -m pytest`.
