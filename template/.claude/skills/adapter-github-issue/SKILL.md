---
version: 3
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
2. 대상 repo에 쓰기 권한이 있는가 — `gh api repos/<owner>/<name> --jq .permissions.push`가 `true`를 반환하는가.

owner 핸들을 `gh auth status` 출력과 대조하는 방식은 사용하지 않는다. `gh auth status`는 인증된 **사용자 계정**을 나열할 뿐이고 `gh repo view --json owner`가 반환하는 org repo의 owner는 **조직 login**이므로, 이름 대조는 org repo를 (사용자가 write 권한을 가져도) 미인증으로 오판해 mint를 조용히 skip한다 — G4 개인/조직 균일 라우팅을 훼손한다. 대신 대상 repo에 대한 실제 권한을 조회한다:

```bash
gh api repos/<owner>/<name> --jq '.permissions.push' 2>/dev/null
```

`true`면 커버로 간주하고 진행한다. `false`·빈 출력·비-0 exit(auth 오류·repo 미접근)면 커버 불충분으로 보아 skip 경로로 폴백한다. 이 검사는 owner가 개인 계정이든 조직 계정이든 동일하게 동작한다.

`GH_ISSUE_DRY_RUN=1`이면 이 게이트를 평가하기 전에 §Dry-run Contract가 우선한다 — `gh`를 호출하지 않으므로 미설치·미인증 환경에서도 조합 명령 출력이 동작한다.

둘 중 하나라도 실패하면 mint를 **skip**하고 수동 명령을 안내한다. 하드 실패(비-0 exit)하지 않는다. 안내 명령의 전체 형태는 §Label Bootstrap·§Story Issue Create를 따른다 (제목은 §Shell-Injection Defense의 HEREDOC 캡처 패턴 사용).

```
gh를 사용할 수 없어 이슈 mint를 건너뜁니다. 수동으로 실행하세요 (전체 명령은 §Label Bootstrap·§Story Issue Create 참조):
  gh label create type:epic  --repo <owner>/<name> --color 5319E7 --description "Epic anchor issue"
  gh label create type:story --repo <owner>/<name> --color 1D76DB --description "Story anchor issue"
  # story 이슈: 제목을 단일따옴표 HEREDOC로 캡처한 뒤 --title "$TITLE" --body-file - 로 생성
```

### Account Routing (owner별 타입 분기 없음)

라벨(`type:epic`·`type:story`)은 개인·조직 repo에서 균일하게 동작하므로 타입 표현에 owner별 분기가 **없다**.

- **owner 감지**: `gh repo view --json owner` — 배포된 repo의 실제 owner를 그대로 사용한다 (개인 계정이든 조직 계정이든 무관). 컴포넌트는 특정 계정 핸들을 하드코딩하지 않는다.
- **권한 커버 확인**: `gh api repos/<owner>/<name> --jq .permissions.push`로 대상 repo에 대한 실제 write 권한을 조회한다 (§Availability Gate). owner 이름을 `gh auth status`와 대조하지 않는다 — org repo 오판을 피한다.
- **대상 지정**: 모든 연산은 `--repo <owner>/<name>`를 명시하거나 현재 repo 컨텍스트로 해석한다.

### Shell-Injection Defense

이슈 제목·본문 등 동적 문자열은 셸 인자로 보간하지 않는다 (`.tack/rules/security.md` Shell Injection Defense 준수).

- **본문**: `--body-file -`로 stdin 전달한다. 여러 줄 본문은 단일따옴표 HEREDOC(`<<'BODY' ... BODY`)으로 파이프한다 — 변수 확장·명령 치환이 비활성화된다.
- **제목**: 동적 제목은 먼저 단일따옴표 HEREDOC로 변수에 **캡처**한 뒤 `--title "$TITLE"`로 전달한다. `"$TITLE"`은 이미 채워진 변수를 한 번만 확장하므로 값 내부의 백틱·`$()`를 재평가하지 않는다 — **단, 이 안전성은 변수가 단일따옴표 HEREDOC 캡처로 채워졌을 때만 성립한다**.

  ```bash
  TITLE=$(cat <<'TITLE_EOF'
  <story-id> — <요약>
  TITLE_EOF
  )
  gh issue create ... --title "$TITLE" --body-file - <<'BODY'
  ...
  BODY
  ```

