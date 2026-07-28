# 위험 tier 라우팅 — 골격 의례와 리뷰 깊이

> plan에 기록된 per-Story `**Risk Tier**`를 실행 라우터로 소비하는 구조. tier가 `high`인 Story는 `scaffold` 골격 Story로 분해되고, tier가 `high`인 토픽은 `/flow-review`에서 2단 리뷰(architect 구조 판정 → lock → code-reviewer unit + security-reviewer)를 거친다.
>
> **대상 트리**: `template/` source (배포 destination은 이 트리의 렌더 결과) · **소유 스토리**: E3-S4 (M1 임계 집합)

## 개요

위험 tier는 두 층으로 나뉜다 — **판정**(무엇이 `high`인가)과 **라우팅**(`high`이면 무엇이 달라지는가). 판정은 `template/.tack/contracts/implementation-plan.md`의 `## Risk Tier` 절이 소유하고, 라우팅은 `template/.claude/skills/wf-risk-routing/SKILL.md`가 소유한다. 계약은 tier 값을 기록만 하며 어떤 분기도 정의하지 않는다고 명시하고, 라우팅 소유자를 그 스킬로 지목한다.

라우팅 대상은 두 개다:

- **골격 의례** — planner가 plan 저작 시 `high` + `Type ∈ {tdd, refactor}` Story를 `scaffold` Story + 구현 Story로 분해한다. 함수 본문 이전에 구조가 정적 검사 + import 스모크로 검증된다.
- **리뷰 깊이** — `/flow-review`가 `topicTier == high`일 때 구조 판정(stage 1)을 잠근 뒤 unit 리뷰(stage 2)를 돌린다. 아키텍처 지적이 line-by-line 홍수에 파묻히지 않게 한다.

라우팅은 **승격만** 정의한다. `low`·`normal` 경로의 리뷰어 구성은 tier 라우팅 도입 이전과 동일하며 어떤 리뷰어도 생략되지 않는다.

## 구조 / 스키마

### 소유처 배분

| 파일 | 소유 대상 |
|------|----------|
| `template/.claude/skills/wf-risk-routing/SKILL.md` | tier→의례 라우팅표, 필드 부재 `normal` fallback, `topicTier` 유도 규칙 |
| `template/.tack/contracts/implementation-plan.md` | tier 판정표(`## Risk Tier`), Story Type enum 6종, `scaffold` 발동 조건, `### scaffold 완료 판정 (언어별)` |
| `template/.claude/skills/flow-review/SKILL.md` | stage 1 rubric·lock 판정, stage 2 스코프 산출, 재진입 재개 지점, adversarial 게이트, human gate |
| `template/.claude/agents/architect.md` | stage-1 구조 판정 프로세스 본문 (`tools` 불변) |
| `template/.claude/agents/code-reviewer.md` | stage-2 unit 스코프 프로세스 본문 |
| `template/.claude/agents/planner.md` | `high` + 로직-bearing Story 분해 규칙 |
| `template/.tack/contracts/review-report.md` | `architect (stage 1)` Reviewers 행, `## Architecture Review (stage 1)` 섹션, `## Tier Notes` 섹션 |

### tier 입력 해석

| 입력 상태 | 해석 |
|-----------|------|
| `**Risk Tier**` 값이 `low`\|`normal`\|`high` | 그 값 |
| 필드 부재 | `normal` — tier를 새로 산정하지 않고 판정표를 열지 않는다 |
| 값이 3종 중 어느 것도 아님 | `normal` + 호출자 산출물에 한 줄 노트 |

`normal` fallback은 tier 라우팅 도입 이전의 현행 동작과 같으므로, 필드가 없는 기존 plan은 동작이 바뀌지 않는다. 계약이 필드 부재를 warning 없이 통과시키는 것과 일관된다.

토픽 단위 라우팅은 `topicTier = max(plan의 모든 Story의 Risk Tier)`(순서 `low < normal < high`)로 집계한다. 집계 스코프는 완료된 Story를 포함한 **모든** Story다.

### 라우팅표

canonical 출처는 `wf-risk-routing`이며 아래는 그 표의 요약이다.

