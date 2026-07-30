# dev-context 엔진

> `dev-context.json` 토픽 라이프사이클 상태와 2층(tracked shared / local) config 저장소를 관리하는 6 서브커맨드 CLI 엔진. 상태 전환 검증은 순수 모듈 `state_machine.py`에, config 키 검증은 순수 모듈 `config_schema.py`에 위임한다.

## 개요

`dev_context.py`는 tack 워크플로우의 상태 저장소를 조작하는 정본 CLI 엔진이다. 토픽 등록·상태 전환·필드 읽기/쓰기·config 점경로 처리·토픽 삭제·강제 전환을 6개 서브커맨드로 제공한다. 레퍼런스 하네스 `dev-context.js`가 89-test로 검증한 동작·외부 계약(stdout 형식·종료 코드·JSON 직렬화·경로 해석)을 byte 단위로 보존하는 Python 패리티 포트로 출발했으나, config 쓰기 경로는 레퍼런스에 없는 스키마 검증·layer 라우팅(`--layer` 플래그)으로 확장됐다 — 등록·전환·삭제·강제 전환 4개 서브커맨드와 읽기 경로는 여전히 레퍼런스와 byte 단위로 대칭이고, `set-field`의 config 분기만 레퍼런스 범위를 넘어선다.

엔진은 두 종류의 판정 로직을 소유하지 않는다. `from state_machine import ...`로 [phase 상태 머신](phase-state-machine.md)의 전환표·상태 순서·판정 함수를, `import config_schema`로 config 키의 네임스페이스·타입·layer 선언 조회·검증 함수를 각각 소비한다. 상태·스키마 로직(데이터 + 판정)과 정책 집행(I/O·차단·경고·CLI 배선)이 파일 경계로 분리되며, 엔진은 후자만 담당한다. `update-state`는 `is_valid_transition`/`allowed_transitions`로, `force-state`는 `is_known_state`/`is_forward_jump`/`STATE_ORDER`로, `set-field`의 config 분기는 `config_schema.lookup`/`check_type`/`layer_of`/`suggest`로 라우팅한다.

## 구조 / 스키마

### 위치

```
template/.tack/scripts/
├── state_machine.py       # import 대상 — 순수 상태 모듈 (별도 문서)
├── config_schema.py       # import 대상 — 순수 config 스키마 로더·검증 모듈
├── dev_context.py         # CLI 엔진
├── conftest.py            # pytest 픽스처(타입 추론 전용 합성 스키마 fixture 포함) + 서브프로세스 커버리지 배선
├── _dc_helpers.py         # 공유 테스트 헬퍼 (DEV_CONFIG_PATH 격리 주입, 스키마 fixture 배선 포함)
├── test_register_topic.py # 서브커맨드별 엔진 통합 pytest
├── test_update_state.py
├── test_set_field.py
├── test_read.py
├── test_config.py         # config 점경로 (스키마 검증 통합 케이스 포함)
├── test_config_schema.py  # config_schema.py 순수 모듈 단위 테스트
├── test_config_shared.py  # 읽기 병합 (local/shared leaf 우선순위, 부재·손상 degrade)
├── test_config_layers.py  # layer 라우팅 (쓰기 대상 결정·승격 거부·파일 생성·보존)
├── test_remove_topic.py
├── test_force_state.py
├── dev-context.js         # 레퍼런스 (승계 원천, 미삭제 — .codex/skills 3파일이 CLI로 호출)
└── dev-context.test.js    # 레퍼런스 89-test (이식 spec)
```

`template/.tack/scripts/`는 authoring source 경로이고 `.tack/scripts/`는 deploy destination이다. 엔진은 `dev-context.js`·`state_machine.py`·`config_schema.py`와 sibling으로 co-locate돼 import seam이 성립한다. 레퍼런스 `.js`는 삭제하지 않고 공존한다 — 배포 스킬층 콜러(E2-S4)와 훅층(E7-S1)은 Python으로 전환됐으나, `.codex/skills` 3파일이 `node dev-context.js`를 CLI로 계속 호출하므로(Codex cutover 이연) 유지되며, 두 엔진은 패리티 대조 근거로도 함께 유지된다.

### 파일 토폴로지

