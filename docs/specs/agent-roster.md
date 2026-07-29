# 에이전트 로스터

> tack이 배포하는 하네스-제네릭 서브에이전트 10개 집합과 3-tier 모델 배분, B6 2단 리뷰 역할 매핑.

## 개요

tack의 flow 파이프라인은 전문 서브에이전트를 호출한다 — `flow-plan`=planner, `flow-impl`=tdd-specialist+code-reviewer, `flow-review`=code-reviewer+security-reviewer(+architect). 따라서 에이전트 로스터는 flow가 호출할 대상이 존재해야 self-host가 가능한 M1 임계 집합이다.

배포 레이아웃은 source/destination 이중 구조를 따른다(base-layout 참조). 에이전트 정의의 **source는 `template/.claude/agents/`**(tack이 편집·추적)이고, Copier가 이를 **destination `.claude/agents/`**(도구 고정 위치)로 렌더한다. 편집은 항상 source에서 수행한다.

로스터는 하네스-제네릭 10개로 확정하며, PostgreSQL 전용 database-reviewer는 로스터 밖(11번째 파일)으로 두고 스택 채우기 단계(E7-S4)로 연기한다.

## 구조 / 스키마

### 로스터 (10개) + 모델 tier

| 에이전트 | 역할 | tier | 자동 활성화 |
|---------|------|------|------------|
| planner | 구현 계획 수립 (task=커밋 분해) | opus | flow-plan |
| tdd-specialist | RED-GREEN-REFACTOR, 80%+ 커버리지 | opus | flow-impl |
| code-reviewer | 코드 품질·보안·유지보수 리뷰. B6 unit-review(함수별) | opus | flow-impl Story 완료마다, flow-review |
| architect | 아키텍처 결정. B6 flow-review(구조·flow 판정 → lock) | opus | 아키텍처 결정 시, flow-review stage 1 (`topicTier == high`) |
| prompt-engineer | 프롬프트 타입 Story의 PROPOSE→EVAL→REFINE | opus | prompt-type Story |
| security-reviewer | 보안 취약점 탐지 | sonnet | flow-review, 커밋 전 |
| refactor-cleaner | 데드 코드 제거·품질 개선 | sonnet | 유지보수·리팩토링 |
| harness-optimizer | 하네스 구성 분석·개선 | sonnet | harness:audit |
| doc-updater | 문서-코드 동기화 | haiku | 구현 완료 후 |
| build-error-resolver | 빌드·타입·린트 오류 해결 | haiku | 빌드 실패 시 |

> database-reviewer(11번째, 로스터 밖)는 sonnet으로 남으며 본 로스터에 포함되지 않는다.

### 프론트매터 필수 필드

각 에이전트 파일은 YAML frontmatter에 5개 필수 필드를 갖는다: `version`(정수)·`name`·`description`·`tools`·`model`. `model`은 별칭(`opus`/`sonnet`/`haiku`)으로 지정하며 버전 핀이 아니다 — 별칭이 현재 모델(Opus 4.8·Sonnet 5·Haiku 4.5)로 자동 해석되어 버전 갱신 부담이 없다.

## 동작

### 3-tier 모델 배분

모델 배분 근거는 `template/.claude/rules/common/performance.md`의 "Harness Agent Model Rationale" 표가 정본이며, 에이전트 frontmatter의 `model:`과 일치한다.

- **opus (추론 중요)**: 계획 분해·TDD 설계·코드/아키텍처 판단·프롬프트 최적화 — 오류 비용이 크고 다단 추론이 필요. planner·tdd-specialist·code-reviewer·architect·prompt-engineer.
- **sonnet (중간)**: 패턴 매칭 + 판단 혼합 — 보안 스캔·리팩토링·하네스 감사. security-reviewer·refactor-cleaner·harness-optimizer.
- **haiku (기계)**: 결정론적·기계적 작업 — 문서 동기화·빌드 오류 수정. Haiku의 속도·비용 우위를 활용하며 품질은 impl 단계 eval로 검증한다. doc-updater·build-error-resolver.

### B6 2단 리뷰 매핑

2단 분리는 **`topicTier == high`인 토픽에서만** 발동한다. `topicTier ∈ {low, normal}`이면 code-reviewer와 security-reviewer가 전체 변경 범위를 병렬로 보는 단일 단계 리뷰이며, stage 구분·lock·human gate가 적용되지 않는다. `topicTier`는 plan의 per-Story `**Risk Tier**` 필드의 최대값이고, 라우팅 소유자는 `template/.claude/skills/wf-risk-routing/SKILL.md`다 (risk-tier-routing 참조).

`high` 토픽에서 flow-review는 2단으로 갈린다: **stage 1 = architect**가 구조·배치·flow 완결성을 8문항 rubric으로 판정하고 **lock**한 뒤, **stage 2 = code-reviewer**가 변경 파일 목록에 스코프를 한정해 함수별 정확성·보안을 검사한다. security-reviewer는 stage 2에서 code-reviewer와 병렬로 돈다. `lock: blocked`(rubric FAIL 1건 이상)면 stage 2를 실행하지 않는다.

이 역할은 각 에이전트의 `description` 필드와 **본문 프로세스 절**(`architect.md`의 stage-1 판정 절, `code-reviewer.md`의 stage-2 unit 스코프 절) 양쪽에 정의된다. lock 판정을 파일에 기록하는 주체는 `/flow-review`이며 architect의 `tools`(`Read, Grep, Glob`)는 확장하지 않는다.

## 제약사항

- **database-reviewer**: PostgreSQL 전용이라 tack(MongoDB) 부적합. 로스터 밖으로 두고 Mongo 재타겟 vs 드롭 결정은 E7-S4로 연기한다. 본 로스터는 이 파일을 편집·삭제·재타겟하지 않는다.
- **에이전트 프롬프트 본문**: frontmatter·description만 소유하며 프롬프트 본문 재작성·모델 버전 리터럴 대응은 E7-S3 소관.
- **flow 스킬의 에이전트 호출 배선**: description의 기존 `/dev:*` 명령 참조는 보존하며 `/flow-*` 재배선은 E3 소관.
- **에이전트 `tools` 배분**: 각 에이전트 `tools` 목록의 tack 도구(Python·Mongo) 조정 여부는 미결로, 레퍼런스 승계값을 유지한다.
- **performance.md 잔여 stale**: 모델 선택 표(Model Selection Strategy)의 stale 모델 리터럴(`Sonnet 4.6`→`Sonnet 5`, `Opus 4.7`→`Opus 4.8`)은 E7-S3에서 해소했다. "Harness Agent Model Rationale" 표의 prompt-engineer 미등재는 E7-S3 범위 밖(E7-S3는 모델 선택 표 리터럴·prompt-authoring de-version만 소관)이라 후속 docs-sync 과제로 남는다.
