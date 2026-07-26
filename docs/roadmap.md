---
version: 3
status: draft
---

# tack 구현 로드맵 (Epic/Story Roadmap)

**목적**: `docs/dossier/`의 확정 방향을 tack 저장소의 **epic > story 분해**로 옮긴다. 각 story는 1 PR 크기이며, 그 안의 task(≈1 commit)·subtask 분해는 **세션 모델상 워크트리 plan 단계**에서 코드-바운드로 작성한다(이 문서에 task 체크리스트를 넣지 않는 이유 — `session-model.md`).

**고도**: 이 문서는 spec 입력(dossier)과 워크트리 plan 사이의 **로드맵 계층**이다. "무엇을 어떤 순서로"에 집중하고, "어느 파일을 어떻게"는 각 story의 spec/plan이 담당한다.

**tack의 성격 — MVP 사냥이 아니다** 🟢: 레퍼런스(yoshi-saddle)는 **이미 완전 동작하는·실전 검증된 하네스**다. 개념 증명(=MVP의 의미)은 이미 존재한다. 따라서 tack은 "최소 동작물"을 찾는 프로젝트가 **아니라**, 검증된 설계를 **더 나은 구조·배포로 재구현하는 v2**다. 함의:
- **목표 스코프 = 레퍼런스 패리티 + 검증된 개선(B-라인) + 더 나은 구조·배포.** 축소가 아니라 완성.
- **phasing은 "가치 분류"가 아니라 "의존 순서"다.** 무엇을 뺄까가 아니라, 무엇이 무엇 위에 서는가.
- **연기는 두 종류뿐이다** — (a) 엔지니어링상 비싼 꼬리·리스크로 연구가 독립적으로 "먼저 만들지 마라" 한 것(유지), (b) ~~MVP 최소주의~~(폐기 — 근거 소멸). 이 문서의 모든 "연기"는 (a)만 남긴다.

**reference 사용 원칙**: `reference/yoshi-saddle/`는 **salvage 인벤토리**(재사용 가능한 로직 원천)이지 구조 템플릿이 아니다. dossier가 명시적으로 폐기한 두 패턴 — `src/ → 루트` self-sync 층(glossary §0, "Copier 하에서 소멸"), `.harness/` 디렉토리명(제품명 충돌로 폐기) — 은 tack 구조로 새어들지 않게 한다. 로드맵의 척추는 dossier 확정 결정이고, reference는 "각 story를 어떤 기존 자산이 충족하는가"만 채운다.

---

## 0. 선결 결정 (Blocking Decisions) — 전부 확정 ✅

dossier가 **의도적으로 열어둔** 항목(D1~D7) + 로드맵 작성 중 표면화된 cross-cutting 결정(D8). 2026-07-22 **전 항목 확정**.

