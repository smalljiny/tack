---
version: 3
---

# tack 컨텍스트 저장소 (Context Store)

tack은 장치 간 세션 컨텍스트 공유를 위해 **원격 영속 저장소**를 둔다. 이 문서는 확정된 `remote-context-store` 스펙(Track 1)을 tack이 **흡수**하면서 오늘 세션의 결정(용어·session-model·GitHub 이슈)으로 **재정합**한 결과를 기록한다. 용어는 `glossary.md`, 세션 경계는 `session-model.md` 기준.

## 출처 — remote-context-store 스펙 흡수

원 스펙: `docs/_local/backlog/remote-context-store/spec.md` (`spec:confirmed`). tack이 이를 subsume한다. 아래 재정합 항목을 반영해 tack 기준으로 개정·재리뷰한다(confirmed → reviewing). 개정 대상이 아닌 결정(port/adapter, 오프라인 폴백, lease 생애주기, secret 처리, 부트스트랩, node-forwarder shim 등)은 원 스펙 그대로 승계한다.

## 역할 배분 🟢 확정 — 3계층, Mongo+CLI가 대시보드

> **최종 결정(2026-07-22) — GitHub Projects 폐기, MongoDB 확정.** 원 스펙 G2 대시보드는 phase:status **뿐 아니라 소유 세션·`acquired_at`·`last_activity_at`**(lease·소유권·활동)을 요구한다. GitHub Projects는 이 Mongo-소유 런타임 사실을 구조적으로 못 보여주므로 "Projects=대시보드"는 G2를 만족시키는 게 아니라 **두 표면으로 쪼갠다**. 따라서 GitHub Projects는 **채택하지 않는 폐기된 안**이며, 대시보드·상태 저장소는 **MongoDB shared registry + CLI 대시보드**로 최종 확정한다(발명 없음 — 오프라인 큐·복구 이미 스펙됨).

| 계층 | 역할 | 근거 |
|------|------|------|
| **GitHub 이슈** | story·epic **정체성/존재** + **PR·코드·sub-issue 링크**(딜리버러블 앵커) | PR-closes-story·sub-issue 계층이 싸고 실질적. **대시보드·워크플로우 상태는 안 맡음** |
| **로컬 per-worktree private** | `phase:status` **SoT** (hot path) | 매 `/flow-*` 전이·게이트. 네트워크에서 분리 (blocker-2 격리 무변경) |
| **원격 Mongo Atlas** | **shared registry**(phase:status 스냅샷 + 소유 세션·`acquired_at`·`last_activity_at`) + **lease(G5)** + **충돌 인덱스(G4)** + config. **대시보드(G2) 데이터 원천** | 원 스펙 그대로. lease·활동·충돌·상태를 한 표면에 — 대시보드가 온전 |

- **대시보드 = CLI-first** (`list_topics`/`tack dashboard`), Mongo 위에서. 원 스펙 G2가 원래 CLI였다. 호스팅 웹앱은 "훅은 Atlas 안 친다" 경량 기조에 반하니 배제.
- **상태 흐름**: 로컬 private가 SoT → staleness 허용 지점(대시보드 조회 등)에 Mongo shared registry로 스냅샷 publish. GitHub 이슈엔 워크플로우 상태를 **투영하지 않음**(딜리버러블 앵커 역할만).
- **엔진**: Mongo Atlas 기본(이미 운영), **port/adapter 유지** → Firebase 등 미래 어댑터 slot-in.
- **config 위치**: Mongo 잔류로 잠정.
- **GitHub Projects 최종 폐기**: 대시보드·상태 저장소는 **MongoDB로 최종 확정**. Projects는 G2의 lease·활동·소유권을 못 담아 채택하지 않는다(폐기된 안).

## 재정합 항목 (원 스펙 → tack 개정)

**① G3 스펙 저작 위치 — 개정.** 원 스펙 G3는 "스펙 저작을 worktree에서, 프로비저닝을 `spec:confirmed` 이전으로 당김"이었으나, session-model 확정(경계=`spec:confirmed`, 스펙=hub)과 충돌. G3가 묶은 두 목적을 분리해 해소:
- (a) 저작 시 충돌 사전검토(G4) → **hub가 원격 store를 읽어 성립**. worktree 불필요, G4 보존.
- (b) 저작 중 lease 보호 → **불필요**. lease는 구현(worktree)을 보호하고, 스펙은 lease 이전 탐색(doc-only, git-ignored). 두 장치가 같은 스펙을 써도 무해 — lease는 프로비저닝에서 발동.
- → G3 삭제·재작성. 프로비저닝 게이트는 `spec:confirmed` 유지.

**② topic → story 리네임.** 스펙 데이터 모델 전반 파급 — lease-per-topic → lease-per-story, `IntentDoc.topic` → `.story`, `project_id` scoping은 유지. glossary §1 기준.

**③ 상태 계층 — 원 스펙 유지(개정 철회).** 한때 shared registry 스냅샷을 GitHub Projects로 이관하려 했으나 G2(lease·활동 포함)를 못 담아 **Projects 폐기**. Mongo operation 전부 유지 — `list_topics`(CLI 대시보드), `acquire/release_lease`, `upsert_intent`/`query_overlapping`, phase 스냅샷 publish. GitHub 이슈는 워크플로우 상태를 안 받고 딜리버러블 앵커만.

## 승계 (원 스펙 무변경)

- port/adapter 경계(`ContextStore` 인터페이스), Mongo/Local 어댑터, Postgres 지연
- 2계층 hot-path 분리(로컬 private + 원격), 오프라인 지속 + 재연결 복구(G6, 단순화)
- lease 생애주기(획득=worktree 생성, 해제=`/flow-done`), force 양방향, heartbeat 없음
- secret 레포밖 파일 + env-경로, 부트스트랩(uv venv), node-forwarder shim + Node 로컬 폴백
- `project_id`는 `/flow-init`에서 설정, 단일 DB + `project_id` 필드 scoping

## Open Questions

- config 최종 위치(Mongo vs 레포 커밋).
- Mongo shared registry 스냅샷·CLI 대시보드 스키마(어떤 phase·소유·활동·충돌 필드를 `list_topics`가 노출하는지) — 재정합 spec에서 확정. (GitHub 이슈는 딜리버러블 앵커만, 워크플로우 상태 투영 없음.)
- 원 스펙 §6 Open Questions(재연결 감지, stale lease UX, resume 진입점)는 그대로 승계.
