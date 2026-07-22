---
version: 6
---

# tack 용어집 (Glossary)

**tack** — 현재 harness 저장소를 기반으로 더 나은 구조·배포 시스템을 갖춰 새로 구현하는 개발 하네스 제품. 이 문서는 tack 설계에 앞서 핵심 용어를 확정하고, 현재 harness에서 발견된 모호성·불일치를 tack에서 어떻게 정리할지 기록한다.

**상태 표기**: `🔴 미결정` — 표준 용어 선정 필요 / `🟡 후보` — 제안됨, 확정 대기 / `🟢 확정` — 표준 확정

## 분류 기준

모호성을 두 종류로 나눈다. 고치는 방법이 다르다.

- **A. 한 용어 → 여러 의미** (진짜 모호성): 의미를 분리하거나 한쪽을 개명한다.
- **B. 여러 용어 → 한 의미** (불일치): 하나로 통일한다.

---

## 0. 제품 정체성 (Product Identity) 🟢 확정

`tack`이라는 고유명 도입으로, 현재 harness에서 한 단어가 4중으로 과부하되던 A1 문제가 근본 해소된다. **"harness"는 고유명 자리에서 은퇴하고 일반 범주어로만 남으며, 제품명은 `tack`으로 고정**한다.

| 표준 용어 | 의미 | 규칙 |
|-----------|------|------|
| `tack` | 제품/시스템 그 자체 (고유명) | 이 의미에만 사용. 저장소·디렉토리·복사본을 `tack`이라 부르지 않는다. |
| `tack repo` | tack을 개발하는 저장소 | 개발 원천 저장소를 가리킬 때. |
| `target project` | tack을 도입한 프로젝트 | 배포 대상. |
| `harness` | 이런 부류의 개발 도구 일반 범주 | 고유명 아님. tack을 "a harness"라 부를 순 있으나 "the harness"로 특정하지 않는다. |

**부수 확정:**
- 현재의 `.harness/` 디렉토리처럼 제품명과 충돌하는 디렉토리명을 tack에서는 두지 않는다. 공유 규칙 영역은 산문에서 "공유 인프라(shared infra)"로 지칭.
- 배포 동작은 동사 `deploy`.

**층 이름 🟢 확정** (OQ1 per-project Copier에서 도출):

| 표준 용어 | 의미 |
|-----------|------|
| `tack template` | Copier 템플릿 = 배포 원천. tack repo가 저작·버전(git tag)한다. |
| `tack instance` | target project에 `copier copy`로 생성되고 `copier update`로 갱신되는 tack 파일 집합(`.claude`·`.codex`·`.harness`·CLAUDE.md·AGENTS.md). |

- 현 harness의 `src/ → 루트` self-sync 층("원천 vs 실행본")은 **Copier 하에서 소멸** — 자기 복사 동기화가 없고 `tack template → tack instance` 단일 방향만 남는다. "처음부터 새로 구현"이 이 우발적 층을 제거한 결과다.
- tack repo가 tack을 dogfood하는 내부 구조(템플릿을 자기 자신에 적용하는지)는 §0 용어가 아니라 **새 저장소의 구조 결정** — spec에서 다룬다.

---

## 1. 작업 계층 (Work Hierarchy) — Epic > Story > Task > Sub-task 🟢 확정

tack은 표준 **Epic > Story > Task > Sub-task** 4계층을 채택한다. 관리 매체가 tier마다 다르다 — 상위 2계층은 **GitHub 이슈**, 하위 2계층은 **implementation-plan 문서 내부** 단위다.

| tier | 이름 | 크기 | 관리 매체 | 기존 harness 대응 |
|------|------|------|-----------|-------------------|
| 최상위 | `epic` | 여러 PR | **GitHub 이슈** (story들을 묶는 umbrella) | *(신규)* |
| 라이프사이클 | `story` | 1 PR | **GitHub 이슈** + `spec`·`implementation-plan` **문서 생성 단위** | 기존 `topic` |
| 작업 | `task` | ≈1 commit | implementation-plan **문서 내부** 항목 | 기존 `Story` |
| 스텝 | `subtask` | 체크리스트 스텝 | task 내부 `[ ]` 체크리스트 | 기존 `Task` |

