# tack

Claude Code로 구동하고 Codex가 게이트마다 리뷰하는 spec 주도 개발 하네스. Copier로 배포된다.

## 무엇인가

tack은 개발 워크플로우를 상태 머신으로 만든 **배포 가능한 하네스 제품**이다.

- **이중 도구** — Claude Code가 각 단계를 실행하고, Codex가 spec·plan·최종 리뷰 게이트에서 독립 검토한다.
- **spec 주도** — 모든 기능은 spec → plan → 구현 순으로 흐르며, 각 전환은 리뷰 게이트를 통과해야 한다.
- **Copier 배포** — tack은 source 트리(`template/`)를 개발·추적하고, Copier가 이를 소비 프로젝트의 destination(`.claude/`·`.codex/`·`.tack/`)으로 렌더한다. source를 편집하고 destination은 렌더 결과다 (→ [base-layout](docs/specs/base-layout.md)).

## 개발 흐름

토픽 하나가 아래 파이프라인을 따라 흐른다. 각 단계는 슬래시 커맨드로 실행하며 `dev-context`가 상태를 추적한다.

```
/flow-spec → /flow-plan → /flow-impl → /flow-review → /flow-verify → /flow-docs → /flow-pr → /flow-done
```

| 단계 | 하는 일 | 리뷰 게이트 |
|------|---------|------------|
| `/flow-spec` | 스펙 초안 작성 | Codex spec-review (READY까지 루프) |
| `/flow-plan` | 구현 계획(Story 분해) 수립 | Codex plan-review |
| `/flow-impl` | Story별 구현 (TDD + 코드 리뷰 자동 호출) | — |
| `/flow-review` | 전체 변경 리뷰 | code-reviewer + security-reviewer, Codex adversarial-review(opt-in) |
| `/flow-verify` | 검증 게이트 (build·type·lint·test·security) | — |
| `/flow-docs` | 참조 문서(`docs/specs/`) 생성·갱신 | — |
| `/flow-pr` | 브랜치 push + PR 생성 | — |
| `/flow-done` | 산출물 아카이브·토픽 정리 | — |

보조 커맨드: `/flow-topic`(토픽 전환), `/flow-worktree`(격리 워크트리), `/flow-setup`·`/flow-init`(초기 설정).

전문 서브에이전트(planner·tdd-specialist·code-reviewer·architect 등 10개)가 단계별로 자동 호출된다 (→ [agent-roster](docs/specs/agent-roster.md)).

## 저장소 구조

| 경로 | 내용 |
|------|------|
| `docs/specs/` | 배포 하네스의 권위 참조 문서 (레이아웃·Copier 골격·에이전트 로스터 등) |
| `docs/dossier/` | tack의 방향 설정 자료 (용어·아키텍처·연구·핸드오프) |
| `docs/roadmap.md` | Epic/Story 로드맵 (무엇을 어떤 순서로) |
| `template/` | Copier가 렌더할 배포 source 트리 |

세부 사항은 각 `docs/specs/*.md`가 담당한다 — 이 README는 진입점일 뿐이다.

## 현재 상태

**Phase 0 (부트스트랩)**. tack은 실전 검증된 레퍼런스 하네스를 더 나은 구조·배포로 재구현하는 v2다. 현재는 레퍼런스 하네스를 dogfooding하며 `template/` source 트리를 구축하는 단계이며, tack이 자기 하네스로 자신을 개발하는 self-host 전환점(M1)을 향한다.

## 기술 스택

- **Python / uv** — 스크립트·상태 머신·훅 (전환 대상; 현재 부트스트랩은 레퍼런스 Node 하네스)
- **Bash** — Copier 배포 substrate
- **Markdown** — 에이전트·스킬·커맨드·규칙 컴포넌트
- **MongoDB** — 공유 컨텍스트 저장소 (registry·lease·대시보드)