```
.tack/config.json                    tracked   file_format + shared 키. 템플릿에 포함되지 않고 첫 shared 쓰기 시 생성된다.
.tack/local/dev-context.json         ignored   current_topic · topics · local/cache 키
.tack/contracts/config-schema.json   tracked   config 키 계약 SSOT (Claude·Codex 공용)
```

`.tack/config.json`은 `{"file_format": "1.0", "config": {"<ns>": {"<key>": <value>}}}` 형태다. 커밋 대상이므로 매 쓰기가 diff 노이즈가 되지 않도록 타임스탬프 필드를 갖지 않는다.

### 경로 해석

세 경로 모두 env override를 우선하고, 미설정 시 서로 다른 기준으로 기본값을 유도한다.

| 경로 | env override | 기본값 유도 | 유도 기준 |
|------|--------------|------------|----------|
| local `dev-context.json` | `DEV_CONTEXT_PATH` | `../../.tack/local/dev-context.json` (`os.path.normpath`) | `__file__`(SCRIPT_DIR) 상대 |
| shared `config.json` | `DEV_CONFIG_PATH` | 해석된 local 경로의 `dirname` 2회 + `config.json` | **해석된 local 경로** 상대 |
| config 스키마 | `DEV_CONFIG_SCHEMA_PATH` | `../contracts/config-schema.json` (`os.path.normpath`) | `__file__`(SCRIPT_DIR) 상대 |

shared 경로 유도가 SCRIPT_DIR이 아니라 **해석된 local 경로**를 기준으로 하는 것은 의도된 비대칭이다 — SCRIPT_DIR 기준으로 유도하면 `DEV_CONTEXT_PATH`로 격리된 호출자(테스트·worktree)가 실제 저장소의 공유 파일을 읽고 쓰게 된다. 스키마 경로는 배포 산출물의 고정 위치이므로 격리와 함께 움직일 필요가 없어 SCRIPT_DIR 기준을 유지한다. 렌더 스모크 테스트는 `DEV_CONFIG_PATH`를 설정하지 않고 이 2-hop 유도에 의존하므로 hop 수는 고정값으로 취급한다.

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

토픽 dict의 키 삽입 순서(phase·status·spec·specReview·plan·planReview·currentStory·createdAt·updatedAt)는 레퍼런스와 일치한다. `read_context`는 로드 시 `topics`·`current_topic`·`config`를 정규화하고, 각 토픽의 `currentTask`→`currentStory` 필드 마이그레이션을 적용한다. 이 JSON은 local 층의 in-file `config` 객체만 담는다 — shared 층의 leaf는 별도 파일(`.tack/config.json`)에 있고 읽기 시점에 병합된다.

### config-schema.json 계약

`.tack/contracts/config-schema.json`은 config 키의 기계 판독 SSOT다. 최상위에 `file_format`·`type_values`(`string`|`boolean`|`integer`|`array`)·`layer_values`(`shared`|`local`|`cache`)·`default_semantics` 설명 문자열을 두고, `namespaces.<ns>.<key>`마다 `type`·`layer`·`default`·`description` 4개 필드를 선언한다. 10개 네임스페이스, 23개 키를 선언한다.

| ns | 키 | layer | 비고 |
|---|---|---|---|
| git | pushRemote·pullRemote·baseBranch·branchPattern (4) | shared | `/flow-setup`이 기록 |
| docs | sourceFilter (1) | shared | 배열, 빈 배열 == 필터 없음 |
| graphify | targets (1) | shared | 배열, 빈 배열이면 풀 빌드 거부 |
| dev_impl | auto_start·auto_commit·batch_mode (local) · currentBatchRunning·currentBatchTopic (cache) (5) | local 3 · cache 2 | 배치 상태 2키는 성격상 휘발이지만 경로 문자열 불변을 위해 네임스페이스는 `dev_impl` 유지 |
| review | adversarial_enabled (1) | local | |
| spec | auto_review (1) | local | |
| plan | auto_review (1) | local | |
| codex | available·authenticated·version·checked_at (4) | cache | `detect-and-cache.js`(레거시 Node 엔진)가 기록 |
| gh | available·native_subissue·version·checked_at (4) | cache | `/flow-init`이 기록 |
| risk | high_gate_enabled (1) | shared | default `true` — 스키마에서 유일하게 `true` 기본값을 갖는 키 |

