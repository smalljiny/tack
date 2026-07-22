---
version: 1
---

# 자료: skeleton-first 구현 + 2단 게이트 리뷰 (B6)

**상태**: 🟡 시안(제안) — spec에서 채택 결정. dossier 확정 결정을 바꾸지 않는다. 단, 아래 실사례로 **강하게 검증됨**.

**조사 대상**: LLM 개발의 **리뷰 피로(비대칭 비용)** 완화 방안 — 목업/스텁으로 함수·이벤트 체인을 먼저 배선하고(골격), 각 함수를 개별 구현하며, **전체 흐름 리뷰와 함수 단위 리뷰를 분리**하는 절차를 에이전트 하네스로 구성할 수 있는가. 실제 적용 사례가 있는가.

**출처**: adapter-exa `/answer` ×3 + `/contents` ×3 (GitHub·에이전트 스킬 레지스트리·arXiv), 2026-07-22.

## 결론 — 이미 활발히 적용되는 2026년 신흥 패턴

사용자가 90년대 구조적/Rx 방식(목업 함수 체인 → 함수별 구현)으로 쓰던 절차는 지금 **Walking Skeleton + London-school(mockist) TDD(GOOS, Freeman & Pryce 2009) + contract-first**로 명명되며, AI 코딩 하네스에 다수 구현돼 있다. 동기도 사용자 설명과 거의 verbatim 일치 — **"AI는 생성·오류 비용 0, 사람은 리뷰 비용 高"(비대칭 비용)**.

## 가장 근접한 사례 3개 (거의 1:1)

| 도구 | 형태 | 메커니즘 | 대응 |
|------|------|----------|------|
| **Design is Code (DisC)** — `mossgreen/design-is-code-plugin` (Claude Code 플러그인) | London-school TDD를 AI 코드생성에 적용 | UML로 오케스트레이션, pure-function leaf는 decision table, 미구현 의존은 **throwing stub**. mockist 테스트가 호출 구조·순서·인자를 고정 → "통과하는 구현은 단 하나" | **목업 체인 → 함수 구현**. 동기=비대칭 비용 |
| **architecture-scaffold** — `petekp/agent-skills` (에이전트 스킬) | "Human Builds the Shell" | 아키텍처 스펙 → **컴파일 가능한 타입-레벨 스켈레톤**을 구현 로직 전에 생성. "스켈레톤이 컴파일되면 아키텍처가 구조적으로 건전" | **시그니처+배선 먼저 → flow 검증(=컴파일+타입체크) → 함수 채움** |
| **full-review** — `kadenn/full-review` (**멀티 하네스: Claude Code + Codex**) | 2단 게이트 리뷰 | ① 아키텍처(맞는 위치? 추상? 애초에 할 일? 이미 있나? 일관? 체인 완결?) 판정 후 **lock** → ② 구현(정확성·silent failure·타입·테스트·보안) | **flow 리뷰 / unit 리뷰 분리**. 동기="line-by-line은 진짜 리뷰의 20%, 아키텍처 지적이 line 홍수에 파묻힘" |

**full-review는 Claude Code + Codex 멀티 하네스 명시 지원** → tack 이중-도구 base와 직접 정합.

## 더 넓은 지형

- **스캐폴드-우선**: Jiti(interface-first + JIT 구현), Jitctx(markdown 스펙 → Go CLI가 skeleton/interface/stub 생성), SecretAgent(`@interface` 스텁 바인딩), GSD architecture 모드.
- **다단 리뷰 분리**: HamReview·Floe·LaReview(PR을 data-flow/아키텍처 슬라이스로 분해), Metareview·LazyLLM·diffray(다단 게이트).
- **London-TDD for agents**: `tdd-london-chicago` 스킬, atdd, mvp-builder, `disciplined-agentic-engineering`, sdd.
- **학술**: arXiv 2509.25297 — Multi-Agent TDD로 요구사항에서 웹앱 자동 생성.

## tack 함의 (B6 시안)

