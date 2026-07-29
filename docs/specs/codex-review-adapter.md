# Codex 리뷰 어댑터 (adapter-codex-review)

> `codex exec`를 감싸 spec-review·plan-review를 1회 실행하고 Decision 한 줄을 돌려주는 외부-도구 어댑터. 실행 스킬 종류는 `dev-context.json`의 `phase:status`에서 파생되고, 루프 제어는 호출자가 소유한다.
>
> **대상 트리**: `template/` source (배포 destination은 이 트리의 렌더 결과) · **소유 스토리**: codex-review-glob-fix

## 개요

`/flow-spec` Step 4와 `/flow-plan` Step 7은 `config.spec.auto_review`·`config.plan.auto_review`가 `true`일 때 Codex 리뷰를 자동 실행한다. 이 어댑터가 그 실행 단위다 — 한 번 로드되면 리뷰 1회를 돌리고 `- Decision:` 줄을 stdout으로 돌려준다. READY/NOT READY에 따른 재시도·상태 전환은 돌려받은 호출자가 판단한다.

**tier**: 외부 도구(`codex` CLI)를 래핑하고 미가용 시 수동 폴백을 자체 선택하므로 5-tier 체계의 `adapter-*`다. skill-registry 발견 대상이 아니라 호출자가 이름으로 직접 Load하는 non-search adapter이며, `adapter-github-issue`·`adapter-dependency-analysis`와 같은 부류다.

두 phase가 **같은 문서를 그대로** 쓴다. spec-review와 plan-review로 분기하는 지점은 `REVIEW_KIND` 한 변수뿐이고, 파일 탐지 패턴·경로 필드·`codex exec` 프롬프트가 전부 그 값에서 파생된다. 분기마다 블록을 복제하지 않는 것이 이 설계의 축이다.

## 구조 / 스키마

### 실행 순서

문서 안 시퀀스 진술은 `## Execution Sequence` 한 곳뿐이다. 호출자도 이 절을 인용하며, 다른 절에 순서를 중복 진술하지 않는다.

```
Auto-Detect Entry Point §1 → §2 → §3 → Availability Gate → Path Validation → Parsing the Decision
```

두 가지 불변식이 이 순서를 고정한다.

- **§2를 건너뛰지 않는다** — `REVIEW_KIND`의 유일한 생산자다. `Parsing the Decision`이 소비 직전에 membership을 검증하므로, 미바인딩이면 codex를 부르기 전에 중단한다.
- **codex 실행 지점은 `Parsing the Decision` 한 곳뿐이다** — 실행 전 파일 목록 스냅샷이 호출보다 먼저 찍혀야 새 리뷰 파일을 식별할 수 있어 두 단계를 분리하지 않는다. 다른 절에서 `codex exec`를 실행하면 리뷰 1회당 두 번 돌고 리뷰 파일도 두 개 생긴다.

`## Isolation via DEV_CONTEXT_PATH`는 이 시퀀스에 포함되지 않는다 — fixture dev-context로 수동 실험할 때만 쓰는 별도 경로이며, 그 절의 `codex exec`는 자동 판정 경로에서 실행하지 않는다.

### phase → REVIEW_KIND 파생

| `phase:status` | `REVIEW_KIND` | 경로 필드 | 리뷰 파일 패턴 |
|---|---|---|---|
| `spec:reviewing` | `spec-review` | `spec` | `spec-review-<YYMMDDHHmmss>.md` |
| `plan:reviewing` | `plan-review` | `plan` | `plan-review-<YYMMDDHHmmss>.md` |
| 기타 | 실행 불가 — 상태별 안내 출력 후 exit 1 | | |

`case` 블록의 `*)` arm이 표의 `기타` 행을 인코딩한다 — 상태 테이블의 모든 행이 코드에 대응하며, 미처리 상태가 조용히 통과하지 않는다.

`PATTERN`은 이 값에서 파생된다:

```bash
PATTERN="${REVIEW_KIND}-*.md"
REVIEW_DIR="$(dirname "$CANON_PATH")"
```

리뷰 파일은 spec/plan 파일과 같은 디렉토리에 생성된다. 어댑터는 리뷰 파일을 쓰지 않는다 — 산출물 저장과 `dev-context.json` 필드 갱신은 Codex 리뷰 스킬(`specReview`·`planReview`)이 단독으로 소유한다.

