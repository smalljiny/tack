---
version: 1
---

# 자료: 개발용 하네스 방향성·베스트 프랙티스 (추가 개선 방향)

**목적**: dossier가 이미 정한 것(용어·계층·워크트리·저장소·Copier·skills) **밖에서** tack이 취할 추가 개선 방향을, 2025–2026 agentic 하네스 베스트 프랙티스·유사 프로젝트 조사로 발굴.

**출처**: adapter-exa `/answer` ×4 (Harness Engineering 가이드·Spec Kit·SpecRoute·OpenSpec·Kiro·CodeConductor·EARS), 2026-07-22.

## A. tack이 이미 정렬된 것 (검증 — 안심 근거)

- **"Harness Engineering" 명제** — 프롬프트 품질보다 하드 인프라 경계로 에이전트를 제약. tack 전체 논지와 일치.
- **Context engineering** — lean 규칙 + loadable skills + 격리된 subagent 창. tack의 skills·서브에이전트·규칙 구조와 일치.
- **결정론적 훅**(Pre/PostToolUse로 lint·format·security 기계 강제). tack 훅과 일치.
- **worktree 병렬 격리**(Spec Kitty·Conductor가 git worktree 자동화). tack `flow-worktree`가 이미 채택.
- **self-improvement 메모리**(LEARNING.md/AGENTS.md). tack memory·`harness:learn`과 일치.
- **⭐ vendor-neutral 크로스툴 base — SpecRoute가 tack 접근을 정확히 검증**: "vendor convergence는 **파일이 아니라 capability 레벨**에서 일어난다 — lifecycle·hooks·agent에 **통합 계약**을 두고 도구별 edge config만 적응." tack의 `.harness/contracts` 공유 + `.claude`/`.codex` 도구별 + port/adapter 철학과 **동일**. tack이 궤도를 벗어나지 않았다는 강한 신호.

## B. 추가 개선 방향 (dossier에 없던 gap) — 우선순위순

### B1. brownfield delta 변경 관리 (OpenSpec) — 🔴 HIGH
tack 흐름은 **greenfield 지향**(새 기능 spec). 그러나 target project는 대부분 **brownfield**(기존 코드)이고, story는 흔히 **기존 코드의 변경**이다. OpenSpec 모델:
- 레거시 전체를 문서화하지 않고 **변경되는 slice만** spec.
- 변경을 self-contained 폴더의 **delta**(`ADDED`/`MODIFIED`/`REMOVED`)로 포착.
- archive 시 delta를 중앙 source of truth로 병합 → 문서가 stale 없이 성장.
→ **tack 제안**: story spec을 "새 기능"만이 아니라 **delta 변경**으로도 표현. `flow-spec`/plan 산출물에 delta 포맷 도입 검토. tack이 실코드 프로젝트에 배포되는 만큼 실효성 큼.

### B2. EARS 표기 acceptance criteria (Kiro·Spec Kit) — 🟠 MED-HIGH
EARS(Easy Approach to Requirements Syntax): `[While <전제>], [When|If|Where <트리거>], the <system> shall <응답>` 구조 문법. 모호성 제거 + **AI가 파싱·검증 가능**. → tack spec은 brainstorming 기반(freeform). EARS를 **acceptance criteria/Completion Criteria에 도입**하면 spec-review·plan `quality-criterion` 게이트가 날카로워지고 자동 검증 추적성이 생김. 저비용(템플릿 규칙).

### B3. requirements/design/tasks 분리 (Kiro·SpecRoute) — 🟡 MED
Kiro·SpecRoute는 feature spec을 **requirements → design → tasks** 3단으로 분리. tack은 spec → implementation-plan(design+tasks 번들). 큰 story엔 별도 **design 아티팩트**가 도움될 수 있음(tack엔 architect 에이전트는 있으나 design 산출물 없음). 단 단순성과 저울질 — 남용 주의.

### B4. risk-based routing + council/consensus (CodeConductor) — 🟡 MED
CodeConductor: **versioned agent contracts**, 위험도 기반 라우팅, **council-consensus**(다중 에이전트 합의), human-in-the-loop 게이트. → tack은 고정 리뷰어 + `adversarial-review`(부분적). 고위험 변경에 **risk-tier로 리뷰 깊이·합의 패널**을 라우팅하는 형식화 검토.

### B5. 형식 task-envelope / artifact blackboard — ⚪ LOW
오케스트레이터가 `/tasks`에 task envelope(goal·criteria·constraints) 기록 → 무상태 subagent가 `/artifacts` 출력 → evaluator 검수. tack의 plan Story/Task + dev-context가 이미 근사. 완전 형식화는 과설계 위험 — 관찰만.

## C. 스터디 대상 (경쟁·참고 프로젝트)

| 프로젝트 | 배울 점 |
|----------|---------|
| **SpecRoute** (Enovatr-Labs) | 최근접 유사물. 아티팩트 taxonomy(PRD·spec[req/design/tasks]·agents·skills·commands·hooks·prompts·workflows·rules), capability-레벨 계약. tack 검증 + taxonomy 차용 |
| **GitHub Spec Kit** | 최성숙 SDD CLI. `/speckit.*` 슬래시, 30+ 에이전트, phase-based. greenfield |
| **OpenSpec** | brownfield delta 모델(B1 원천), cross-repo store |
| **Kiro** (AWS) | req/design/tasks + EARS + steering files + event-driven hooks |

## 정리

tack의 핵심 아키텍처는 SpecRoute가 검증(궤도 정상). 추가 방향은 **B1(brownfield delta)이 최우선** — 실코드 배포 대상에 직결. B2(EARS)는 저비용 고효율. B3·B4는 선택적 형식화. 이들은 **새 저장소 spec 단계에서 채택 여부 결정**할 후보이며, 지금 dossier 확정 결정을 바꾸지 않는다.