| # | 결정 | 출처 | 매달린 epic |
|---|------|------|-------------|
| ~~D1~~ ✅ | **phase 목록** — 7-phase `spec→plan→impl→review→docs→pr→done`. verify는 독립 phase 아님 = review phase 내 **stateless verify-check**(review→docs 게이트에서 매번 재실행). 리뷰 수정은 `review⇄impl` 루프로 해소. glossary A2(verify-check) 정합 | handoff §3 | E2 |
| ~~D2~~ ✅ | **dogfood — Copier로 자기적용**. template 소스를 `template/` 디렉토리에 두고 `copier copy`/`update`로 tack instance를 repo 루트에 생성 → 하네스 개발자가 자기 하네스를 매일 사용(지속 검증). reference `src/→루트` self-sync를 Copier-native로 대체(소스/인스턴스 분리는 `.copier-answers.yml`이 통제) | handoff §3, glossary §0 | E1 |
| ~~D3~~ ✅ | **tracked** — tack instance 파일을 target/dogfood 양쪽에서 **git tracked로 커밋**. `copier update`의 3-way merge + `.copier-answers.yml` 커밋 필수가 tracked 전제(gitignored면 로컬 수정 보존 실패 위험). reference의 gitignored는 self-sync 재생성 전제였으나 Copier엔 로컬 재생성이 없음. churn은 clean 경계 update로 통제. **실제 copier update 동작 검증은 E1-S4** | handoff §3, upgrade-method | E1 |
| ~~D4~~ ✅ | **config 위치 — 성격별 분리**: 정적 config(dev_impl·auto_review·git·adversarial·docs.sourceFilter·graphify.targets)=**레포 커밋**(D3 정합, 오프라인·버전드·리뷰), 런타임 공유상태(lease·소유권·활동·phase 스냅샷)=**Mongo**(E4), 휘발 캐시(codex TTL)=**로컬** dev-context(재생성) | handoff §3, context-store OQ | E2/E4 |
| ~~D5~~ ✅ | **대시보드 스키마 — G2 코어 셋**: `story`·`epic`·`phase:status`·`owner_session`·`acquired_at`·`last_activity_at`·`conflict`(**MVP=domain 단위** affected-domains 중첩; requirement 단위는 안정 ID 채택 시 — 연기됨). branch/PR 링크는 선택 확장 | handoff §3, context-store OQ | E4 |
| ~~D6~~ ✅ | **B1/B2/B6 — 채택**. B1 delta 프레이밍 + B2 EARS 채택(flow-spec/docs에 통합). B6 skeleton-first **코어**(scaffold task + 2단 리뷰 분리) 채택(flow-impl/review에 통합). 연기(자체 merit): 안정 ID·자동 병합(B1 꼬리), mockist contract-lock·함수별 병렬 worktree(B6 꼬리) | handoff §5 | E8→E3 통합 |
| ~~D7~~ ✅ | **B3/B4 — 경량 채택**. per-story 위험 tier(delta가 신호)가 리뷰 깊이·design ceremony·B6 골격 의례를 라우팅. 무거운 consensus/패널 기계장치는 연기(자체 merit). B6 tier-gate의 짝 | risk-tier-b3-b4 | E8→E3 통합 |
| ~~D8~~ ✅ | **tack 스크립팅 언어 — Python/uv 전면 전환**. dev-context 엔진·훅·store 모두 Python(.venv). 근거: Track 2 방향 실현, from-scratch라 전환 적기(하이브리드를 강요하던 "기존 Node 안 깨기" 제약 소멸), store·Copier·부트스트랩이 이미 Python → 단일 uv 툴체인. dev-context.js는 코드가 아니라 **동작·전환표·config 스키마·89-test를 spec 삼아 port**(테스트 대고 TDD로 de-risk). E2-S2·E4-store·E7-훅의 "직접 승계"는 **동작-승계 + Python port**로 확정 | remote-context-store, OQ1, harness-python-migration | E2·E4·E7 |

> **연기(자체 merit)로 남은 꼬리**: ① 안정 ID + 결정론적 자동 병합(병렬 충돌 회피 기계장치가 무겁고, 프레이밍 검증 후 착수) ② mockist contract-lock(리팩토링 brittle — skeleton-first-b6 §주의) ③ 함수별 병렬 worktree(단일 흐름 검증 후 스케일링). 이들은 MVP와 무관하게 엔지니어링 판단으로 연기.

---

## 1. 에픽 분해

의존 순서로 배열. 각 epic: **목표 · 근거(확정 결정) · story(1 PR 단위) · 승계 자산 · 선결 의존**. B-라인(delta·EARS·skeleton-first·tier)은 채택돼 **E3 flow 스킬에 통합**되며, 통합 지점을 E3 story에 명시하고 상세 근거는 E8에 모은다.

### E1 — 저장소 구조 & Copier substrate 🔩 (최상류)

**목표**: tack template의 도구-중립 base 레이아웃과 Copier 배포·업그레이드 substrate를 세운다. 나머지 전부가 이 구조 안에 산다.

**근거**: OQ1(per-project Copier, 도구-중립 base) · glossary §0(tack template/instance, self-sync 소멸) · D2·D3.