**핵심 정합**: 기존 `topic` 단위로 만들던 `spec`·`implementation-plan`이 그대로 `story` 단위가 된다 — 문서 생성 로직은 이름만 바뀌고 구조는 유지된다. flow 사이클(spec→plan→impl→…→PR)이 **story 하나**에 부착되고, `epic`은 관련 story들을 묶는 기획/그룹 umbrella다 (전용 spec/plan 문서 없이 GitHub 이슈 설명으로 관리).

- **관계**: `epic 1 : N story`, `story 1 : N task`, `task 1 : N subtask`.
- **GitHub 이슈 = epic, story** (2개 타입). `task`·`subtask`는 이슈가 아니라 문서 단위 — story당 이슈 폭증을 피하고, GitHub의 `[ ]` task-list 진행률 렌더를 활용.
- **라이프사이클 부착 지점**: `phase:status`(spec→plan→impl→review→docs→pr→done)는 **story**에 붙는다 (기존 topic → story). 저장소 위치는 OQ3.
- **`task` vs "Task 도구" 구분**: `task`는 tack의 작업 단위(문서 항목)이고, **"Task 도구"**는 그 task/subtask를 세션 중 표면화하는 Claude Code 메커니즘이다. 산문에서 Claude 메커니즘은 항상 "Task 도구"로 수식한다 — 충돌이 아니라 정합.

### 1.1 Type·에이전트·진행의 부착 계층 🟢 확정

작업 Type(실행 전략)·에이전트 사이클·진행 관리가 각각 어느 tier에 붙는지 확정한다.

| 개념 | 부착 tier | 규칙 |
|------|-----------|------|
| **Type**(실행 전략: tdd/prompt/config/infra/refactor) | **`task`** (≈1 commit) | 한 commit = 한 behavior = 한 전략 = 한 에이전트 사이클. 기존 harness "Story Type"을 그대로 tack `task` 필드로 승계. task 하나는 단일 Type. |
| **다중-Type 컨테이너** | **`story`** (1 PR) | 한 story는 서로 다른 Type의 task 여러 개를 묶는다(예: config task + tdd task + prompt task). "하나의 단위가 여러 타입 작업을 포함해야 한다"는 요구는 story 레벨에서 충족된다. |
| **에이전트 경계·진행 국면** | **`subtask`** | subtask는 한 task의 에이전트 사이클 안에서 test/impl 등 **국면(phase)**을 이룬다. Type·에이전트 경계가 아니다. 진행 관리(Task 도구 갱신)는 subtask 단위로 이뤄지되 Type 부착·에이전트 배정과 직교한다. |

**근거(완료 계획 실측, 2026-07-22)**: muhan 132 + marketing-strategist 122 = **254 Story 전수에서 예외 없이 단일-Type**. tdd task 내부 subtask는 impl+test가 하나의 RED-GREEN 사이클을 이뤄(예: `account-character` Story 1의 T1.2 스키마 변경 ↔ T1.4 테스트 갱신 강결합), 국면 분할 시 TDD 피드백 루프·커밋 원자성이 붕괴한다. 다중-Type은 항상 topic(=tack `story`) 레벨에서 발생한다.

**함의**:
- Type을 subtask로 내리지 않는다 — 전략 사이클 분할을 회피한다.
- per-unit 에이전트가 필요하면 **task를 더 잘게 분해**한다(subtask 분할 아님).
- config/infra/refactor 전용 전략 에이전트는 선택적 개선이다(현 harness에서 미실행이나 병목 아님) — base 결정과 분리한다.

---

## A. 한 용어가 여러 의미를 가짐 (carry-over)

현재 harness에서 발견됐고 tack에서도 정리해야 할 항목.

### A2. `gate` 🟢 확정 — 5가지 의미 (grep 전수 확인)

grep 전수 확인 결과 4개가 아니라 **5개** 의미로 갈린다 (기존 "상태 체크 guard"가 자동 상태 조건 + 사용자 승인 대기로 분리). 2개 부류로 묶어 정리한다.