### 배포 위치

| 경로 | 역할 |
|---|---|
| `template/.claude/skills/adapter-codex-review/SKILL.md` | 정본 (Copier 배포 source) |
| `template/.claude/skills/flow-spec/SKILL.md` | 호출자 — Step 4 |
| `template/.claude/skills/flow-plan/SKILL.md` | 호출자 — Step 7 |
| `scripts/codex-review-detection.test.js` | 회귀 테스트 + 전수 스캔 게이트 (`_subdirectory: template` 밖 — 배포 대상 아님) |
| `scripts/fixtures/codex-review-detection/pre-fix-section.md` | anti-vacuity fixture |

## 동작

### 새 리뷰 파일 탐지

`codex exec` 전후의 파일 목록을 비교해 이번 실행이 만든 파일을 식별한다. `-newer` 방식은 macOS의 타임스탬프 해상도 때문에 신뢰할 수 없어 쓰지 않는다.

```bash
BEFORE_FILES=$(find "$REVIEW_DIR" -maxdepth 1 -name "$PATTERN" 2>/dev/null | sort)
# … codex exec …
AFTER_FILES=$(find "$REVIEW_DIR" -maxdepth 1 -name "$PATTERN" 2>/dev/null | sort)
REVIEW_FILE=$(comm -13 <(echo "$BEFORE_FILES") <(echo "$AFTER_FILES") | tail -1)
```

열거는 `find`로 한다. **셸 글롭에 의존하지 않는 것이 요구사항**이다 — zsh는 변수 치환 결과를 글롭 확장하지 않으므로 `ls "$REVIEW_DIR"/$PATTERN`은 `spec-review-*.md`를 리터럴 파일명으로 찾고 매치 0건으로 끝난다. Claude Code의 Bash 도구가 zsh로 실행되기 때문에, 셸 글롭에 기대면 리뷰가 정상 생성돼도 어댑터가 실패로 판정하고 자동 루프 전체가 수동 폴백으로 낙하한다. `find`는 패턴을 인자로 받아 자체 매칭하므로 zsh·bash 양쪽에서 같은 결과를 낸다.

`comm -13`은 "before에 없고 after에 있는" 파일을 돌려주며, `BEFORE_FILES`가 빌 때 `echo`가 흘리는 빈 줄은 첫 스트림에만 존재하므로 자동으로 억제된다.

### 가드 3종

세 지점에서 fail-closed로 중단한다. 세 가드 모두 잘못된 입력으로 리뷰를 계속 진행하는 것보다 즉시 실패하는 쪽을 택한다.

| 가드 | 위치 | 차단 대상 |
|---|---|---|
| `REVIEW_KIND` membership (`case`) | `Parsing the Decision` 진입 | §2 미실행 상태에서의 codex 호출. `PATTERN`이 `-*.md`가 되어 매치 0건으로 끝나는 경로를 codex 실행 **전에** 끊는다 |
| `CANON_PATH` 바인딩 (`: "${CANON_PATH:?…}"`) | 같은 지점 | Path Validation 미실행. 없으면 `dirname ""` → `.`로 조용히 fallback해 리포지터리 루트를 뒤진다 |
| `EXEC_EXIT` 비-0 차단 | `codex exec` 직후 | 실패한 실행이 남긴 부분 파일의 `- Decision:` 줄이 유효 판정으로 통과하는 것 |

`:?` 가드는 command substitution 안이 아니라 top-level에 두어야 실행 셸이 실제로 종료한다.

세 가드는 `REVIEW_KIND`·`CANON_PATH`가 **같은 셸 프로세스**에 살아 있음을 전제한다. `## Execution Sequence`가 절을 하나씩 따르도록 진술하는 이유이며, 이 전제가 깨질 때의 동작은 아래 제약사항에 기록한다.

### 경로 검증

경로 읽기·검증·정규화는 `validate-path.js` 단일 호출이 처리한다 — `dev-context.json`에서 읽고, 빈값·절대경로·leading dash·경로 탐색(`..`)·제어 문자를 거부하고, `realpathSync()`로 정규화한 뒤 리포지터리 루트 내부인지 확인한다.