| story | 의도 | 승계/salvage |
|-------|------|--------------|
| E1-S1 | Copier 템플릿 골격 — `copier.yml`, `_skip_if_exists`(CLAUDE.md·AGENTS.md·commit-scopes init-once 보존), git-tag 단일 버전, uvx 실행 | deploy-harness의 skip-if-exists 로직 개념(엄격 상위호환), deploy-manifest selective-cleanup 원리 |
| E1-S2 | 도구-중립 base 레이아웃 — Claude(`.claude`/`CLAUDE.md`)·Codex(`.codex`/`AGENTS.md`)·공유 인프라(이름 미정, `.harness` 아님) 3소비자 트리 | src/ 트리 구조 참조(단 self-sync 층 제거) |
| E1-S3 | ✅ **dogfood 구현** — template 소스를 `template/`에 두고 `copier copy`/`update`로 tack instance를 repo 루트 생성. 소스/인스턴스 분리는 `.copier-answers.yml` 통제 | — (신규, self-sync 대체) |
| E1-S4 | ✅ **tracked 확정** — tack instance 파일 git tracked 커밋. `copier update` 3-way merge + `.copier-answers.yml` 커밋 실검증(clean tree·로컬 수정 보존 확인) | upgrade-method 긴장점 해소(tracked 방향) |
| E1-S5 | 업그레이드 경로 — `copier update`(migrations·`--vcs-ref` 롤백·`.copier-answers.yml` 커밋), 안전 타이밍(hub·clean tree·story 사이) | upgrade-method |

**선결**: 없음(최상류).

---

### E2 — 상태 머신 & dev-context 코어 ⚙️

**목표**: story 라이프사이클의 phase:status 상태 머신 엔진. tack 워크플로우의 심장.

**근거**: glossary §1(story에 라이프사이클 부착, topic→story) · A4(phase/status/state 산문 규칙) · session-model · D1·D4.

| story | 의도 | 승계/salvage |
|-------|------|--------------|
| E2-S1 | ✅ **phase 확정** — 7-phase `spec→plan→impl→review→docs→pr→done` → `VALID_TRANSITIONS` 전환표. verify=review 내 stateless verify-check(review→docs 게이트 재실행), 리뷰 수정=`review⇄impl` 루프 | reference 전환표 직접 승계(verify를 phase로 승격하지 않음 — 검증됨) |
| E2-S2 | dev-context 엔진 **Python port**(D8) — 6 서브커맨드 CLI, config 점경로/타입추론, prototype-pollution 방어, 원자적 쓰기, `topic→story` 리네임 | `dev-context.js`의 동작·전환표·config 스키마·89-test를 spec 삼아 Python(.venv)으로 재구현(테스트 대고 TDD) |
| E2-S3 | ✅ **config 스키마 + 위치** — 정적 config=레포 커밋, 런타임 공유=Mongo(E4), 휘발 캐시=로컬. 네임스페이스 스키마 확정. **위험 tier 필드**(D7) 포함 | `dev-context-config.md` SSOT |
| E2-S4 | 계약 스킬 `meta-dev-context` — read/write CLI 사용 계약 캡슐화 | `meta-dev-context` 스킬 |

**선결**: E1(구조).

---

### E3 — flow 오케스트레이션 파이프라인 & 세션 모델 🔀

**목표**: `spec→plan→impl→review→docs→pr→done` 7-phase 스킬과 hub/worktree 세션 분리. 게이트 강제 + 5-tier 스킬 체계. **채택된 B-라인이 여기 통합된다** — flow-spec은 explore+delta+EARS로(B1/B2), flow-impl/review는 skeleton-first+2단 리뷰로(B6 코어), 위험 tier가 의례를 라우팅(B3/B4). 상세는 E8.

**근거**: glossary §1·A3(command=user-invocable 스킬 투영, command file 0) · OQ4(skills-only, shadowing 회피) · session-model(경계=`spec:confirmed`) · D6/D7.