- **금지 — 리터럴 직접 보간**: 신뢰불가 텍스트(spec 요약·AI 생성 문자열)를 `--title "<...>"`처럼 명령 소스의 큰따옴표 리터럴에 **직접 보간**하지 않는다. 큰따옴표는 리터럴 소스의 word-splitting·globbing만 억제할 뿐, 그 안에 실제로 존재하는 백틱·`$()`의 명령 치환은 막지 못한다. 제목이 백틱을 포함하면(예: `` Fix `parseUser()` bug `` — 마크다운 코드 관례로 흔함) gh 도달 전에 셸이 `parseUser()`를 실행한다. 이것이 `.tack/rules/security.md`가 금지한 "문자열 연결로 셸 인자 구성"이다.
- **금지 — `-m` 인라인**: `-m "$VAR"` 또는 `-m "$(...)"` 패턴. 동적 메시지는 항상 stdin(`--body-file -`) 또는 위 HEREDOC 캡처로 우회한다.

### Dry-run Contract (echo-not-execute)

환경변수 `GH_ISSUE_DRY_RUN=1`이 설정되면 모든 연산은 **echo-not-execute** 모드로 동작한다:

- 조합된 `gh` 명령을 stdout에 출력한다.
- `gh`를 **전혀 호출하지 않는다** (zero gh calls) — 실 이슈·라벨을 생성하지 않는다.
- exit 0으로 종료한다.

dry-run은 Availability Gate에 우선한다 — `gh`를 호출하지 않으므로 `gh` 미설치·미인증 환경에서도 조합 명령 출력이 동작한다. 따라서 dry-run 점검은 `gh` 없이 성립한다.

이 계약에 따라 dry-run 모드는 대상 repo를 오염시키지 않는다 (gh 미호출이 구조적으로 무오염을 보장한다). standalone 검증(§Standalone Verification)은 이 성질을 정적 점검으로 확인한다.

### stdout Return Convention

생성 연산(story 이슈·epic umbrella)은 성공 시 생성된 이슈 **번호**와 **URL**을 stdout으로 반환한다. 호출자는 stdout을 파싱해 후속 배선에 사용한다. dry-run 모드에서는 실 번호·URL 대신 조합된 gh 명령만 출력한다.

## Label Bootstrap (G1 — 멱등)

`type:epic`·`type:story` 두 라벨을 대상 repo에 부트스트랩한다. §Operational Contract(가용성 게이트·계정 라우팅·dry-run)를 따른다.

### 연산

```bash
gh label create type:epic  --repo <owner>/<name> --color 5319E7 --description "Epic anchor issue"
gh label create type:story --repo <owner>/<name> --color 1D76DB --description "Story anchor issue"
```

### 멱등성

라벨이 이미 존재해도 실패하지 않는다. 두 방식 중 하나를 사용한다:

- **선체크**: `gh label list --repo <owner>/<name>`로 라벨 존재를 확인하고, 없는 라벨만 생성한다.
- **오류 tolerate**: `gh label create ... 2>/dev/null || true`로 "already exists" 오류를 흡수한다. 이 방식은 auth·network 등 실 오류도 함께 흡수하므로 선체크를 우선한다.

재실행 시 두 라벨이 모두 존재하면 no-op이며 exit 0으로 종료한다. 현재 대상 repo에 이미 존재하는 `type:epic`·`type:story`(수동 생성분)와 충돌하지 않는다.

### dry-run