`default`는 선언 메타데이터일 뿐 런타임 폴백이 아니다 — `read`는 미설정 키에 대해 `default`를 합성하지 않고 빈 출력을 유지한다("미설정" 의미 보존). `config.risk.high_gate_enabled`는 스키마 선언·저장·조회(읽기/쓰기)만 제공한다 — 이 값을 읽어 human approval gate를 켜고 끄는 소비 로직은 `wf-risk-routing`·`/flow-review` 어디에도 아직 배선돼 있지 않다.

### 진입점·인자 파싱

- **진입점**: `#!/usr/bin/env python3` shebang + `python3 dev_context.py <subcommand> [--flag=value]` 직접 호출. uv 래핑·`.venv` 부트스트랩은 스크립트 밖 환경 관심사로 분리한다. 레퍼런스 `node dev-context.js` 직접 호출과 대칭이다.
- **인자 파싱**: 레퍼런스 `parseArgs`를 수동 파싱으로 이식한다(argparse 미채택). `--key=value` 정규식(`^--([^=]+)=(.*)\Z`)과 값 없는 boolean flag(`--allow-unsafe-force` → `True`)를 파싱한다. `\Z` 앵커 + DOTALL 미사용으로 JS `/^--([^=]+)=(.*)$/`(no `s` flag)의 개행 처리 동작을 재현한다.

## 동작

### 서브커맨드

| 서브커맨드 | 필수 인자 | 동작 |
|-----------|----------|------|
| `register-topic` | `--topic` `--spec` | 토픽을 `spec:drafting`으로 신규 등록. 중복 시 die(현재 상태 안내), 레거시 필드(`current_spec`·`specConfirmed`·`planConfirmed`) 정리, `current_topic` 설정 |
| `update-state` | `--topic` `--phase` `--status` | `is_valid_transition`으로 검증 후 전환. 동일 상태는 idempotent no-op(파일 미변경). 무효 전환은 die + `allowed_transitions` 안내 |
| `set-field` | `--field` (`--topic` `--value` `--layer`) | 글로벌(`current_topic`·`config.<ns>.<key>`)/토픽 필드 분기. config 쓰기는 스키마 검증(ns·key·타입)과 `--layer` 라우팅을 거쳐 목적지 파일을 결정한다. phase·status 차단, 예약 키 거부 |
| `remove-topic` | `--topic` | 토픽 삭제. `current_topic`이 삭제 대상이면 남은 토픽 중 첫 키 또는 null로 전환 |
| `read` | `--field` (`--topic`) | 글로벌/토픽 필드 조회. `--field` 없으면 사용법 die. config 읽기는 local→shared leaf 우선순위 병합이며 스키마를 조회하지 않는다. config 배열은 `\n` join |
| `force-state` | `--topic` `--phase` `--status` | `is_known_state` 검증 후 전환표 우회 강제 전환. `is_forward_jump`이 순방향이면 `--allow-unsafe-force` 요구, 강제 시 stderr 경고 |

`--layer`는 `set-field`의 config 점경로 쓰기에만 의미가 있다. 다른 서브커맨드·다른 필드 축에 오면 명시 거부한다(아래 쓰기 검증·라우팅 절 1~4행).

### config 점경로 처리

`parse_config_path`는 `config.<ns>.<key>` 깊이 2 고정 파싱(세그먼트 3개·`config` prefix·비어있지 않은 ns/key)을 수행하고 예약 키를 거부한다. `coerce_config_value`는 config 전용 타입 추론을 적용한다:

- `'true'`/`'false'` → bool
- `^-?[0-9]+$` → int
- `^\s*\[.*\]\s*$` → JSON 배열(문자열 원소만, 줄바꿈·비문자열 원소 위반 시 die)
- 그 외 → str

`[invalid`(닫히지 않음)·`[A-Z].*`(`]` 뒤 문자) 같은 스칼라는 배열 패턴에 미매치해 문자열로 보존된다. 토픽 필드 값은 타입 추론 없이 문자열 그대로 저장한다 — 타입 추론은 config 전용이다. 이 타입 추론 규칙 자체는 변경되지 않았다. 추론된 타입이 스키마 선언 타입과 일치하는지, 네임스페이스·키가 스키마에 존재하는지는 아래 쓰기 검증·라우팅 절에서 별도로 판정한다.

### 읽기 병합