| tier | 골격 의례 (planner, plan 저작 시) | 리뷰 깊이 (`/flow-review`) |
|------|----------------------------------|----------------------------|
| `low` | 없음 | code-reviewer + security-reviewer 병렬 |
| `normal` | 없음 | code-reviewer + security-reviewer 병렬 |
| `high` | `Type ∈ {tdd, refactor}` Story에 한해 `scaffold` + 구현 Story로 분해 | stage 1 architect → lock → stage 2 code-reviewer(unit) + security-reviewer, adversarial 승격, human gate 1회 |

### `scaffold` Story Type

Story Type enum은 `tdd|config|infra|refactor|prompt|scaffold` 6종이다. `scaffold`는 시그니처 + 타입/인터페이스 + 호출·이벤트 체인 배선 + throwing stub만 작성하며 함수 본문 로직을 담지 않는다. 발동 조건은 `Risk Tier == high` AND `Type ∈ {tdd, refactor}` Story의 분해 산물이고, planner가 plan 저작 시 1회만 생성한다.

완료 판정은 언어별 정적 검사 + entry 모듈 import 스모크다 — 판정표의 canonical 출처는 계약의 `### scaffold 완료 판정 (언어별)` 절이며 다른 컴포넌트는 이 절을 인용한다. 정적 검사만으로는 배선이 실제로 로드되는지 확인되지 않으므로 import 스모크를 함께 요구한다.

import 스모크는 인터프리터 인라인 payload(`python3 -c`, `node -e`)를 쓰므로 `flow-impl`의 mutating 토큰 검사가 닿지 않는다. 두 층으로 방어한다 — **1차**는 payload가 정해진 두 템플릿과 정확히 일치하고 치환값이 전체 일치 정규식(`<module>`은 `^[A-Za-z_][A-Za-z0-9_.]*$`, `<entry>`는 `^[A-Za-z0-9_./-]+$`, leading `-`·`..` 거부)을 만족하는지, **2차**는 치환값에 `;`·개행·백틱·`$(`·따옴표·`__import__`·`open(`·`exec`·`eval`·`require(`가 없는지다. 2차 denylist는 치환값에만 적용한다 — 템플릿 리터럴 자체가 `;`를 포함하므로 리터럴에 적용하면 JavaScript 경로가 실행 불가가 된다.

## 동작

### planner — plan 저작 시 분해

planner는 각 Story에 tier를 부여할 때 계약의 `## Risk Tier` 절을 적용하고, `high` + `Type ∈ {tdd, refactor}` Story를 `scaffold` Story + 함수별 구현 Story로 분해한다. 그 외 Type은 분해하지 않는다.

분해는 plan 저작 시 1회만 적용하며 분해로 생성된 자식 Story는 재분해 대상이 아니다. 자식 Story도 부모와 같은 delta를 접촉해 `high`로 유지되므로, 종료 조건 없이는 규칙이 자기 출력에 재발화한다.

`plan-review`는 두 개의 carve-out을 갖는다 — Gate 3(Story 독립성)은 `scaffold` Story가 독립 실행·커밋 가능 기준은 충족하되 독립 배포 가능 기준은 동일 PR 단위에서 평가하고, Gate 5(Story 타입 정확성)는 선행 `scaffold` Story를 가진 `high` tier `tdd`·`refactor` Story를 골격 의례 충족으로 간주한다. carve-out이 없으면 `plan-review`가 분해 결과를 매번 FAIL 처리한다.

### `/flow-impl` — scaffold Story 실행

`/flow-impl`은 이미 분해된 plan을 실행하며 실행 시점에 Story를 분해하지 않는다. tier로 하는 일은 두 가지다:

1. `scaffold` Type Story를 만나면 계약의 완료 판정 절을 기준으로 적용한다. `scaffold`는 Direct handling으로 처리되어 tdd-specialist(RED-GREEN-REFACTOR)와 `simplify` 후속 호출에서 제외된다 — 골격에 본문 로직이 없어 대상이 아니다.
2. `high` + `Type ∈ {tdd, refactor}` Story에 선행 `scaffold` Story가 없으면 그 사실을 Story 브리핑에 한 줄로 남기고 그대로 실행한다. 실행을 중단하지 않으며 Story를 분해하지도 않는다.