`GH_ISSUE_DRY_RUN=1`이면 §Dry-run Contract에 따라 두 `gh label create` 명령을 stdout에 출력하고 `gh`를 호출하지 않으며 exit 0으로 종료한다 — 라벨을 생성하지 않는다. 선체크(`gh label list`)도 gh 호출이므로 dry-run에서는 건너뛰고 두 create 명령만 출력한다.

## Story Issue Create (G2 — 중복 가드 포함)

`type:story` 라벨을 단 story 이슈를 생성한다. §Operational Contract를 따른다. 제목은 `<story-id> — <요약>`, 본문은 spec 요약과 링크다.

### 중복 가드 (컴포넌트 책임 — OQ3)

동일 story-id 이슈 재생성을 컴포넌트가 막는다 (caller 책임이 아니라 컴포넌트 소유). 생성 **전** 검색으로 기존 이슈를 확인한다.

story-id는 셸 인자로 보간되기 전에 형식을 검증한다 — `^E[0-9]+-S[0-9]+$`에 매칭하지 않으면 skip한다. 이 어서션은 중복 가드 prefix 판정의 전제이자, 제약된 식별자가 셸에 도달하기 전 백틱·`$()` 유입을 차단하는 방어다.

```bash
gh issue list --repo <owner>/<name> --label type:story --search "<story-id> in:title" --json number,url,title --state all
```

- `--search`는 GitHub 검색의 하이픈 토크나이즈로 fuzzy 매칭되므로 결과를 **title로 post-filter**한다 (검색 출력에 `title` 필드를 포함한 이유).
- 제목이 `<story-id> —`(story-id + 구분자 " — ")로 **정확히 시작**하는 이슈만 **중복**으로 판정한다. bare-prefix가 아니다 — `E5-S1`으로 검색해도 `E5-S10 — ...` 제목은 구분자 경계 불일치로 중복이 아니다 (false-positive 방지).
- 중복이면 생성을 **skip**하고 기존 이슈의 번호·URL을 stdout으로 출력한 뒤 exit 0으로 종료한다 (skip-not-fail). 하드 실패하지 않는다.
- 중복이 없으면 생성으로 진행한다.
- `--state all`로 closed 이슈까지 감지해 재생성을 방지한다.

### 생성 연산

본문은 stdin(`--body-file -`)으로 전달한다. 제목은 단일따옴표 HEREDOC로 변수에 캡처한 뒤 `--title "$TITLE"`로 전달한다 (§Shell-Injection Defense — 리터럴 직접 보간 금지).

```bash
TITLE=$(cat <<'TITLE_EOF'
<story-id> — <요약>
TITLE_EOF
)
gh issue create --repo <owner>/<name> --label type:story \
  --title "$TITLE" --body-file - <<'BODY'
<spec 요약>

Spec: <spec 링크>
BODY
```

생성 성공 시 §stdout Return Convention에 따라 이슈 번호와 URL을 stdout으로 반환한다.

### dry-run

`GH_ISSUE_DRY_RUN=1`이면 §Dry-run Contract에 따라 조합된 `gh issue create` 명령(제목·라벨·대상 repo 포함)을 stdout에 출력하고 `gh`를 호출하지 않으며 exit 0으로 종료한다 — 이슈를 생성하지 않는다. 중복 검색(`gh issue list`)도 gh 호출이므로 dry-run에서는 건너뛴다.

## Epic Umbrella Mint (G3 — flat)

`type:epic` 라벨을 단 umbrella 이슈를 생성한다. §Operational Contract를 따른다. epic 요약과 묶인 story 목록을 본문에 기술하는 상위 앵커다.

### flat 생성 (계층 링크 없음)

본문에 묶인 story id를 **텍스트로만** 나열한다. sub-issue 계층 링크(GraphQL node ID로 부모-자식 연결)는 **하지 않는다** — E5-S2 경계다. S1은 flat 이슈 생성까지다.

본문은 stdin(`--body-file -`)으로 전달한다 (§Shell-Injection Defense).