| story | 의도 | 승계/salvage |
|-------|------|--------------|
| E3-S1 | 5-tier 스킬 분류 체계 — flow/wf/adapter/stack/meta 경계 + `user-invocable` SSOT + skills-only(command file 0, 기존 audit·setup·add-language-rules를 스킬로 이전) | `command-skill-boundary.md`, `component-boundaries.md` |
| E3-S2 | hub 단계 — flow-spec/flow-plan (spec:confirmed 경계, planner, backlog→active). **B1/B2 통합**: flow-spec에 explore 스텝 + ADDED/MODIFIED/REMOVED delta + EARS+scenario. **위험 tier 산정**(delta가 신호) | flow-spec·flow-plan 스킬 + delta-model-proposal |
| E3-S3 | 세션 분리 — flow-worktree + wf-worktree-context (프로비저닝 게이트=spec:confirmed, per-worktree `docs/_local`, dev-context 격리) | flow-worktree·wf-worktree-context 스킬 |
| E3-S4 | worktree 실행 단계 — flow-impl/review/verify (tdd-specialist·code-reviewer, `--all` 배치). **B6 코어 통합**: `scaffold` task type(골격=시그니처+체인+throwing stub) → 함수별 task, **2단 리뷰 분리**(architect flow-review→lock→code-reviewer unit-review). tier로 골격 의례 게이팅(복잡·다함수 story만) | flow-impl/review/verify + wf-tdd/verification + full-review(Claude+Codex, `reference/` 어댑트 후보) |
| E3-S5 | 마무리 단계 — flow-docs/pr/done. **flow-docs = delta 적용(수동/에이전트)**: story delta를 `docs/specs/`에 반영(ADDED 삽입·MODIFIED 교체·REMOVED 삭제, 산문 참조 기반) | flow-docs/pr/done + pr-body 템플릿 |
| E3-S6 | skill-registry capability 발견 — 태그 기반 동적 스킬 로드 | skill-registry 스킬 |

**선결**: E2(dev-context), E1(구조). **소비**: E5(이슈 생성=flow-spec, PR 링크=flow-pr), E6(Codex review 루프=flow-spec/plan). **통합**: E8(B-라인 상세).

---

### E5 — GitHub 이슈 모델 (epic/story 앵커) 🏷️

**목표**: epic·story를 GitHub 이슈로, 타입=라벨, 계층=sub-issue, 딜리버러블 앵커(PR·코드 링크)만. 워크플로우 상태는 안 맡음.

**근거**: OQ2(`type:epic`·`type:story` 라벨, sub-issues, native Issue Types·Projects 미채택) · context-store(이슈=앵커).

| story | 의도 | 승계/salvage |
|-------|------|--------------|
| E5-S1 | 이슈 생성·라벨 — `gh issue create` + `type:epic`/`type:story` 라벨, 계정 라우팅(개인/조직) 균일. **epic 이슈 mint 워크플로우 포함**(hub가 관련 story들을 묶는 umbrella 이슈 생성 — session-model이 hub에 부여한 책임) | github-issue-mechanism |
| E5-S2 | sub-issue 계층 — epic umbrella 아래 story 링크 | github-issue-mechanism |
| E5-S3 | PR-closes-story 링크 — flow-pr가 story 이슈에 PR·sub-issue 연결 | flow-pr |

**선결**: 없음(독립). **피소비**: E3-S2(flow-spec), E3-S5(flow-pr).

---

### E4 — ContextStore + Mongo shared registry + CLI 대시보드 🗄️

**목표**: 3계층 상태 배분(로컬 SoT / Mongo registry / GitHub 앵커) 구현. remote-context-store 스펙 흡수. 장치 간 공유·대시보드·lease. **레퍼런스 패리티의 일부** — 원 하네스가 이미 스펙한 설계이지 "나중에 얹는 옵션"이 아니다.

**근거**: OQ3(MongoDB shared registry + CLI 대시보드, Projects 폐기) · context-store(3계층, port/adapter) · D4·D5.

> **⚠ salvage 출처 주의**: 원 `remote-context-store` 스펙은 `docs/_local/`(gitignored)에 있어 클론 스냅샷엔 없었으나, **`reference/yoshi-saddle/docs/_local/backlog/remote-context-store/spec.md`(+ 리뷰 2개)로 반입 완료**(2026-07-22, 원본 `/Users/mario/Workspace/harness`에서). E4 착수 시 in-tree Read/Grep/@-멘션 가능. `docs/_local/done/`의 48개 완료 토픽·`backlog/harness-python-migration`은 아직 원본 워킹 트리에만 존재(필요 시 추가 반입).

