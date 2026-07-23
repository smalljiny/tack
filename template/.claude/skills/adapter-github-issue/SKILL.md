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

## Operational Contract

모든 mint 연산(라벨 부트스트랩·story 이슈·epic umbrella)이 공유하는 실행 계약이다. 이후 연산 섹션은 이 계약을 재정의하지 않고 "Operational Contract를 따른다"로 참조한다.

### Availability Gate

`gh` 명령을 실행하기 전에 두 조건을 확인한다:

1. `gh` CLI가 설치돼 있는가 — `command -v gh`.
2. 대상 repo owner가 인증됐는가 — `gh auth status`가 해당 owner를 커버하는가.

둘 중 하나라도 실패하면 mint를 **skip**하고 수동 명령을 안내한다. 하드 실패(비-0 exit)하지 않는다.

```
gh를 사용할 수 없어 이슈 mint를 건너뜁니다. 수동으로 실행하세요:
  gh label create type:story --repo <owner>/<name>
  gh issue create --repo <owner>/<name> --label type:story --title "<title>" --body-file -
```

### Account Routing (owner별 타입 분기 없음)

라벨(`type:epic`·`type:story`)은 개인·조직 repo에서 균일하게 동작하므로 타입 표현에 owner별 분기가 **없다**.

- **owner 감지**: `gh repo view --json owner` — 배포된 repo의 실제 owner를 그대로 사용한다 (개인 계정이든 조직 계정이든 무관). 컴포넌트는 특정 계정 핸들을 하드코딩하지 않는다.
- **인증 커버 확인**: `gh auth status`로 감지된 owner가 현재 인증에 포함되는지 확인한다.
- **대상 지정**: 모든 연산은 `--repo <owner>/<name>`를 명시하거나 현재 repo 컨텍스트로 해석한다.

### Shell-Injection Defense

이슈 제목·본문 등 동적 문자열은 셸 인자로 보간하지 않는다 (`.tack/rules/security.md` Shell Injection Defense 준수).

- **본문**: `--body-file -`로 stdin 전달한다. 여러 줄 본문은 단일따옴표 HEREDOC(`<<'BODY' ... BODY`)으로 파이프한다 — 변수 확장·명령 치환이 비활성화된다.
- **제목**: `--title "$TITLE"` 단일 인자로 전달한다. 큰따옴표로 감싼 변수 확장은 값 **내부**의 백틱·`$()`를 재평가하지 않으므로 안전하다. 문자열 연결로 명령을 조립하지 않는다.
- **금지**: `-m "$VAR"` 또는 `-m "$(...)"` 패턴. 위험한 것은 플래그 자체가 아니라 AI가 생성한 리터럴 메시지를 명령에 인라인 조립하는 경우다 — 백틱·`$()`·따옴표 escape 실패로 임의 명령이 실행될 수 있다. 동적 메시지는 항상 stdin(`--body-file -`)으로 우회한다.

### Dry-run Contract (echo-not-execute)

환경변수 `GH_ISSUE_DRY_RUN=1`이 설정되면 모든 연산은 **echo-not-execute** 모드로 동작한다:

- 조합된 `gh` 명령을 stdout에 출력한다.
- `gh`를 **전혀 호출하지 않는다** (zero gh calls) — 실 이슈·라벨을 생성하지 않는다.
- exit 0으로 종료한다.

dry-run은 Availability Gate에 우선한다 — `gh`를 호출하지 않으므로 `gh` 미설치·미인증 환경에서도 조합 명령 출력이 동작한다. 따라서 dry-run 점검은 `gh` 없이 성립한다.

이 계약에 따라 dry-run 모드는 대상 repo를 오염시키지 않는다 (gh 미호출이 구조적으로 무오염을 보장한다). standalone 검증(§Standalone Verification)은 이 성질을 정적 점검으로 확인한다.

### stdout Return Convention

생성 연산(story 이슈·epic umbrella)은 성공 시 생성된 이슈 **번호**와 **URL**을 stdout으로 반환한다. 호출자는 stdout을 파싱해 후속 배선에 사용한다. dry-run 모드에서는 실 번호·URL 대신 조합된 gh 명령만 출력한다.