```bash
TITLE=$(cat <<'TITLE_EOF'
<epic-id> — <epic 요약>
TITLE_EOF
)
gh issue create --repo <owner>/<name> --label type:epic \
  --title "$TITLE" --body-file - <<'BODY'
<epic 요약>

## 묶인 Story
- <story-id-1> — <요약>
- <story-id-2> — <요약>
BODY
```

story 목록의 각 항목은 사람이 읽는 텍스트 라인이다. GitHub sub-issue 위젯에 연결되는 링크·node ID 참조를 포함하지 않는다.

> **중복 가드 이월**: story 이슈(§Story Issue Create)와 달리 epic umbrella는 재-mint 중복 가드를 두지 않는다. umbrella를 언제·누가 mint하는가(트리거)가 OQ4로 E3-S2에 이월됐으므로, 재-mint 멱등성도 트리거 배선과 함께 E3-S2에서 확정한다. 의도적 이월이며 누락이 아니다.

### stdout·dry-run

생성 성공 시 §stdout Return Convention에 따라 이슈 번호와 URL을 stdout으로 반환한다. `GH_ISSUE_DRY_RUN=1`이면 §Dry-run Contract에 따라 조합된 `gh issue create` 명령을 stdout에 출력하고 `gh`를 호출하지 않으며 exit 0으로 종료한다 — 이슈를 생성하지 않는다.

## Standalone Verification (G6 — 무오염 dry-run)

소비자(E3) 배선 없이 컴포넌트를 독립 검증한다. 검증은 `GH_ISSUE_DRY_RUN=1` 하에서만 수행하며, §Dry-run Contract가 gh 미호출(zero gh calls)을 보장하므로 대상 repo(예: `smalljiny/tack`)를 오염시키지 않는다 — 무오염은 실행이 아니라 **구조적으로** 성립한다.

### 검증 절차

G6 검증은 두 확인 행위로 구성되며 서로 다른 주체가 수행한다:

- **(a) dry-run 출력 확인** — 계약을 실행하는 에이전트/소비자가 `GH_ISSUE_DRY_RUN=1` 하에서 세 연산의 bash를 해석·echo해 조합된 gh 명령이 stdout에 나오는지 확인한다. 본 컴포넌트는 실행 코드 없는 프롬프트 문서이므로 `GH_ISSUE_DRY_RUN`을 읽는 러너가 별도로 존재하지 않는다 — 라이브 dry-run 실행은 소비자(E3)가 컴포넌트를 구동할 때 일어난다.
- **(b) 무오염 보장** — §Dry-run Contract의 zero gh calls로 **구조적으로** 성립하며, 실 repo 조회·생성 없이 계약 텍스트의 정적 점검(reasoning)으로 확인한다. S1의 코드 없는 범위에서 G6은 이 구조적·정적 확인이다.

세 연산을 `GH_ISSUE_DRY_RUN=1`로 해석했을 때 stdout에 조합된 gh 명령이 출력되는지 확인한다:

1. **라벨 부트스트랩** (§Label Bootstrap) — dry-run 시 두 `gh label create` 명령(`type:epic`·`type:story`)이 출력되고 라벨은 생성되지 않는다.
2. **story 이슈** (§Story Issue Create) — dry-run 시 조합된 `gh issue create --label type:story` 명령이 출력되고 이슈·중복 검색(`gh issue list`) 모두 gh를 호출하지 않는다.
3. **epic umbrella** (§Epic Umbrella Mint) — dry-run 시 조합된 `gh issue create --label type:epic` 명령이 출력되고 이슈는 생성되지 않는다.

### 무오염 확인

세 연산 모두 dry-run에서 gh를 호출하지 않으므로(§Dry-run Contract) 대상 repo에 실 이슈·라벨이 생성되지 않는다. 이 성질은 gh 미호출로 구조적으로 보장되며, 실 repo에 대한 조회·생성 없이 계약 텍스트의 정적 점검으로 확인한다. 실 이슈·라벨을 만들지 않는 것이 검증의 전제이므로 검증 자체가 repo를 변경하지 않는다.
