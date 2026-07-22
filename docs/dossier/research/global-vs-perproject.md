---
version: 1
---

# 검토: global 설치 vs per-project (OQ1)

**질문**: tack을 (cmux처럼) 머신 전역에 설치하는가, 아니면 per-project(Copier)로 배포하는가?

## 두 층 + 가로지르는 contracts

| 층 | 예 | global 친화 |
|----|-----|-------------|
| capability | skills·agents·commands·CLI·generic rules | ✅ 프로젝트 무관 |
| config/state | CLAUDE.md/AGENTS.md 프로젝트 섹션·commit-scopes·project.id·dev-context 상태 | ❌ 프로젝트 고유 |
| **contracts** | `.harness/contracts/` | ⚠ 내용 무관, **버전은 프로젝트 산출물과 결합** |

## global의 환원 불가능한 비용 — 계약 업데이트 타이밍 통제 상실

`.harness/contracts/`는 포맷 명세라 내용상 프로젝트 무관이지만, 버전이 그 계약으로 생성한 프로젝트별 산출물(spec-review·plan-review·implementation-plan)과 묶인다. global은 스큐를 제거하는 게 아니라 **"스킬↔계약"에서 "global 계약↔프로젝트 산출물"로 옮기고, 업데이트를 미룰 능력을 제거**한다.

> 예: 프로젝트 A가 계약-v1 in-flight 플랜 보유 → tack 전역 v2 → A의 plan-review(이제 v2)가 A의 v1 플랜을 읽어 **미룰 수 없는 불일치**. per-project `copier update`면 A에만 clean 경계에서 착지.

(지난 턴의 "global=스큐"는 부정확했고, "global 전체 capability=스큐 없음"도 과함. 진실은 중간 — 스큐가 아니라 **타이밍 통제**가 비용.)

## "per-project = 재현성"은 조건부

per-project 재현성 이점은 tack 파일이 target repo에 **커밋될 때만** 성립. `wf-worktree-context`가 "하네스 git-미추적 프로젝트"를 명시 → 미추적이면 per-project는 재현성 무이득, footprint만 증가. 따라서 "per-project 기본" 선호는 생각보다 균형적.

## Vercel symlink 중간경로 — 채택 제약

"global 원천 + per-project symlink"(Vercel Skills 권장)는 tack worktree의 copy 결정(blocker-1 codex 샌드박스·blocker-2 dev-context.js 경로)과 충돌. tack이 이미 symlink 대신 copy를 택한 층에는 부적합.

## 결정 — 워크플로우 사실 하나로 갈림

**한 머신의 두 프로젝트가 서로 다른 tack 버전을 필요로 하는 경우가 있는가?**
- 있다 → **per-project 필수**(버전 핀 + 계약 타이밍 통제).
- 없다(항상 최신) → **global 유효·ergonomic 우월**(footprint 0, 1회 업데이트로 전 프로젝트).

## 🟢 확정 — per-project (Copier)

사용자 확정(2026-07-21): **per-project (Copier)**. 프로젝트별 버전 핀 + 계약 업데이트 타이밍 통제 유지, in-flight 산출물 보호. global 설치는 배제(계약 타이밍 통제 상실이 결정적). 결과로 §0 유보 층 이름 도출 가능 — **tack repo = Copier 템플릿(원천), target project = 생성된 인스턴스**.