| story | 의도 | 승계/salvage |
|-------|------|--------------|
| E4-S1 | `ContextStore` port/adapter 인터페이스 + Local 어댑터(로컬 per-worktree SoT, hot path). **Python/.venv**(D8) | remote-context-store 스펙 승계(store 모듈 이미 Python) |
| E4-S2 | Mongo Atlas 어댑터 — shared registry(phase 스냅샷 + 소유 세션 + `acquired_at`/`last_activity_at`) | remote-context-store 스펙 |
| E4-S3 | lease(G5) + 충돌 인덱스(G4) — 생애주기(worktree 생성=획득, flow-done=반납), heartbeat 없음. **B1 delta의 affected-domains가 충돌 신호 강화** | remote-context-store 스펙 + delta-model §4 |
| E4-S4 | ✅ **CLI 대시보드** — `list_topics`/`tack dashboard`, G2 코어 필드(`story`·`epic`·`phase:status`·`owner_session`·`acquired_at`·`last_activity_at`·`conflict`) | remote-context-store G2 |
| E4-S5 | 오프라인 지속 + 재연결 복구(G6), secret(레포밖 파일+env), 부트스트랩(uv venv), node-forwarder shim | remote-context-store 스펙 |

**선결**: E2(상태 코어). **관계**: 로컬 SoT(E4-S1)는 flow 파이프라인(E3)의 hot path라 함께 서고, Mongo·lease·대시보드(E4-S2~S5)는 그 위 공유층. lease는 Atlas 필요(오프라인 시 로컬 SoT 지속).

---

### E6 — Codex 이원 통합 & 공유 계약층 🤝

**목표**: Claude↔Codex 동일-버전 공유 계약 + Codex 리뷰 게이트. tack의 핵심(이중-도구 조율).

**근거**: OQ1(도구-중립 base, 공유 계약은 양쪽 동일 버전) · glossary §0(공유 인프라, `.harness` 이름 폐기).

| story | 의도 | 승계/salvage |
|-------|------|--------------|
| E6-S1 | 공유 계약층 — Producer↔Consumer 명세 5개(spec/spec-review/implementation-plan/plan-review/review-report), 공유 rules, 수정 시 양쪽 동시 갱신 규칙. **디렉토리명은 `.harness` 아님** | `.harness/contracts` + rules(이름만 교체) |
| E6-S2 | Codex 리뷰 게이트 — spec-review/plan-review 8-point + adapter-codex-review 래퍼(단일 `codex exec`, 루프 제어는 호출측). **2단 리뷰의 flow-review를 Codex와 겸용**(full-review 정합) | `.codex/skills` + adapter-codex-review |
| E6-S3 | Codex 세션 감지 — detect-and-cache TTL 1시간 캐시, `config.codex.*` 4필드, session-start 훅 위임 | detect-and-cache.js + session-detection |
| E6-S4 | 이원 컨텍스트 — AGENTS.md(인라인 임베드, Codex는 @import 미지원)/CLAUDE.md(@import) 대칭 | AGENTS.md/CLAUDE.md 구조 |

**선결**: E1(base 레이아웃), E2(config). **피소비**: E3(review 루프).

---

### E7 — 훅 · 에이전트 로스터 · 컴포넌트 표준 🪝

**목표**: 자동화 훅, 에이전트 세트, 컴포넌트 작성 표준. 파이프라인을 둘러싼 실행 환경.

**근거**: salvage 인벤토리 A(하네스 제네릭 코어) 항목 7·8·9.

