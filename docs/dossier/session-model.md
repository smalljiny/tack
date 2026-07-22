---
version: 2
---

# tack 세션 운영 모델 (Session Model)

tack은 **메인(hub) 세션**과 **워크트리 세션**을 분리 운영한다. 이 문서는 어떤 작업이 어느 세션에 속하는지, 그 경계와 근거를 기록한다. 용어는 `glossary.md` 기준(story = 라이프사이클 단위 = 워크트리/PR 단위).

## 경계 — `spec:confirmed` (스펙 작성 완료) 🟢 확정

| 세션 | 소유 활동 | 성격 |
|------|-----------|------|
| **메인(hub)** | 스펙 작성·확정 (spec draft → 리뷰 루프 → `spec:confirmed`), epic·story 이슈 생성, story 워크트리 승격(provision/teardown) | 탐색적, cross-story, 가벼운 조율점 |
| **워크트리** | plan → impl → review → verify → docs → pr → done | 코드-바운드, intra-story, 긴 작업 |

story가 `spec:confirmed`에 도달하면 hub가 워크트리로 승격하고, 이후 라이프사이클은 워크트리 세션이 소유한다.

## 근거 — 왜 스펙은 hub, plan부터는 워크트리인가

**spec과 plan의 결정적 차이 (산출물이 아니라 내용):**
- `spec`: 산출물도 doc, 내용도 코드 무관 (무엇을·왜) → 코드 경로 불필요 → hub.
- `plan`: 산출물은 doc이지만 **내용이 코드-바운드** (실제 파일을 task=커밋으로 분해, 순서·의존 판단) → 실제 작업 경로(feature 브랜치)에서 작성해야 함 → 워크트리.

**뒷받침:**
1. **관심사 분리** — spec = cross-story 스코핑(epic 내 형제 story 조망 필요 → hub), plan = intra-story 분해(한 story 내부 → 워크트리로 충분). epic-형제 가시성은 spec에만 걸리고 plan엔 안 걸린다.
2. **처리량** — plan은 오래 걸린다. hub에서 돌리면 hub가 다른 story 스펙·조율을 못 한다. 긴 작업(plan+impl)을 워크트리로 오프로드해 hub를 가벼운 조율점으로 유지.
3. **그라운딩** — plan을 feature 브랜치 실파일 위에서 작성 → impl과 컨텍스트 공유, plan 핸드오프 소멸, main working tree 오염 없음.
4. **아키텍처 정합** — plan-review의 codex `workspace-write` 샌드박스 제약(blocker-1) 때문에 `docs/_local`이 per-worktree 실디렉토리로 설계됨 → plan-review가 워크트리에서 동작하도록 이미 만들어져 있음.

**수용한 반대 비용:** plan 도중 스펙 결함이 드러나면 프로비저닝 비용 매몰 + teardown. 단 (a) spec-review가 확정 전 스코프 이슈를 거르고, (b) tack story는 1 PR 크기라 대규모 재스코핑이 드물어 잔여 리스크는 작다.

## 현 harness와의 관계

이 경계는 현 harness의 검증된 설계(`flow-worktree`·`wf-worktree-context` — 프로비저닝 게이트 `spec:confirmed`, "main hub는 `/flow-spec`까지, plan 이후는 worktree")와 일치한다. tack은 재설계 부담 없이 이를 승계하되, glossary 용어(topic→story) 기준으로 재명명한다.

## Open Questions

- 병렬 story(같은 epic 아래 여러 워크트리) 동시 진행 시 hub의 조율·상태 집계는 OQ3 확정에 따라 **Mongo shared registry**(`context-store.md`)가 담당한다. 잔여: Mongo 스냅샷·`list_topics` 필드 스키마는 재정합 spec에서 확정.