`--all` 배치 루프는 `scaffold` Story를 정상 통과하며, 정적 검사·import 스모크 실패는 배치 중단 조건에 포함된다.

### `/flow-review` — 2단 리뷰

`topicTier ∈ {low, normal}`이면 stage 구분·lock·human gate 없이 code-reviewer + security-reviewer가 전체 변경 범위를 병렬로 본다.

`topicTier == high`이면 stage 1에서 architect를 단독 호출한다. architect는 8문항 rubric — (1) 변경이 맞는 위치에 있는가, (2) 추상 수준이 주변 코드와 맞는가, (3) 애초에 해야 할 일인가, (4) 같은 일을 하는 것이 이미 있는가, (5) 기존 패턴과 일관적인가, (6) 호출·이벤트 체인이 완결됐는가, (7) `component-boundaries.md`의 5-tier 배치가 맞는가, (8) 스킬·규칙 호출이 Delegation Pattern 표준 형태를 쓰는가 — 를 PASS / FAIL / NOTE로 판정한다. FAIL이 1건 이상이면 `lock: blocked`, 0건이면 `lock: locked`이며 advisory NOTE는 lock을 막지 않는다.

`lock: locked`면 stage 2로 진행해 code-reviewer(변경 파일 목록 한정 unit 스코프) + security-reviewer를 병렬 호출한다. code-reviewer는 stage 1이 잠근 구조 배치를 재론하지 않는다. 스코프 목록은 stage 2 진입 시점과 CRITICAL·HIGH 수정 후 재리뷰 시점 각각에서 `git diff --name-only <pullRemote>/<baseBranch>...HEAD`로 재산출한다 — 고정 목록을 재사용하면 review-fix commit이 추가한 신규 파일이 누락된다.

`lock: blocked`면 stage 2를 실행하지 않고, 정지 전에 stage-1-only review-report를 쓴다. 이 파일이 다음 실행의 재개 지점 입력이며, 보류 상태에서도 stage-1 원문과 lock 값이 보존돼 재실행 비용이 줄어든다. 토픽은 `review:in-progress`로 유지된다 — `/flow-review`는 `review → impl` 역전이를 만들지 않는다.

lock 판정을 파일에 기록하는 주체는 `/flow-review`다. architect의 `tools`(`Read, Grep, Glob`)는 확장하지 않는다.

### 상태 게이트와 재진입

`/flow-review` Step 1은 exhaustive 상태 테이블이다.

| `phase:status` | 동작 |
|----------------|------|
| `impl:in-progress` | 첫 진입 — `review:in-progress`로 전환 후 진행 |
| `review:in-progress` | 재진입 — 전환 없이 진행, `SAVED_SHA`만 재캡처 |
| (그 외) | 게이트 실패 메시지 출력 후 정지 |

재진입 시 재개 지점은 최신 `review-report-*.md`의 `lock` 값이 정한다. 아래 표는 위에서부터 첫 매칭으로 적용한다.

| 조건 (첫 매칭) | 재개 지점 |
|----------------|-----------|
| `topicTier != high` | Step 5부터 (병렬 리뷰) |
| review-report 파일 없음 | Step 5부터 |
| `lock: locked` | stage 2부터 (stage 1 재사용) |
| `lock: blocked` | stage 1부터 |
| `lock` 파싱 실패 | stage 1부터 |

마지막 행은 `## Architecture Review (stage 1)` 섹션이 없는 이전 형식 보고서를 흡수한다. stage 1을 재사용한 실행은 `architect (stage 1)` 행을 `skipped` / skipReason `stage 1 reused`로 적고 직전 보고서의 섹션 본문과 `lock: locked` 라인을 그대로 옮겨 적는다 — lock 라인은 다음 재진입의 파싱 입력이다.

### adversarial 승격과 human gate

adversarial 리뷰 실행 조건은 `(topicTier == high OR adversarial_enabled == true) AND codex.available AND codex.authenticated`다. `high` 토픽에서는 `config.review.adversarial_enabled` 값과 무관하게 자동 승격된다.