`read --field=config.<ns>.<key>`는 leaf 단위로 local과 shared 두 층을 병합한다.

1. `resolve_config_leaf`가 우선순위 내림차순 iterable(local → shared)을 순회해 첫 own-property 히트를 반환한다. 값이 JSON `null`·빈 배열·`false`여도 앞선 layer에 own property가 있으면 그 layer가 이긴다 — Python dict의 `in` 검사가 곧 hasOwn 가드다.
2. 두 층 모두 미스면 미설정 센티널(`_MISSING`)을 반환하고, `read`는 빈 출력을 낸다. 스키마 `default`는 합성하지 않는다.
3. 배열은 통째 교체다 — 두 층을 concat하지 않는다.
4. 층은 generator로 넘겨 지연 획득한다. local이 답하는 읽기는 shared 파일을 열지 않으므로, 손상된 shared 파일의 경고가 무관한 읽기마다 반복 출력되지 않는다.
5. shared 파일이 없으면 빈 layer(`{"file_format": "1.0", "config": {}}`)로 간주해 예외 없이 진행한다(G5). JSON 파싱 실패·최상위가 dict가 아님·`config`가 dict가 아님도 같은 방식으로 빈 layer로 degrade하며, stderr에 경고 한 줄을 남기고 exit 0을 유지한다 — 손상된 shared 파일 하나가 워크플로 진입 전체를 막지 않는다.
6. config 배열의 각 원소는 emit 시 `_js_string`을 통과한다(bool→`true`/`false`, `None`→빈 문자열) — 손으로 편집된 shared 파일에 비-문자열 원소가 들어와도 `read`가 exit 1로 죽지 않는다.
7. `read`는 스키마를 조회하지 않는다. 알 수 없는 ns·key도 exit 0 + 빈 출력이다 — 조회 한 번이 워크플로 진입을 막지 않기 위함이다.
8. `read`에 `--layer`가 오면 die한다 — 병합된 값 하나만 출력하는 것이 계약이고, 어느 층에서 왔는지(provenance) 표시하는 기능은 계약에 없다. layer 선택은 `set-field` 전용이다.

### 쓰기 검증·라우팅

`set-field`의 config 분기는 아래 순서로 검사한다. 위에서 die하면 그 아래 단계는 실행되지 않는다.

| 순서 | 위치 | 판정 |
|---|---|---|
| 1 | `main()` | `--layer`가 지정됐는데 서브커맨드가 `set-field`가 아니면 die (`read`일 때는 병합 계약을 설명하는 부연 문구 추가) |
| 2 | `cmd_set_field` | `--field` 부재 또는 `--value` 키 자체 부재(`in args` 미포함) → die |
| 3 | `cmd_set_field` | `--layer`가 지정됐는데 필드가 `config.<ns>.<key>` 점경로가 아니면 die |
| 4 | `cmd_set_field` | config 점경로인데 `--topic`이 함께 오면 die |
| 5 | `parse_config_path` | 세그먼트 3개·`config` prefix·ns/key 비어있지 않음·예약 키(`__proto__`·`constructor`·`prototype`) 아님 |
| 6 | `_validate_layer_flag` | `--layer` 값이 `local`\|`shared` 중 하나(또는 미지정) — 스키마 조회보다 먼저 실행해 플래그 오타가 "알 수 없는 네임스페이스"로 오표시되지 않게 한다 |
| 7 | `load_config_schema` | 스키마 파일 로드. 부재·손상 시 fail-closed die (해석된 경로를 메시지에 포함) |
| 8 | `validate_config_write` | 네임스페이스 조회 → 키 조회 → `coerce_config_value` → declared type 일치 검사. 위반은 오타 근접 후보(`difflib`, 최대 3개, cutoff 0.6)와 함께 die |
| 9 | `resolve_write_target` | `WRITE_ROUTES` 표에서 목적지 결정. 승격 거부는 타입 검사 **다음**에 판정해 타입 오류가 먼저 보고되게 한다 |
| 10 | `WRITE_TARGETS[target]` | 결정된 목적지 파일에 실제로 쓴다 |

라우팅 표(선언 layer × `--layer` 요청):