| story | 의도 | 승계/salvage |
|-------|------|--------------|
| E7-S1 | 훅 세트 **Python port**(D8) — session-start(컨텍스트 복원+codex 감지), type-check/prettier(PostToolUse), session-logger, git-push-review, suggest-compact, memory-persist, console-log-audit | `.claude/scripts/hooks/*`의 동작을 Python(.venv)으로 재구현 + hooks.json + settings |
| E7-S2 | 에이전트 로스터 — architect/planner/tdd-specialist/code-reviewer/security-reviewer/refactor-cleaner/build-error-resolver/doc-updater/database-reviewer/prompt-engineer/harness-optimizer + opus/sonnet 모델 배분. **architect=flow-review, code-reviewer=unit-review**(B6 2단) | 11 에이전트 + `performance.md` rationale |
| E7-S3 | 컴포넌트 작성 표준 — prompt-authoring 규칙(모델 버전 리터럴 대응), 모델 버전 갱신(Opus 4.7→현행), meta-skill-creator | prompt-authoring rules + meta-skill-creator |
| E7-S4 | stack-* 유지 정합 — 배포 대상(TS 주력 모노레포) 정합이므로 **삭제 대상 없음**. 현 16개 전량 유지, registry 노출 15개 frontmatter·capabilities 점검(`stack-prompt`은 direct-load 예외), commit-scopes 환경별 설정 명시 | stack-* 16개 전량 유지 / commit-scopes(환경별 설정) |

**선결**: E1, E2. **성격**: 대부분 병렬 가능(파이프라인 뼈대와 독립적으로 이식).

---

### E8 — delta · EARS · skeleton-first · 위험 tier 개선 라인 (채택) 🧪

**목표**: dossier 확정 밖이었으나 **채택 확정된**(D6/D7) 개선 라인. 하나의 story 파이프라인으로 엮임: explore → EARS delta(B1+B2) → delta 형태가 위험 tier(B4) → tier가 design ceremony(B3)+리뷰 깊이+골격 의례(B6) 라우팅. **각 조각은 E3 flow 스킬에 통합**되며(위 E3 참조), 이 epic은 그 상세 설계·근거·연기 경계를 담는다.

**근거**: handoff §5, delta-model-proposal(B1/B2), risk-tier-b3-b4(B3/B4), skeleton-first-b6(B6) — 실사례 검증(DisC·architecture-scaffold·full-review).

| story | 의도 | 통합 지점 |
|-------|------|-----------|
| E8-S1 | B1 delta 프레이밍 — explore 스텝 + ADDED/MODIFIED/REMOVED 구조. greenfield=all-ADDED degenerate delta. **연기: 안정 ID·결정론적 자동 병합**(§merit) — MVP는 산문 참조 + 수동/에이전트 병합 | E3-S2(spec), E3-S5(docs 병합) |
| E8-S2 | B2 EARS — delta requirement를 EARS 5패턴 + GIVEN/WHEN/THEN scenario → Completion Criteria→TDD→verify 추적성 | E3-S2(spec) |
| E8-S3 | B3/B4 위험 tier — per-story tier(delta가 신호)가 리뷰 깊이·design ceremony·골격 의례 라우팅. 기본=plan design 섹션, high-tier=별도 design. **연기: consensus 패널·무거운 기계장치** | E2-S3(tier 필드), E3-S2(산정), E3-S4(라우팅) |
| E8-S4 | B6 skeleton-first 코어 — `scaffold` task type(골격=컴파일/smoke로 flow 검증) + 2단 리뷰 분리(architect lock→code-reviewer unit). **연기: mockist contract-lock(brittle), 함수별 병렬 worktree(스케일링)** | E3-S4(impl/review), E7-S2(에이전트 역할) |

**연기 경계(자체 merit, MVP 무관)**: 안정 ID+자동 병합 · mockist contract-lock · 함수별 병렬 worktree. 각각 §0 하단 표 참조.

**주의**(skeleton-first-b6 §주의): 골격의 "컴파일=flow 자동 검증"은 typed target에서만 자동 — 동적 언어(tack 스크립팅 등)는 smoke 테스트로 대체. 골격 대상 = 함수/이벤트 체인 있는 로직-bearing story(config/데이터-only는 tier로 자연 배제).

---

## 2. 시퀀싱 & 의존 그래프