**부류 I — go/no-go 체크포인트** (진행/정지 제어). `-gate` 접미사 유지, 접두사로 구분:

| 개념 | 무엇을 검사 | 해소 | 제안어 | 출처 |
|------|-----------|------|--------|------|
| 진입 상태 조건 | `phase:status` precondition | 자동 block/proceed | `state-gate` | "Gate: topic must be plan:confirmed" (전 flow-*) |
| 외부 도구 가용성 | 도구 available? | skip/fallback | `availability-gate` | adapter-codex-review·flow-plan (이미 "Availability Gate") |
| 사용자 승인 지점 | 사람의 결정 | 사람 입력 대기 | `approval-gate` | 미체크 Task 게이트·human gate (flow-impl) |

**부류 II — must-pass 테스트 항목** (통과 대상). "gate"라 부르지 않음:

| 개념 | 무엇을 검사 | 해소 | 제안어 | 출처 |
|------|-----------|------|--------|------|
| 검증 시퀀스 | build/lint/test 기계 통과 | pass/fail | `verify-check` | /flow-verify |
| 리뷰 품질 기준 | rubric 판정 | READY 판정 | `quality-criterion` | spec/plan-review 8개 |

**적용 규칙**: `gate`는 부류 I(진행 제어)에만, 반드시 접두사와 함께 쓴다. 부류 II는 `check`/`criterion`으로 부른다. → "gate"가 단일 의미(go/no-go 지점)로 수렴한다.

### A3. `command` vs `skill` (사용자 진입점) 🟢 확정

현 harness는 진입점을 이원화한다 — (a) command 파일 `.claude/commands/*.md`(harness:audit·codex:setup·add-language-rules), (b) `user-invocable: true` 스킬(flow-*). 둘 다 `/foo`로 보여 "커맨드"가 양쪽을 지칭 → 모호. tack은 다음으로 확정한다.

| 용어 | 의미 |
|------|------|
| `skill` | 모든 능력/로직 구현 단위 (tier 체계). 진입점 로직도 스킬에 둔다. |
| `command` | 사용자가 타이핑하는 `/foo` **인터페이스(surface)**. 독립 아티팩트가 아니라 `user-invocable` 스킬이 노출하는 슬래시 핸들. |
| `command file` | (명시 지칭 전용) `.claude/commands/*.md` 파일 메커니즘. 워크플로우 로직에는 쓰지 않는다. |

**구조 원칙**: `command`는 user-invocable 스킬의 **투영(projection)**이지 병렬 아티팩트 타입이 아니다 → 진입점 = user-invocable 스킬로 단일화. (현 component-boundaries의 "`user-invocable: true` = 슬래시 노출 단일 진실 원천"을 tack에서 구조 원칙으로 승격.) 기존 command 파일(audit·setup·add-language-rules)은 tack에서 user-invocable 스킬로 이전.

### A4. `상태` (state / phase / status) 🟢 확정 — 산문 규칙

코드는 명확(`phase` + `status` = `state`)하나 한국어 산문의 "상태"가 셋 다에 매핑됨. **규칙**: 산문에서 `phase`=단계, `status`=진행상태, `state`=`phase:status` 쌍으로 고정하고 "상태"를 세 개념 전반에 남발하지 않는다. (§1에 따라 이 라이프사이클은 `story`에 부착된다.)

---

## B. 여러 용어가 한 의미 (carry-over)

### B1. 기존 `Story`/`Task` → §1로 해소 (Section B 성격 아님)

이 항목은 **불일치(여러 용어→한 의미)가 아니라 별개 계층**이었다(Story ≠ Task). 따라서 Section B에 속하지 않으며 §1에서 해소된다 — 기존 `Story`(커밋)→tack `task`, 기존 `Task`(스텝)→tack `subtask`. 잔여 실제 결함은 `git-workflow.md`의 "Commit per Task"(사실 "커밋 단위" 의미)뿐 → tack `task`(≈1 commit)로 자연 정합. (Claude "Task 도구" 구분은 §1 규칙.)

### B2. `<name>` vs `<topic>` 🟢 확정 — 둘 다 폐기, `story`로 대체

