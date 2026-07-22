---
version: 7
---

# tack 종합 정리 (Handoff Summary)

**목적**: 새 tack 저장소 구현의 **spec 입력**. 현 harness를 기반으로 확정한 방향·용어·아키텍처 결정을 한 문서로 종합한다. 세부는 `docs/dossier/`의 개별 문서·`research/` 참조.

**범위**: 방향·용어·아키텍처 결정만. 구현·코드·정식 flow spec/plan은 새 저장소에서 진행한다.

---

## 1. tack이란

현 harness를 기반으로 더 나은 구조·배포 시스템을 갖춰 새로 구현하는 **개발 하네스 제품**. Claude Code + Codex를 동시에 구동하는 이중-도구 시스템.

---

## 2. 확정 결정 (Decision Ledger)

### 2.1 용어 (`glossary.md`)

**제품 정체성** — "harness"는 일반 범주어로 강등, 고유명은 tack.

| 용어 | 의미 |
|------|------|
| `tack` | 제품/시스템 |
| `tack repo` | tack template을 개발하는 저장소 |
| `target project` | tack을 도입한 프로젝트 |
| `tack template` | Copier 템플릿 = 배포 원천 |
| `tack instance` | target에 생성된 tack 파일(`copier copy`/`update` 산출) |
| `harness` | 이런 부류의 도구 일반 범주(고유명 아님) |

**작업 계층** — 표준 Epic > Story > Task > Sub-task, tier별 매체 상이.

| tier | 크기 | 매체 | 기존 대응 |
|------|------|------|-----------|
| `epic` | 여러 PR | GitHub 이슈(딜리버러블 앵커) | (신규) |
| `story` | 1 PR | GitHub 이슈(앵커) + spec·implementation-plan **문서 생성 단위**(라이프사이클 부착) | 기존 topic |

> epic·story가 GitHub 이슈인 것은 확정(PR·sub-issue 링크). 타입 구분은 **이슈 라벨**(`type:epic`·`type:story`)로 표현하고 native 커스텀 Issue Types는 채택하지 않는다(개인·조직 repo 양쪽 균일 동작). 계층은 sub-issues. Projects 폐기로 상태는 Mongo 소유, 이슈는 앵커·계층만.
| `task` | ≈1 commit | implementation-plan 문서 내부 항목 | 기존 Story |
| `subtask` | 체크리스트 스텝 | task 내부 `[ ]` | 기존 Task |

> **Type·에이전트·진행 부착 계층 확정** (glossary §1.1): 작업 Type(실행 전략 tdd/prompt/config/infra/refactor)·에이전트 사이클은 **`task`**(1 commit·단일 Type)에 붙고, 다중-Type 컨테이너는 **`story`**(1 PR), 진행 국면은 **`subtask`**다. 근거 = 완료 계획 254 Story 전수 단일-Type 실측. Type을 subtask로 내리지 않는다(TDD 사이클 분할 회피); per-unit 실행이 필요하면 task를 잘게 분해한다.

**gate (5분류)** — 진행 제어 `-gate`(`state-gate`·`availability-gate`·`approval-gate`) / 통과 대상(`verify-check`·`quality-criterion`).

**진입점** — `command`=슬래시 인터페이스, `skill`=구현. 진입점은 **user-invocable 스킬 전용**(command file 0).

**상태** — 산문에서 `phase`(단계)·`status`(진행상태)·`state`(쌍) 고정.

### 2.2 세션 운영 (`session-model.md`)

메인(hub) + 워크트리 세션 분리, **경계 = `spec:confirmed`**.
- **hub**: 스펙 작성·확정, epic·story 이슈 생성, 워크트리 provision/teardown.
- **워크트리**: plan → impl → review → verify → docs → pr → done.
- 근거: plan은 산출물만 doc이고 **내용은 코드-바운드**(실파일 분해)라 실제 작업 경로에서 작성. spec은 cross-story 스코핑(hub), plan은 intra-story(worktree).

### 2.3 컨텍스트 저장소 (`context-store.md`)

장치 간 공유 = remote-context-store 스펙(Track 1) 흡수. **3계층 역할 배분**:

| 계층 | 역할 |
|------|------|
| GitHub 이슈 | story·epic **딜리버러블 앵커**(PR·sub-issue 링크). 워크플로우 상태 안 맡음 |
| 로컬 per-worktree | `phase:status` **SoT**(hot path, blocker-2 격리) |
| **Mongo Atlas** | shared registry(phase 스냅샷+소유권+활동) + lease(G5) + 충돌 인덱스(G4) + config. **대시보드(G2) 원천** |

- **대시보드 = CLI-first**(`list_topics`) over Mongo. **GitHub Projects는 최종 폐기**(G2의 lease·활동을 못 담아 두 표면으로 쪼개짐). 대시보드·상태 저장소는 **MongoDB로 최종 확정**한다.
- port/adapter(Mongo 기본·Local 폴백·Postgres 지연, Firebase 미래 어댑터). 오프라인: 로컬 SoT 지속, lease는 Atlas 필요.
- secret = 레포 밖 파일 + env 경로. lease 생애주기 = worktree 생성(획득)/flow-done(반납), heartbeat 없음.
- 원 스펙 G3(worktree 스펙저작)는 session-model(스펙=hub) 충돌로 폐기. topic→story 리네임.

### 2.4 배포 & 업그레이드 (`research/base-packaging.md`·`upgrade-method.md`·`global-vs-perproject.md`·`plugin-provisioning.md`·`cmux-deployment.md`)

- **base는 도구-중립** — tack은 Claude(`.claude`/`CLAUDE.md`)+Codex(`.codex`/`AGENTS.md`)+공유(`.harness`) 이중 소비자. `.harness/contracts/`는 양쪽 동일 버전 필수. **플러그인-only 배제**(계약을 도구 채널로 쪼개면 스큐), **하이브리드 배제**.
- **패키징 = Copier 템플릿(uvx)**, git-tag 단일 버전, `_skip_if_exists`로 init-once(`CLAUDE.md`·`AGENTS.md`·`commit-scopes.md`) 보존.
- **per-project**(global 배제 — 계약 업데이트 타이밍 통제).
- **업그레이드 = `copier update`**: migrations(breaking change), `--vcs-ref` 롤백, `.copier-answers.yml` 커밋 필수(멀티머신 일관). 안전 타이밍 = hub·clean tree·story 사이.
- 참고: Vercel Skills가 다중에이전트 배포 solved임을 검증(단 skill 스코프라 base 대체 불가; 선택적 interop).

### 2.5 진입점 (`research/command-shadowing.md`)

skills-only, command file 0. 플러그인 command shadowing은 platform 버그 영역이나 tack은 **shadowing 안 함**(자기 네임스페이스 진입점이 위임) → 회피.

---

## 3. 남은 것 (새 저장소 spec 단계)

| 항목 | 내용 |
|------|------|
| **phase 목록 확정** | spec/plan/impl/review/docs/pr/done 최종화 → dev-context state 머신 |
| **dogfooding 구조** | tack repo가 tack template을 자기 자신에 적용하는지(내부 구조) |
| **tracked/gitignored 실검증** | Copier smart-update가 gitignored harness 파일에 동작하는지 → tack이 tracked로 이동하는지 |
| **config 위치** | Mongo vs 레포 커밋 |
| **CLI 대시보드 형태** | `list_topics` 출력·필드(phase·소유권·활동·충돌) 설계 |

---

## 4. 핸드오프 체크리스트 (새 repo 첫 단계)

- [ ] 새 저장소 생성, 이 dossier를 spec 입력으로 임포트.
- [ ] 현 harness 구현 참조 셋업 — **gitignored in-tree `reference/harness/` 스냅샷**(서브모듈 아님). 근거: Codex `workspace-write` 샌드박스가 out-of-tree를 못 읽고, in-tree라야 Grep/Glob/subagent/@-멘션이 네이티브 동작. 셋업: `.gitignore`에 `reference/` 추가 · `reference/README.md`에 "읽기전용 harness 원천, 편집·이식 대상 아님" + harness commit SHA 기록 · CLAUDE.md에 동일 읽기전용 지시 · graphify targets 제외 · 리뷰/스캔 스코프를 tack 자기 디렉토리로 한정. 이식 완료 후 디렉토리 삭제.
- [ ] tack v1 spec 작성 — §2 확정 용어·아키텍처를 기준 용어로 사용.
- [ ] Copier 템플릿 골격(`copier.yml`·`_skip_if_exists`·git-tag) 설계.
- [ ] `ContextStore` port/adapter 인터페이스 + Mongo/Local 어댑터 (remote-context-store 스펙 승계).
- [ ] 3계층 상태 배분(로컬 SoT / Mongo registry / GitHub 앵커) 구현 스토리 분해.
- [ ] 이슈 모델 반영 — epic/story = 라벨(`type:epic`·`type:story`) + sub-issue 계층, Projects·native Issue Types 없음, 상태는 Mongo.