```
E1 저장소/Copier substrate ─┬─► E2 상태머신 코어 ─┬─► E3 flow 파이프라인 (B-라인 통합)
                            │                     │        ▲   ▲
                            │                     │        │   └─ E5 GitHub 이슈 (독립, E3가 소비)
                            │                     └─► E4 ContextStore/Mongo (로컬 SoT는 E3와 동반)
                            └─► E6 Codex 공유계약 ───────────┘ (E3 review가 소비)
                            └─► E7 훅/에이전트/표준 (대체로 병렬)
                     E8 (B-라인 상세) ── E3에 통합, 별도 후반 epic 아님
```

**권장 착수 순서** (부트스트랩-구동 — self-hosting 임계 경로를 먼저, §2.5):
1. **E1-S2** (도구-중립 레이아웃) + **E1-S1** (Copier 골격) — 스킬이 살 자리 확정.
2. **E2** (상태 머신 Python port) — dev-context·phase·config·계약. flow의 전제.
3. **E3-코어 + E7-S2** (flow-spec/plan/impl/review/docs/pr/done + 에이전트 로스터 + 번들 wf-*) — **여기서 M1 도달 = 자체 하네스 전환점**. B-라인(delta/EARS/skeleton-first) 처음부터 통합(retrofit 회피).
4. **[M1 이후 self-host로 개발]** **E3-S3**(worktree) + **E4-S1**(로컬 SoT) — 세션 격리·hot path.
5. **E5 + E6** (GitHub 이슈 + Codex 이원 통합) — 완전한 flow(이슈 앵커·Codex 리뷰 게이트). M1엔 불필요했던 계층.
6. **E4-S2~S5** (Mongo/lease/대시보드) + **E7-S1/S3/S4** (훅·표준·stack) — 장치 간 공유·편의. 상당수 병렬.
7. **E8 연기 꼬리** — 안정 ID+자동 병합·mockist-lock·병렬 worktree. 각 통합 지점 안정화 뒤.

> **MVP 경계 없음, 그러나 self-hosting 임계점은 있음**: 레퍼런스가 이미 검증된 하네스이므로 tack은 처음부터 패리티+개선을 목표한다(축소 아님). 단 tack이 **자기 자신을 개발**하려면 최소 flow가 서야 하는 부트스트랩 임계점이 존재한다(§2.5). 위 순서는 그 임계점(M1)을 먼저 넘도록 배열했다 — 이전 v2의 "E5/E6 먼저"를 뒤집은 이유.

---

## 2.5 자체 하네스 전환점 (Self-Hosting Threshold) 🐣

**부트스트랩 문제**: tack이 일정 수준 진행 전엔 자기 하네스로 개발할 수 없다(컴파일러 self-hosting과 동형). 따라서 **레퍼런스 하네스로 개발하다 임계점(M1)에서 tack 자체 하네스로 전환**한다.

### M1 — 자체 하네스 사용 가능 임계 집합 (critical path)

tack의 flow가 tack story를 spec→…→done으로 돌리는 데 최소 필요한 것:

| 필요 | 이유 |
|------|------|
| **E1-S2** 도구-중립 레이아웃 | 스킬이 `.claude`/`.codex` 어디 사는지 확정돼야 활성화 |
| **E2 전체** 상태 머신(Python) | dev-context 없으면 phase 게이트·flow 불가 |
| **E3-S1/S2/S4/S5** flow 코어 | spec/plan/impl/review/docs/pr/done + 번들 wf-*(brainstorming·tdd·verification) |
| **E7-S2** 에이전트 로스터 | flow가 planner·tdd-specialist·code-reviewer·security-reviewer를 **호출**하므로 존재 필수 |

### M1에 **불필요** (전환 후 tack 자신으로 개발 = 진짜 dogfood)

| 항목 | 우회 |
|------|------|
| E4 Mongo/lease/대시보드 | 단일 개발자는 로컬 SoT(E4-S1)만 |
| E5 GitHub 이슈 | flow는 이슈 없이 동작(이 로드맵 epic 이슈를 수동 등록한 것처럼) |
| E6 Codex 리뷰 게이트 | `auto_review=off`로 우회 |
| E7-S1/S3/S4 훅·표준·stack | 편의·프로젝트별 |
| E8 delta/EARS/skeleton | 개선 |
| E3-S3 worktree | 초기엔 main hub 직접 작업(곧 필요) |
| E1-S1/S4/S5 Copier update | 배포용 — 첫 전환은 수동 배치로 가능 |