```bash
CANON_PATH=$(node .tack/scripts/validate-path.js --topic="$TOPIC" --field=<field>)
```

`REVIEW_DIR`이 leading dash로 시작해 `find`의 옵션으로 오인되는 경로는 이 검증으로 도달 불가다. `PATTERN`도 `-name "$PATTERN"`으로 인용돼 글롭 확장이 일어나지 않는다.

### 호출자 계약

`/flow-spec`·`/flow-plan`은 어댑터를 `Load .claude/skills/adapter-codex-review/SKILL.md` 한 줄로 로드하되, 다음 세 가지를 지시문에 명시한다.

1. **`## Execution Sequence`를 따른다** — 특정 절 이름을 종점으로 지목하지 않는다. 절 구조가 바뀌어도 호출자가 stale해지지 않는다.
2. **`REVIEW_KIND` 파생을 진술한다** — `derives REVIEW_KIND=<kind> from it`. 어댑터가 phase에서 스스로 파생하지만, 호출자 지시문이 이 단계를 누락하면 그 단계를 건너뛴 실행이 membership 가드에 걸려 자동 경로가 체계적으로 수동 폴백으로 떨어진다.
3. **폴백 조건을 진술한다** — 어댑터가 새 리뷰 파일 없이 종료하면(Availability Gate 실패, `codex exec` 비-0, 샌드박스 쓰기 차단) 수동 폴백을 보이고 정지한다.

어댑터를 로드하기 전에 호출자가 `config.codex.available`·`config.codex.authenticated`를 먼저 확인한다. 어댑터도 같은 게이트를 자체 보유하므로 이 검사는 이중이며, 호출자 쪽 검사가 어댑터 로드 자체를 아낀다.

Decision 파싱 결과에 대한 처리는 호출자가 소유한다 — `READY`/`READY WITH NOTE`는 다음 단계로, `NOT READY`는 Required Fixes 적용 후 이전 상태로 롤백하고 재시도한다(최대 3회). 리뷰 보고서는 LLM 생성 출력이므로 호출자는 신뢰 경계를 두고 문서화된 품질 게이트에 대응하는 구조·사실·형식 수정만 적용한다.

### 검증 방식

`scripts/codex-review-detection.test.js`가 두 층으로 강제한다. 실행법은 `node --test scripts/codex-review-detection.test.js` 하나다.

**1층 — 문서 코드블록 실행 회귀 테스트.** `## Parsing the Decision` 절의 bash 펜스 블록을 SKILL.md에서 **추출해 실제로 실행**한다. 정적 grep이 아니라 실행이어야 하는 이유는 검증 대상이 문법이 아니라 셸 의미론이기 때문이다. `codex exec` 줄만 스텁으로 치환하고 나머지는 문서 원문 그대로 돌린다 — SKILL.md가 SSOT로 남고 테스트가 그 문서를 읽으므로 코드 복제 drift가 없다.

매트릭스: 3케이스(신규 1개 생성 / 기존 2개 + 1개 추가 / 생성 없음) × zsh·bash × `REVIEW_KIND` 2종. 여기에 `codex exec` 실패 케이스와 가드 3종의 실행 커버리지가 더해진다. zsh·bash 중 하나라도 resolve되지 않으면 skip이 아니라 **실패**로 처리해 매트릭스가 조용히 반쪽으로 도는 것을 막는다.

셸 격리: `zsh -f` / `bash --noprofile --norc`로 실행하고 자식 환경에서 `BASH_ENV`·`ENV`·`ZDOTDIR`를 제거한다. zsh는 비대화형 스크립트에서도 `.zshenv`를 읽고 그 안의 별칭을 확장하므로, 격리하지 않으면 개발자의 `alias ls=…` 하나로 anti-vacuity 통제가 조용히 green이 된다.

anti-vacuity: 수정 전 블록을 체크인 fixture로 두고 같은 파이프라인에 통과시켜, zsh에서 실패하고 bash에서 통과함을 고정한다. 판별자로 **스텁이 만든 리뷰 파일이 실행 후에도 디스크에 존재함**을 함께 assert한다 — 이것이 없으면 "새 파일이 없어서 올바르게 실패했다"와 "존재하는 파일을 못 봐서 실패했다"가 같은 exit code·같은 stderr로 구분되지 않는다.