---

## 5. 추가 개선 방향 후보 (B1~B6, 연구)

베스트 프랙티스 조사(`research/harness-directions.md`)로 발굴한, dossier 확정 결정 **밖**의 개선 후보. 새 저장소 spec에서 채택 결정. **하나의 story 파이프라인으로 엮임**: explore → EARS delta(B1+B2) → delta 형태가 위험 tier(B4) → tier가 design ceremony(B3)+리뷰 깊이(B4) 라우팅. **B6는 이 라인을 구현·리뷰 층으로 연장**(골격=실행형 design, 2단 게이트 리뷰).

| 후보 | 판정 | 요지 | 문서 |
|------|------|------|------|
| B1 brownfield delta | 🟡 시안 | story spec을 docs/specs/에 대한 ADDED/MODIFIED/REMOVED delta로. MVP=프레이밍, 자동병합 연기 | `delta-model-proposal.md` |
| B2 EARS | 🟡 결합 | delta requirement를 EARS+GIVEN/WHEN/THEN으로 → TDD·verify 추적성 | `delta-model-proposal.md` §8 |
| B3 design 분리 | 🟢 경량 | 기본=plan design 섹션, high-tier만 별도 단계 | `research/risk-tier-b3-b4.md` |
| B4 risk tier + consensus | 🟢 경량 | per-story 위험 tier가 리뷰 깊이 라우팅, 고위험만 패널. delta가 신호. 무거운 기계장치 연기 | `research/risk-tier-b3-b4.md` |
| B5 artifact blackboard | ⚪ 관찰 | plan Story/Task가 이미 근사, 과설계 위험 | `research/harness-directions.md` |
| B6 skeleton-first + 2단 리뷰 | 🟡 시안(실사례 검증) | 골격 task(시그니처+체인 배선+throwing stub, 컴파일=flow 검증) 먼저 → 함수별 task 구현. **flow 리뷰(architect, lock) / unit 리뷰(code-reviewer) 분리**로 리뷰 피로↓. Type@task(§1.1)에 `scaffold` 타입 추가, B3 구체화·흡수, tier로 게이팅. 함수 격리로 per-unit 에이전트·병렬 worktree 열림 | `research/skeleton-first-b6.md` |

**검증**: SpecRoute(최근접 유사물)가 tack의 크로스툴 base 접근을 정확히 확인 — 궤도 정상. B6는 실사례(DisC·architecture-scaffold·**full-review**[Claude+Codex 멀티하네스])로 강하게 검증 — 동기(비대칭 비용·리뷰 피로)까지 verbatim 일치.

---

## 6. 자료 인덱스 (`docs/dossier/`)

- `README.md` — dossier 커버·목적
- `handoff.md` — (이 문서) 종합
- `glossary.md` — 용어(전 항목 확정) + Open Questions
- `session-model.md` — 세션 운영 모델
- `context-store.md` — 컨텍스트 저장소(Projects 폐기·MongoDB 최종 확정)
- `delta-model-proposal.md` — B1 delta + B2 EARS 시안(🟡 제안)
- `research/` — plugin-provisioning · base-packaging · cmux-deployment · global-vs-perproject · upgrade-method · command-shadowing · harness-directions · risk-tier-b3-b4 · **skeleton-first-b6**(B6 시안·실사례 검증) · **github-issue-mechanism(⚠ 부분 폐기 — OQ2·OQ3 최종 결정: 라벨+sub-issue·앵커만 유효, native Issue Types·Projects 미채택)**