### 전환 3단계

```
Phase 0 (부트스트랩)   : 레퍼런스 하네스를 tack repo에 배포 → 그걸로 M1 임계집합 개발
        │               (tack 자체 스킬은 template/ 소스에서 "일반 파일"로 편집 — 활성 .claude와
        │                충돌 없음; 레퍼런스 flow가 그 파일들을 편집 대상으로 다룰 뿐)
        ▼
M1 = 자체 하네스 전환점 : tack의 .claude/.codex 활성화(첫 전환 수동, 이후 E1-S3 dogfood로 형식화)
        │               + 레퍼런스 undeploy(매니페스트 기반 정확 제거)
        ▼
Phase 1 (self-hosted)  : 나머지 E4·E5·E6·E7·E8을 tack 자신으로 개발 (진짜 dogfood)
```

**검증**: M1 이후 E4~E8을 tack으로 만들 수 있다는 것 자체가 하네스의 인수 테스트다.

**유의**: Phase 0에서 레퍼런스는 Node dev-context, tack은 Python(D8)이라 두 상태 머신이 공존한다 — tack 스킬 개발 중엔 레퍼런스 dev-context가 SoT이고, 전환 시 tack Python dev-context로 SoT 이관. reference 최종 삭제(§3)는 Phase 1 안정화 후.

---

## 3. 리스크 & 열린 결정 요약

- **구조가 상류다** — E1(구조·Copier)이 흔들리면 이후 전 epic이 흔들린다. reference의 self-sync·`.harness` 이름을 무심코 이식하면 dossier가 폐기한 층이 부활한다.
- **B-라인은 채택** — delta·EARS·skeleton-first·tier는 E3에 통합. 연기되는 것은 자체 merit 꼬리(안정 ID+자동 병합·mockist-lock·병렬 worktree)뿐.
- **D8 Python/uv 전면 → E2/E4/E7은 동작-승계 + port** — dev-context.js·훅은 코드 직접 승계가 아니라 동작·89-test를 spec 삼아 Python 재구현(테스트 대고 TDD로 de-risk). 단일 uv 툴체인 확보. skeleton-first "컴파일=flow 검증"은 Python(동적)이라 **smoke 테스트로 대체**(typed target의 자동 컴파일 검증 이점은 tack 자체엔 약함, target project엔 유효).
- **모델 버전 갱신** — 승계하는 prompt-authoring·에이전트 모델 배분의 "Opus 4.7" 등은 tack 시점 현행 모델로 갱신(E7-S3).
- **reference 소멸** — 이식 완료 후 `reference/yoshi-saddle/` 삭제(handoff §4 체크리스트).

---

## 부록 — 확정 결정 ↔ epic 매핑

| 확정 결정 (dossier) | 반영 epic |
|---------------------|-----------|
| OQ1 per-project Copier, 도구-중립 base | E1, E6-S1 |
| glossary §1 epic/story/task/subtask, topic→story | E2, E3, E5 |
| §1.1 Type=task/컨테이너=story/국면=subtask (+ `scaffold` type) | E3(flow-impl), E7(tdd-specialist/architect) |
| A2 gate 5분류 | E3(게이트 강제 명명) |
| A3/OQ4 command=스킬 투영, skills-only | E3-S1 |
| A4 phase/status/state 산문 규칙 | E2 |
| session-model hub/worktree, 경계=spec:confirmed | E3-S2/S3 |
| OQ2 이슈=라벨+sub-issue 앵커 | E5 |
| OQ3 Mongo shared registry + CLI 대시보드 | E4 |
| D1~D5 선결 결정 (phase·dogfood·tracked·config·대시보드) | E1·E2·E4 |
| D6/D7 B1·B2·B6·B3·B4 채택 | E3(통합) · E8(상세) |
| D8 Python/uv 전면 전환 | E2·E4·E7 |
