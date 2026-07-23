---
version: 1
name: adapter-github-issue
description: Mint GitHub issues and labels as deliverable anchors via the `gh` CLI. Idempotently bootstraps type:epic/type:story labels, creates story issues, and mints flat epic umbrella issues with uniform personal/org account routing. Self-skips with a manual fallback when `gh` is missing or the target owner is unauthenticated. Intended for direct Load by consumer skills (flow-spec, flow-pr) rather than skill-registry discovery.
origin: harness
---

# adapter-github-issue

`gh` CLI를 감싸 epic·story를 GitHub 이슈로 프로그램적으로 mint하는 외부-도구 어댑터다.

**역할**: `type:epic`·`type:story` 라벨을 멱등 부트스트랩하고, story 이슈를 생성하며, epic umbrella 이슈를 flat 하게 mint한다. 대상 repo owner가 개인 계정이든 조직 계정이든 분기 없이 균일 처리한다.

**산출물 (stdout 계약)**: 생성 연산은 이슈 번호와 URL을 stdout으로 반환한다. 호출자는 stdout을 파싱해 후속 배선(E3)에 사용한다.

**소비자**: 소비자 스킬(`flow-spec`·`flow-pr`)이 이름으로 직접 Load하도록 설계된다 — skill-registry 발견 대상이 아니다. 실제 호출 배선은 E3-S2·E3-S5 소관이다. 본 스킬은 flat 이슈·라벨 mint 연산만 제공하며, 트리거 배선·PR 링크·sub-issue 계층은 소비자와 후속 스토리 소관이다.

**제약**: 이슈는 딜리버러블 앵커일 뿐 워크플로우 상태(phase:status 등)를 담지 않는다 — 상태 저장소는 MongoDB(E4) 소유다. `gh` 미설치 또는 대상 owner 미인증 시 mint를 skip하고 수동 명령을 안내한다 (하드 실패 아님). 제목·본문 동적 문자열은 stdin(`--body-file -`)으로 전달하며 `-m "$VAR"` 보간을 금지한다 (`.tack/rules/security.md` Shell Injection Defense).

## Tier Rationale

본 컴포넌트는 5-tier 스킬 체계의 `adapter-*` tier에 속한다.

- **판별 근거**: 외부 도구(`gh` CLI)를 래핑하고, 도구 미가용 시 자체적으로 skip/fallback을 선택한다. `component-boundaries` 결정 트리에서 "외부 도구 없으면 skip/fallback을 자체 선택하는가? → 예 → `adapter-*`" 경로로 귀결된다.
- **명명**: 컴포넌트 이름은 `adapter-github-issue`로 확정한다. 이후 모든 파일 경로·참조는 이 이름을 일관되게 사용한다.
- **직접 Load되는 non-search adapter 선례**: 하네스의 `adapter-*`가 모두 skill-registry 발견 대상 search-adapter인 것은 아니다. `adapter-codex-review`(Codex CLI 래핑)와 `adapter-dependency-analysis`(knip·dependency-cruiser 래핑)는 둘 다 외부 도구를 감싸고 가용성 게이트를 가지며, skill-registry 발견이 아니라 `flow-*` 스킬이 이름으로 **직접 Load**하는 non-search adapter다. `adapter-github-issue`도 동일하게 소비자가 이름으로 직접 Load하는 non-search adapter다.

## Non-Goals

다음은 본 컴포넌트의 범위 밖이며 구현하지 않는다:

- **sub-issue 계층 링크**: epic umbrella 아래 story를 GraphQL node ID로 계층 연결하는 작업. E5-S2 소관. S1은 flat 이슈 생성까지만.
- **PR-closes-story 링크**: PR을 story 이슈에 연결하는 작업. E5-S3 소관.
- **flow-spec/flow-pr 배선**: 소비자 스킬에 본 컴포넌트 호출을 삽입하는 작업. E3-S2·E3-S5 소관. S1은 독립 컴포넌트만 제공한다.
- **Projects 대시보드**: 폐기됨. 대시보드·상태 저장소는 MongoDB(E4) 소유다.
- **native 커스텀 Issue Types**: 폐기됨. 타입 표현은 라벨(`type:epic`·`type:story`) 단일 방식이다.
- **워크플로우 상태 저장**: 이슈에 phase:status 등 워크플로우 상태를 담지 않는다. 상태는 MongoDB 소유다.
- **기존 수동 이슈 마이그레이션·정리**: ad-hoc 생성된 기존 이슈의 재작성·정합화는 범위 밖이다.

> **Deferred to E3 (OQ4 — epic umbrella 트리거)**: umbrella 이슈를 언제·누가 mint하는가(hub가 신규 epic 감지 시 자동 vs 명시 호출)는 E3-S2 배선 시점에 확정한다. 본 컴포넌트는 mint **연산**만 제공하고 트리거 배선은 소비자 소관이다. (기록만 — S1 범위 밖)