| 선언 layer | `--layer` 미지정 | `--layer=local` | `--layer=shared` |
|---|---|---|---|
| `shared` | `.tack/config.json` | `.tack/local/dev-context.json` | `.tack/config.json` |
| `local` | `.tack/local/dev-context.json` | `.tack/local/dev-context.json` | 거부 |
| `cache` | `.tack/local/dev-context.json` | `.tack/local/dev-context.json` | 거부 |
| 미선언(스키마 결함) | `local` 행과 동일 폴백 | 동일 | 거부 |

`--layer`로 지정 가능한 값은 이 표의 **요청 열**에서 유도된 `{local, shared}`뿐이다 — `cache`는 선언 가능한 layer이지만 지정 가능한 목적지가 아니며 항상 `local` 파일로 접힌다.

shared 목적지 쓰기의 세부:

- shared 파일이 없으면 `{"file_format": "1.0", "config": {...}}` 형태로 새로 생성한다(최상위 키 정확히 2개). 템플릿에는 포함하지 않는다.
- 기존 shared 파일이 파싱 불가능(비-JSON, 최상위가 dict 아님, `config`가 dict 아님)하면 die — 손상된 tracked 파일을 단일 키로 덮어쓰지 않는다. 안내 메시지는 파일을 고치거나 `--layer=local`로 개인 층에 쓰라고 제안한다.
- 대상 네임스페이스 자리가 이미 존재하는데 dict가 아니면 die — 조용히 dict로 갈아끼우면 커밋된 내용이 사라진다.
- 기존 shared 파일의 무관한 네임스페이스·키·최상위 필드는 read-modify-write로 보존된다.
- 타임스탬프 필드를 넣지 않는다 — 매 쓰기가 tracked diff 노이즈가 되지 않도록.
- `atomic_write_json`(임시 파일 write + `os.replace`)이 local·shared 두 목적지 공통 쓰기 관용구다. `write_context`(local 전용)는 `updatedAt` 스탬핑 후 이를 호출한다.

### 읽기 출력 계약

- null/미설정 스칼라 → 빈 줄(`"\n"`)
- 스칼라 값 → `"<value>\n"` (bool은 `_js_string`으로 `true`/`false` 변환해 JS `String()` 재현)
- config 배열 → 원소를 `_js_string`으로 변환 후 `\n`으로 join + trailing `\n`
- 빈 배열 == 미설정 → 빈 줄(동일 출력)
- config read는 hasOwn 가드로 상속 속성을 차단한다. Python dict는 상속 데이터 키가 없어 `in` 검사가 곧 hasOwn 가드다(local·shared 두 층 모두 동일 적용)

### 방어·안전성

- **prototype-pollution 방어**: config 세그먼트·토픽 이름(`force-state`)·set-field 필드에서 예약 키(`__proto__`·`constructor`·`prototype`) 거부. `resolve_config_leaf`도 layer 데이터가 파일에서 온 신뢰 밖 값이므로 같은 예약 키를 재차 차단한다.
- **PROTECTED_FIELDS**: `set-field`의 phase·status는 `update-state` 전용으로 차단.
- **원자적 쓰기**: 임시 파일(`.tmp`) write → `os.replace` rename. local 쓰기는 `updatedAt` ISO 타임스탬프를 갱신하고, 부모 디렉토리를 자동 생성한다. shared 쓰기는 타임스탬프를 갖지 않는다.
- **쓰기 중단(fail-closed)**: 스키마 파일 부재·손상, shared config 파일 손상, shared 네임스페이스 자리가 비-dict인 경우 모두 die하고 파일을 만들지도 건드리지도 않는다. `read`는 이 어느 경우에도 영향받지 않는다.
- **순방향 점프 차단**: `force-state`는 역방향 복구가 의도된 용도이므로, 순방향 점프에 `--allow-unsafe-force`를 요구해 아티팩트 검증 없는 게이트 우회를 막는다.

### 필드 마이그레이션

`read_context`는 각 토픽을 순회하며 `currentTask`가 있고 `currentStory`가 없을 때만 `currentStory`로 승격하고 `currentTask`를 제거한다. 두 필드가 동시 존재하면 no-op으로 `currentTask`를 보존한다(수동 정리 대상). CLI 플래그 `--topic`은 리네임하지 않는다 — 마이그레이션은 저장 필드에 한정된다.

## 제약사항

