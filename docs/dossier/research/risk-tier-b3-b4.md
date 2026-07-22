---
version: 1
---

# 검토: B3(design 분리) + B4(risk routing/consensus) — 위험도 tier로 통합

**상태**: 🟡 제안(시안). MED 우선순위. spec에서 채택 결정.

**출처**: adapter-exa /answer (Kiro design-phase·CodeConductor), 2026-07-22.

## 핵심 통찰 — B3·B4는 하나의 per-story 위험도 tier로 수렴

두 방향 모두 "**이 story가 얼마나 위험/복잡한가**"라는 단일 판정에 달렸다. 하나의 tier가 둘을 라우팅한다:

| 위험도 tier | B3 design | B4 review |
|-------------|-----------|-----------|
| **low**(루틴) | plan 내 design **섹션**만 | 경량 리뷰(code-reviewer) |
| **normal** | plan 내 design 섹션 | 현행(code-reviewer + security-reviewer 병렬) |
| **high**(복잡·breaking·보안) | **별도 design 산출물/단계** | + adversarial-review + **consensus 패널**(다관점 투표) + human gate |

→ **B1 delta가 tier를 먹인다(시너지 확정)**: MODIFIED/REMOVED 많은 delta(기존 requirement 변경=breaking) 또는 보안/critical 도메인 접촉 = 고위험. all-ADDED(신규) = 저위험. tack이 delta 구조에서 **위험 신호를 공짜로** 얻는다.

## B3 평가 — design은 기본 "섹션", 복잡할 때만 분리

- Kiro design.md = 기술 청사진(아키텍처·컴포넌트 책임·인터페이스·데이터 모델·에러 처리·테스트 계획). requirements=WHAT, design=HOW.
- **Kiro 스스로** 분리를 "복잡한 기능·회귀 비싼 버그·팀 프로젝트"에만 권함. 루틴은 Quick Plan(게이트 없이 3문서 일괄).
- **tack 판정**: story = 1 PR(대개 루틴). 매 story 3문서 강제는 ceremony. tack은 이미 implementation-plan에 design 사고 + architect 에이전트 보유. → **기본: design을 plan의 명시 섹션으로**. high-tier story만 **별도 design 단계**로 승격. (신규 게이트 아님 — tier 라우팅.)

## B4 평가 — 위험도 라우팅 + 고위험 consensus (경량만)

- CodeConductor: 위험도(low/med/high) 분류 → 전문 에이전트 라우팅. 고위험 → council-consensus(다수/만장 투표 + confidence 임계 <0.6/평균<0.7 escalate + 보안 veto + human gate).
- **tack은 이미 조각을 가짐**: code-reviewer + security-reviewer 병렬, adversarial-review(opt-in). 문제는 **위험 무관하게 균일 적용**.
- **tack 판정**: **경량 위험 tier(low/normal/high)** 도입해 리뷰 깊이 라우팅. 고위험만 adversarial + consensus 패널(다관점 투표) + human gate. 저위험은 경량 리뷰로 **비용 절감**.
- tack의 기존 원리와 연속: `performance.md`가 이미 모델을 복잡도로 라우팅(haiku/sonnet/opus). risk-tier는 그 원리를 **리뷰 깊이**로 확장.

## 비싼 꼬리 — 연기 (defer-the-tail)

CodeConductor의 무거운 기계장치는 tack 규모에 과설계:
- confidence 임계 자동 escalate, veto 채널, versioned agent contracts → **연기**.
- MVP = **3-tier 라우팅 + 고위험 consensus 패널**뿐. 위험도 판정은 planner(또는 delta 형태 규칙)가 부여.

## 권고 요약

| 방향 | 판정 | 형태 |
|------|------|------|
| B3 design 분리 | 🟢 채택(경량) | 기본=plan design 섹션, high-tier만 별도 |
| B4 risk 라우팅 | 🟢 채택(경량) | 3-tier가 design ceremony(B3)+리뷰 깊이 동시 라우팅 |
| B4 consensus | 🟠 고위험만 | 다관점 투표 패널(기존 adversarial 확장) |
| 무거운 기계장치 | 🔴 연기 | confidence/veto/contracts |

**단일 메커니즘**: per-story 위험도 tier(low/normal/high). delta 형태(B1)가 신호, planner가 부여. 이 tier가 B3(design 분리)·B4(리뷰 깊이)를 함께 라우팅.

## Open Questions (spec)

- 위험도 판정 주체·규칙: planner 판정 vs delta 형태 자동 규칙(MODIFIED/REMOVED 수·보안 도메인) vs 혼합.
- consensus 패널 구성(어떤 관점 몇 개), 투표 규칙(다수/veto).
- tier 경계 정의(무엇이 high인가) — 보안·breaking·다도메인 등.
