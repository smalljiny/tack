---
version: 3
---

# 자료: GitHub 이슈 메커니즘 (OQ2)

> ⚠ **부분 폐기 (2026-07-22, OQ2·OQ3 최종 결정)**: 이 노트의 **대시보드=Projects·커스텀 Issue Types 기계장치**(org 타입·label 폴백 어댑터·phase→Projects 필드 매핑·GraphQL status 래퍼) 관련 결론은 **최종 폐기**됐다. **① 최종 결정 — epic/story 표현은 이슈 라벨(`type:epic`·`type:story`)로 확정, native 커스텀 Issue Types는 채택하지 않는다**(org 전용이라 개인 repo 미지원 + 어댑터 복잡도 + GraphQL 타입 래퍼 불요, 라벨은 개인·조직 repo 균일 동작). **③ 대시보드=Projects는 폐기**, 대시보드·상태 저장소는 **MongoDB로 최종 확정**(→ Mongo+CLI, `context-store.md`·glossary OQ2·OQ3). 상태는 Mongo가 소유한다. **유효한 부분은 sub-issue 계층·issue를 딜리버러블 앵커로 쓰는 것뿐.** 아래 내용(특히 ① native Issue Types 권고, ③ 대시보드=Projects)은 폐기된 조사 기록으로만 보존한다.

**조사 대상**: §1의 `epic`/`story` 이슈 타입 + `epic 1:N story` 계층 + 대시보드(G2)를 GitHub에서 어떻게 표현하는가. tack이 이슈를 프로그램적으로 생성·링크·갱신해야 하므로 **자동화 성숙도**도 핵심.

**출처**: adapter-exa `/answer` (GitHub 공식 문서·Changelog), 2026-07-21.

## 결과 — GitHub 네이티브가 3요소 모두 지원

| tack 요소 | GitHub 메커니즘 | 상태·한계 |
|-----------|-----------------|-----------|
| `epic`·`story` 타입 구분 | **커스텀 Issue Types** | GA, **org 레벨**, org당 최대 25종. REST `POST /orgs/{org}/issue-types` |
| `epic 1:N story` 계층 | **sub-issues** | GA, 부모당 100개, 8단계 중첩(tack은 2단계라 여유) |
| 대시보드(G2) | **GitHub Projects** | table/board/roadmap, 커스텀 status 필드, **타입별 필터/그룹** |
| 자동화 | GraphQL(주·성숙) + REST(2025-09 추가) + `gh api graphql` | node ID 기반. 타입 지정 생성·sub-issue 링크·status 갱신 가능 |

## 방향 함의 (tack 권고)

**① ~~타입 = 네이티브 Issue Types + labels 폴백~~ (폐기 — 라벨 단일 방식으로 확정, 상단 배너 참조).** 커스텀 Issue Types는 **org 레벨 기능**이다. 따라서:
- **org 소유 repo** → `epic`·`story`를 커스텀 Issue Type으로 등록(25종 한도 여유).
- **개인 repo**(org 아님) → Issue Types 미지원 → **labels로 폴백**(`type:epic`·`type:story`).
- 이건 tack의 port/adapter 철학과 정합 — **"이슈-타입 표현" 어댑터**(org=native types, 개인=labels)로 caller 무변경 slot-in.
- ⚠ 사용자 계정 라우팅(개인=smalljiny / 조직=happymario·aimers)상 **두 경우 모두 발생** → 폴백 필수.

**② 계층 = sub-issues.** epic(부모) ← story(자식). tack 2단계는 GitHub 한계(100개·8단계) 대비 여유. `task`·`subtask`는 이슈 아님(§1) → sub-issue 미사용.

**③ ~~대시보드 = Projects~~ (폐기 — MongoDB로 최종 확정, 상단 배너 참조).** coarse 상태를 Projects status 필드에 투영, 타입별 필터로 epic/story 뷰. G2 대시보드를 GitHub이 담당. → 이 안은 채택하지 않는다. 대시보드·상태 저장소는 Mongo shared registry + CLI(`list_topics`).

**④ 자동화 = `gh api graphql` 주축.** Projects 필드·sub-issue 링크는 GraphQL node ID 기반이라 단순 `gh issue create`보다 복잡. tack 자동화는 GraphQL 래퍼가 필요 — **구현 복잡도 요인**(spec에서 명령 래퍼 설계).

**⑤ "Task" 타입 충돌 — 해소 확인.** GitHub 기본 타입(Bug/Feature/Task)의 "Task"는 tack `task`(이슈 아님)와 무관. tack은 커스텀 타입 epic·story만 등록하고 기본 "Task"를 쓰지 않음 → 혼동 없음.

## Open (spec 단계)

- coarse 상태 → Projects status 필드 매핑(어떤 phase가 어떤 status/컬럼).
- 이슈-타입 어댑터(native vs labels) 감지 로직(repo가 org 소유인지 판정).
- GraphQL 명령 래퍼 설계(node ID 해석·타입 지정 생성·sub-issue 링크).

## 인용
- Managing issue types in an organization — docs.github.com/.../managing-issue-types-in-an-organization
- Evolving GitHub Issues [GA] — github.blog/changelog/2025-04-09-evolving-github-issues-and-projects/
- Adding sub-issues (REST API) — github.com/github/docs/.../adding-sub-issues.md
- REST API endpoints for Project items/fields — docs.github.com/en/rest/projects/