- **패리티 포트 + 국소 확장** — 등록·전환·삭제·강제 전환 4개 서브커맨드와 `read`의 외부 계약은 레퍼런스 6 서브커맨드와 byte 단위로 대칭이다. `set-field`의 config 분기(스키마 검증·`--layer` 라우팅)만 레퍼런스 `dev-context.js`에 없는 확장이며, 이 확장이 있어야 `config.<ns>.<key>` 쓰기가 어느 파일로 가는지 계약으로 고정된다.
- **전환표 미소유** — 전환표·`STATE_ORDER`를 엔진에 재정의하지 않는다. `state_machine.py`(E2-S1)가 정본을 소유하며 엔진은 import로만 소비한다.
- **read는 layer-blind** — layer 강제는 쓰기 경로(`set-field`)에만 있다. 손으로 편집된 `.tack/config.json`이 `cache`·`local` 성격의 키를 담고 있어도, local 미스 시 그 값이 그대로 서빙된다. 스펙이 이 한계를 수용한다 — 읽기가 스키마를 로드해 걸러내면 스키마 파일 하나가 조회 실패로 워크플로 진입을 막게 되기 때문이다.
- **손상된 shared 파일은 조용히 빈 layer로 degrade한다** — `read`는 stderr 경고만 남기고 exit 0 + shared 키의 문서화된 기본 동작(빈 출력)으로 폴백한다. 손상을 적극적으로 알리는 채널은 이 stderr 한 줄뿐이다.
- **config leaf를 제거하는 CLI 경로가 없다** — `--value=null`은 config 점경로에서 타입 추론을 거쳐 리터럴 문자열 `"null"`로 저장된다(빈 배열·빈 문자열로 대체하거나 파일을 직접 편집해야 실질적 제거가 된다). 이는 `current_topic`·토픽 필드 경로와 다르다 — 그 두 경로는 `--value=null`을 실제 JSON `None`으로 변환해 저장한다.
- **`detect-and-cache.js`가 스키마 검증을 우회한다** — `template/.claude/scripts/codex/detect-and-cache.js`는 `config.codex.*` 4필드를 레거시 Node 엔진(`node dev-context.js`)으로 기록하므로 Python 엔진의 스키마 검증을 거치지 않는다. 훅층 Codex cutover가 선행돼야 닫히는 별건이다.
- **라이브 콜러 부분 전환** — 배포 스킬층 콜러(`flow-setup`·`flow-init` 포함)는 Python 엔진 호출로 전환돼 있고, 두 스킬 문서와 `git-workflow.md` 규칙은 config 쓰기 목적지(shared vs local)를 키별로 정확히 기술한다. 훅층은 `dev-context.json`을 직접 읽어 dev-context.js CLI를 경유하지 않으며 Python으로 포트돼 있다. dev-context.js를 CLI로 호출하는 잔존 콜러는 `.codex/skills` 3파일(spec-review·plan-review·rules-and-inputs)이며, 이 파일들은 config를 쓰지 않고 상태 조회·전환만 호출한다. dogfood 허브 SoT(`.harness/scripts/`)는 별건이다. 엔진은 등록·전환·삭제·강제 전환·읽기 경로에서 byte-identical 외부 계약을 보존해 콜러가 프리픽스 교체만으로 무전환 대체되도록 한다.
- **레퍼런스 `.js` 공존** — `.codex/skills` 3파일이 CLI로 사용하므로 삭제하지 않는다(Codex cutover 선행 필요, 패리티 유지).
- **서브프로세스 테스트** — pytest는 CLI 계약(exit code·stdout·stderr) 검증을 위해 엔진을 `subprocess.run([sys.executable, SCRIPT, ...])`로 실행한다. `_dc_helpers.py`는 `DEV_CONTEXT_PATH`·`DEV_CONFIG_PATH`를 매 호출에 항상 주입해 shared config 층까지 테스트별로 격리하고, `schema_path` 인자로 합성 스키마(`conftest.py`의 `fixture_schema_path`)를 선택 주입할 수 있다 — 실사용 인벤토리에 `integer` 타입 키가 없어 타입 추론 회귀 테스트가 이 fixture에 의존한다. `conftest.py`는 `--cov` 활성 시에만 `COVERAGE_PROCESS_START` + `sitecustomize`로 서브프로세스 커버리지를 배선한다. 실행은 `uv run --with pytest --with pytest-cov python -m pytest`.