skeleton-first 2단 리뷰를 tack 계층에 얹는다. 확정 결정(Type@task §1.1)에 자연 추가된다.

```
story (1 PR)
├─ task 0: 골격(scaffold)  ── flow 리뷰(architect) → lock
│    시그니처 + 타입/인터페이스 + 호출/이벤트 체인 배선 + throwing stub + flow(컴파일/mockist) 테스트
├─ task 1: 함수 A 구현      ── unit 리뷰(code-reviewer, A로 스코프 한정)
├─ task 2: 함수 B 구현      ── unit 리뷰(B로 스코프 한정)
└─ …                       (인터페이스 뒤 격리 → 병렬 worktree)
```

- **골격 = 컴파일 가능한 타입-레벨 shell** (architecture-scaffold). flow 테스트의 실체 = 컴파일 + 타입체크. TS target에 자연 적합.
- **함수 계약 = mockist 상호작용 테스트** (DisC). unit 리뷰는 "본문이 계약을 만족하나"만 검사. B2(EARS scenario)와 결합.
- **2단 게이트 + 아키텍처 lock** (full-review). tack `flow-review`(architect) → 잠금 → per-function `code-review`. full-review는 이미 Claude+Codex 겸용이라 `reference/` 레퍼런스·어댑트 후보.
- **골격 = 새 task Type**(`scaffold`) — 로직 없으니 TDD 아닌 flow 리뷰로 라우팅.
- **per-unit 에이전트 해소**: 함수가 인터페이스 뒤에서 독립 → 함수별 에이전트·병렬 구현이 원리적으로 타당해짐(앞선 Type@task 논의의 미해결점 해결).

## 기존 후보와의 관계

- **B3(design 분리) 구체화·흡수**: 골격 = 프로즈 대신 **실행 가능한 design 산출물**. B3의 "high-tier만 별도 design"을 컴파일 검증형으로 실체화.
- **B4(risk tier) 게이팅**: 작은 story엔 골격 task가 과례. tier로 적용 범위 제한(복잡·다함수 story만).
- **B2(EARS)**: 함수 계약을 EARS requirement로, mockist 테스트를 그 scenario로.

## 주의

- DisC의 **"리뷰 불필요"** 표방은 mockist로 구현을 1개로 못박는 강한 주장이다. 과도한 mocking은 리팩토링에 **brittle**해질 수 있어, 목표가 "리뷰 **피로 감소**"라면 full-review식 **"분리하되 리뷰 유지"**가 안전(두 극 중 후자 채택).
- architecture-scaffold도 주 용례를 "에이전트 일관성을 못 믿는 대규모 리팩토링"으로 한정 → tier 게이팅이 실전 권장.
- 대상 = 함수/이벤트 체인이 있는 로직-bearing story. config/데이터-only는 대상 아님(tier로 자연 배제).

## 인용

- DisC — github.com/mossgreen/design-is-code-plugin
- architecture-scaffold — playbooks.com/skills/petekp/agent-skills/architecture-scaffold
- full-review (멀티 하네스) — github.com/kadenn/full-review
- Jiti — github.com/RyanSaxe/jiti · Jitctx — github.com/jitctx/jitctx · SecretAgent — github.com/wwcohen/secretagent · GSD — github.com/dwall-sys/gsd-code-first
- HamReview — github.com/samuelasselin/hamreview · Floe — github.com/avifenesh/floe · LaReview — github.com/puemos/lareview · Metareview — github.com/dsifry/metareview · LazyLLM — docs.lazyllm.ai/en/stable/Best%20Practice/git_review_pipeline/ · diffray — diffray.ai/multi-agent-code-review/
- London-TDD: skillhub.club(tdd-london-chicago) · github.com/swingerman/atdd · github.com/petbrains/mvp-builder · github.com/swingerman/disciplined-agentic-engineering · github.com/genkovich/sdd
- 학술 — arxiv.org/pdf/2509.25297
- SDD 비교 — glukhov.org/ai-devtools/ai-coding-assistants/spec-kit-vs-kiro-vs-claude-code/