**2층 — 변수-글롭 전수 스캔 게이트.** `template/.claude/skills/**/SKILL.md`의 모든 bash 펜스 블록에서 같은 유형의 위반이 0건임을 강제한다.

탐지 정의는 "확장 직후 글롭 메타문자"가 아니다 — 그 정의로는 정작 대상인 `ls "$REVIEW_DIR"/$PATTERN`을 매치하지 못해 게이트가 공허해진다. 실제 술어는 **같은 bash 블록 안에서 글롭 메타문자(`*` `?` `[`)를 값에 담은 따옴표 대입으로 선언된 변수의 unquoted 확장**이다. quoted span 제거는 줄 단위로 한다 — 블록 단위로 하면 한 줄의 미종결 따옴표가 뒤따르는 줄들을 통째로 삼킨다.

탐지기는 순수 함수 하나로 존재하고, template 수집 경로와 fixture 입력이 그 함수의 별개 진입점이다. 실제 fixture로 정확히 2건을 잡음(under-detection 통제)과 `set -u` 빈 배열 패턴을 잡지 않음(over-detection 통제)을 양방향으로 고정한다.

## 제약사항

- **시퀀스는 단일 셸 호출을 전제한다** — 각 절을 별도 Bash 호출로 실행하면 `REVIEW_KIND`·`CANON_PATH`가 unbound가 되어 가드가 매번 트립한다. fail-closed라 오작동은 아니지만, 절을 나눠 실행하면 자동 경로가 통째로 막힌다. `## Execution Sequence`가 절을 하나씩 따르라고 진술하는 것이 유일한 강제 수단이며, 코드 수준 강제는 없다.
- **동시 리뷰 시 파일 선택이 불확정** — `comm -13` 결과에서 `tail -1`을 무조건 고른다. 같은 spec/plan 디렉토리를 대상으로 두 자동 리뷰가 동시에 돌면 둘 다 상대의 보고서가 생기기 전에 스냅샷을 찍고, 이후 여러 새 파일을 본다. 실행 식별자·기대 출력 경로·정확히-1건 가드가 없어 다른 실행의 Decision으로 상태가 전진할 수 있다.
- **테스트가 자동 실행 경로에 없다** — `node --test scripts/codex-review-detection.test.js`가 유일한 실행법이며 `wf-verification` Gate 4에 등록하지 않는다. Gate 4는 `pnpm test`를 실행하는데 이 저장소에 루트 `package.json`이 없어 실행 자체가 불가하다. Gate 4 재설계가 별도 이월로 이 갭을 소유한다.
- **전수 스캔 범위가 template 스킬 문서로 한정** — `template/.claude/skills/**/SKILL.md`의 `bash` 펜스 안쪽만 본다. 배포·dogfood 사본, Codex 스킬(`.codex/skills/`), 에이전트 파일, `*.sh`는 대상이 아니다. 확장 범위 사전 조사에서 실제 위반 0건·false positive 2건만 나와 오탐 억제 비용만 늘기 때문이다. 펜스 언어도 `bash` 한정이라 향후 ` ```sh ` 블록은 게이트를 우회한다.
- **탐지기 술어의 사각** — 따옴표 없는 대입(`PATTERN=*.md`), 블록 간 참조(A 블록에서 대입, B 블록에서 사용), 명령 치환 대입(`PATTERN=$(cat globs.txt)`), 배열은 잡지 못한다. 현재 코퍼스에 이 shape의 실제 사례는 없다.
- **`find`에 `-type f`가 없다** — 리뷰 파일 패턴과 같은 이름의 디렉토리가 있으면 선택될 수 있다.
- **dogfood 허브 사본의 version이 동결** — 이 저장소 루트 `.claude/skills/adapter-codex-review/SKILL.md`는 untracked 배포 사본이며 `## Parsing the Decision`·`## Execution Sequence` 내용은 정본과 동일하지만 frontmatter `version`은 갱신하지 않는다. 버전 값만으로 정본 대비 최신 여부를 판별할 수 없다. 루트 사본 전체 동기화는 "루트 dogfood stale" 이월이 소유한다.