기존에 라이프사이클 단위를 `topic`/`<name>` 혼용으로 불렀다. tack에서 **라이프사이클 단위는 `story`**(§1)이므로 `topic`·`<name>` 둘 다 폐기하고 `story`로 통일한다. `dev-context`의 `topic`, `flow-topic`, `--topic` 등은 tack 재구현 시 `story` 기준으로 명명 (from-scratch, churn 비구속).

---

## 제외한 후보 (모호하지 않음)

- **`review`** 계열(spec-review·plan-review·code-review·adversarial-review): 복합어로 각각 명확.
- **`confirmed`**: 일관됨.

---

## Open Questions (설계 단계)

- **OQ1. 배포 시스템 모델** 🟢 **확정 — per-project Copier**:
  - **배포 범위 = per-project** (global 배제). 근거: 프로젝트별 tack 버전 핀 + 계약 업데이트 타이밍 통제. global은 "global 계약↔프로젝트 in-flight 산출물" 불일치를 미룰 수 없어 배제 (`research/global-vs-perproject.md`).
  - **패키징 = Copier 템플릿(uvx)**, git-tag 단일 버전, `_skip_if_exists`로 init-once 구분.
  - 이하는 이 결정에 이른 근거 기록:
  - **확정 제약 — base는 도구-중립**: tack은 고정된 별개 관례를 가진 **두-도구 제품**(Claude=`.claude`/`CLAUDE.md`, Codex=`.codex`/`AGENTS.md`, `.harness`=공유)이다. 어느 쪽도 상대의 플러그인을 소비하지 못하고, 특히 `.harness/contracts/`(Claude↔Codex 교환 명세)는 **양쪽이 동일 버전을 읽어야** 한다. 도구 전용 채널(Claude 플러그인)로 계약을 실으면 version skew → tack의 핵심(Claude↔Codex 조율)이 깨진다. 따라서 **배포 base는 반드시 도구-중립. 플러그인은 최대 additive 편의 계층, 결코 base 아님. 플러그인-only는 배제.**
  - **배제 — 하이브리드**(Claude=플러그인 + Codex/공유=별도 채널): 계약을 두 버전 스트림으로 쪼개는 함정. 채택 안 함.
  - **무효 escape hatch**: "Codex 자체 플러그인" 유무는 구원 못 됨 — 플러그인 둘 버전 정합은 스큐 악화.
  - **패키징 방식 → Copier 유력** (조사 완료, `research/base-packaging.md`): 도구-중립 base를 **Copier 템플릿(uvx 실행)**으로 패키징. 유일하게 UPDATE+로컬화해를 네이티브 제공, git-tag 단일 버전(계약 정합), `_skip_if_exists`가 init-once↔always-resync 구분, uv 정렬. 현 `deploy-harness.sh` skip-if-exists의 엄격한 상위호환. adapter-exa 교차검증 완료(`uvx copier update`·clean-git-repo 제약).
  - **cmux/Vercel Skills 참고** (`research/cmux-deployment.md`): Vercel Skills CLI가 다중에이전트(Claude+Codex) 배포가 solved임을 검증 → 도구-중립 base 방향 확신. 단 SKILL.md 스코프 한정이라 hooks/contracts를 못 실어 base 대체 불가. tack 스킬은 계약과 버전-결합돼 per-project(Copier)가 맞음. **부차 결정(spec)**: tack 스킬을 Vercel Skills 생태계에 선택 발행할지(cmux interop).
  - **~~유효 미지수~~ → 해결됨**: Claude 플러그인이 SessionStart 훅 + 번들 스크립트로 비-Claude 파일(`.codex`·`.harness`·`AGENTS.md`)을 **기술적으로 provision 가능**하나, (a) 비지원 패턴, (b) 업데이트 순서 버그(GH #52218·#60219)가 프로비저너를 stale 버전으로 실행시켜 **버전 스큐를 되살림**. → 신뢰할 base 못 됨, 제약 유지. 상세: `research/plugin-provisioning.md`.
  - 이 결정이 §0에서 유보한 층 이름(원천/실행본, 템플릿/인스턴스)을 도출한다.
- **OQ2. GitHub 이슈 메커니즘** 🟢 **확정 — 라벨로 표현** (조사 `research/github-issue-mechanism.md`): epic/story **타입 구분 = 이슈 라벨**(`type:epic`·`type:story`), **계층 = sub-issues**(GA, 100/8단계 — tack 2단계는 여유). **native 커스텀 Issue Types는 채택하지 않는다** — org 전용이라 개인 repo(smalljiny) 미지원 + org/개인 감지 어댑터 복잡도 + GraphQL 타입 지정 래퍼가 불필요. 라벨은 계정 라우팅(개인 smalljiny / 조직 happymario·aimers) **양쪽에서 균일 동작**한다. 상태는 Mongo가 소유하고(Projects·대시보드 폐기), 이슈는 story·epic **딜리버러블 앵커**(PR·sub-issue 링크)만. 자동화는 `gh issue create`·label·sub-issue 링크로 충분(Projects 필드 GraphQL 래퍼 불요). "Task" 기본 타입은 미사용(tack task는 이슈 아님)이라 충돌 없음.
- **OQ3. 워크플로우 저장소** 🟢 **확정 — MongoDB shared registry + CLI 대시보드** (`context-store.md`): phase:status SoT는 **로컬 per-worktree**, 공유·대시보드(G2)는 **MongoDB shared registry**(phase 스냅샷 + lease + 소유권·활동 + 충돌), 대시보드는 **CLI-first**(`list_topics`). **GitHub Projects=대시보드는 최종 폐기** — G2가 요구하는 lease·활동을 Projects가 못 담아 두 표면으로 쪼개짐. GitHub 이슈는 story·epic 딜리버러블 앵커(PR·sub-issue 링크)만. 대시보드·상태 저장소는 **MongoDB로 최종 확정**(Projects는 채택하지 않는 폐기된 안).
- **OQ4. command file 잔존 여부** 🟢 **확정 — skills-only, command file 0** (조사 완료, `research/command-shadowing.md`): 스킬이 주 메커니즘(같은 이름 command보다 우선)이라 command file 불필요. 플러그인 command shadowing은 platform 버그 영역(#44871·#62500·#14945)이나, tack은 **shadowing을 안 함** — 플러그인 명령 이름을 하이재킹하지 않고 자기 네임스페이스 진입점이 하부 도구를 위임 호출(현 `codex:setup` shadow를 회피). 버그 영역을 애초에 안 밟음.

---

## 진행 현황

| 항목 | 상태 |
|------|------|
| §0 제품 정체성 (tack / tack repo / target project) | 🟢 확정 |
| §1 작업 계층 (epic / story / task / subtask) | 🟢 확정 |
| §1.1 Type·에이전트·진행 부착 계층 (Type=task / 컨테이너=story / 국면=subtask) | 🟢 확정 |
| A2 `gate` (5개 구분어) | 🟢 확정 |
| B1 기존 Story/Task → tack task/subtask 재명명 | 🟢 확정 |
| B2 `name`/`topic` → `story`로 대체 | 🟢 확정 |
| A3 `command`(인터페이스) vs `skill`(구현) | 🟢 확정 |
| A4 `상태` (phase/status/state) | 🟢 확정 |
| OQ1 배포·업그레이드 (per-project Copier) | 🟢 확정 |
| OQ2 GitHub 이슈 (story·epic=이슈 라벨 + sub-issue 앵커, native Issue Types 미채택) | 🟢 확정 |
| OQ4 command file (skills-only, shadowing 회피) | 🟢 확정 |
| OQ3 워크플로우 저장소 (MongoDB shared registry + CLI 대시보드, Projects 폐기) | 🟢 확정 |

**dossier 방향 결정 완료** — 용어 전부 + OQ1·OQ2·OQ3·OQ4 **전 항목 확정**. OQ2 이슈 표현은 라벨(native Issue Types 미채택), OQ3 저장소는 MongoDB로 최종 확정(GitHub Projects 폐기).

## 다음 작업

1. 확정 용어·방향을 새 tack 저장소 초기 spec의 기준으로 핸드오프 (label 명명 스킴 세부는 spec 구현 단계)