human gate는 review-report 작성 후 완료 보고 직전에 `AskUserQuestion`으로 1회 발동한다. `/flow-impl`의 배치 루프와 무관하며(`/flow-review`는 사용자가 별도 호출하는 독립 커맨드), `lock: blocked` 경로에서는 발동하지 않는다. `AskUserQuestion`을 쓸 수 없는 headless·CI 환경에서는 승인 없이 진행하지 않고 정지 + 안내를 출력한다.

### 검증 방식

편집 대상이 전부 `template/` 하위이고 이 저장소의 hub 세션은 부트스트랩 하네스(`.claude/` + `.harness/`)로 동작하므로, 편집한 `template/` 스킬은 이 저장소에서 실행되지 않는다. 따라서 검증은 라이브 실행이 아니라 `scripts/risk-routing-assertions.test.js`의 **정적 assertion**이다 — 합성 plan fixture를 입력으로 두고 편집된 컴포넌트 파일에 라우팅 규칙·Type 분기·stage 분기·`normal` fallback·표준 위임 문구가 존재하는지 확인한다.

이 스위트는 두 층의 anti-vacuity 통제군을 갖는다 — 무관한 컴포넌트 본문(fixture)에서 6개 assertion이 전부 실패하는지, 그리고 실제 대상 파일에서 해당 절만 제거했을 때 각 assertion이 실패하는지 확인한다. 후자가 "다른 위치의 우연한 토큰으로 통과" 실패 모드를 막는다. fixture와 스크립트는 저장소 루트 `scripts/` 아래에 둔다 — `copier.yml`의 `_subdirectory: template`으로 렌더 대상 밖이며, `template/` 하위에 두면 배포 매니페스트가 fixture를 배포 대상으로 열거한다.

## 제약사항

- **승격만 정의** — `low`·`normal` 경로에서 리뷰어를 생략하지 않는다. 라우팅표는 어떤 리뷰어도 제거하지 않는다.
- **판정표 비복제** — 무엇이 `high`인가(6행 판정표·보안 마커 목록)는 `implementation-plan.md` 계약이 단일 소유하며 `wf-risk-routing`은 인용만 한다. 조건 변경 시 계약 한 곳만 갱신된다.
- **골격 분해는 plan 저작 시 1회** — planner가 수행하며 실행 시점 분해와 자식 Story 재분해는 없다. `/flow-impl`은 분해된 plan을 실행할 뿐이다.
- **골격 의례 강제 없음** — `high` + `tdd`/`refactor` Story에 선행 `scaffold` Story가 없어도 `/flow-impl`은 한 줄 노트만 남기고 실행한다. `plan-review` Gate 5도 그 조합을 FAIL 처리하지 않는다.
- **human gate는 `/flow-review` 내부에 한정** — 승인·보류·headless 실패 세 경로 모두 토픽을 `review:in-progress`로 남기고, 그 상태가 `/flow-docs`의 진입 게이트다. 따라서 보류 직후에도 하류 진행이 기술적으로 가능하며 이 gate는 advisory 성격이다. 하류 강제는 새 lifecycle 상태 또는 승인 마커 영속을 요구한다.
- **lock 재사용이 판정 시점 HEAD와 미바인딩** — `lock: locked` 재개 행은 lock이 계산된 commit과 현재 HEAD가 같은지 검증하지 않는다. stage 2 도중 쌓인 review-fix commit이 구조 이탈을 들여오면 stage 1을 다시 통과하지 않은 채 lock된 것으로 취급된다.
- **rubric 이중 정의** — 8문항 rubric과 lock 판정 규칙이 `flow-review/SKILL.md`와 `architect.md` 양쪽에 존재한다. 두 사본의 drift는 `scripts/risk-routing-assertions.test.js`의 `deepStrictEqual` 비교가 차단한다.
- **`flow-verify` 무변경** — `wf-verification`에 위임할 뿐이고 `scaffold` 완료 판정이 재사용하는 정적 검사 게이트는 이미 그 스킬에 있다.
