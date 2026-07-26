---
version: 6
name: adapter-github-issue
description: Mint GitHub issues and labels as deliverable anchors via the `gh` CLI. Idempotently bootstraps type:epic/type:story labels, creates story issues, and mints epic umbrella issues with uniform personal/org account routing. Links story issues under an epic as native sub-issues by issue number, with an idempotent pre-check and post-link verification. Links a pull request to its story issue with a same-repo `Closes #N` closing keyword and verifies the link via closingIssuesReferences, warning when the PR base is not the repository default branch. Self-skips with a manual fallback when `gh` is missing or the target owner is unauthenticated. Intended for direct Load by consumer skills (flow-spec, flow-pr) rather than skill-registry discovery.
origin: harness
---

# adapter-github-issue

`gh` CLI를 감싸 epic·story를 GitHub 이슈로 프로그램적으로 mint하는 외부-도구 어댑터다.

**역할**: `type:epic`·`type:story` 라벨을 멱등 부트스트랩하고, story 이슈를 생성하며, epic umbrella 이슈를 mint하고, epic↔story를 네이티브 sub-issue 계층으로 연결하며, PR을 story 이슈에 closing keyword로 연결한다. 대상 repo owner가 개인 계정이든 조직 계정이든 분기 없이 균일 처리한다.

**산출물 (stdout 계약)**: 생성 연산은 이슈 번호와 URL을 stdout으로 반환한다. 호출자는 stdout을 파싱해 후속 배선(E3)에 사용한다.

**소비자**: 소비자 스킬(`flow-spec`·`flow-pr`)이 이름으로 직접 Load하도록 설계된다 — skill-registry 발견 대상이 아니다. 실제 호출 배선은 E3-S2·E3-S5 소관이다. 본 스킬은 이슈·라벨 mint 연산, sub-issue 계층 링크 연산, PR-story 링크 연산을 제공하며, 트리거 배선은 소비자 소관이다.

**제약**: 이슈는 딜리버러블 앵커일 뿐 워크플로우 상태(phase:status 등)를 담지 않는다 — 상태 저장소는 MongoDB(E4) 소유다. `gh` 미설치 또는 대상 owner 미인증 시 연산을 skip하고 수동 명령을 안내한다 (하드 실패 아님). 예외는 두 가지다 — (a) **링크 검증 실패**: §Sub-Issue Link·§PR-Story Link가 링크를 시도한 뒤 형성을 확인하지 못한 경우, (b) **의존 조회 실패로 인한 중단**: §PR-Story Link 기존 PR 경로에서 본문·base 조회가 실패해 본문을 수정하지 않고 중단한 경우. 둘 다 **비-0 exit**으로 호출자에게 보고하며, (a)는 링크를 시도했고 (b)는 시도조차 하지 않았다는 점에서 구별된다. 제목·본문 동적 문자열은 stdin(`--body-file -`)으로 전달하며 `-m "$VAR"` 보간을 금지한다 (`.tack/rules/security.md` Shell Injection Defense).

## Tier Rationale

본 컴포넌트는 5-tier 스킬 체계의 `adapter-*` tier에 속한다.

- **판별 근거**: 외부 도구(`gh` CLI)를 래핑하고, 도구 미가용 시 자체적으로 skip/fallback을 선택한다. `component-boundaries` 결정 트리에서 "외부 도구 없으면 skip/fallback을 자체 선택하는가? → 예 → `adapter-*`" 경로로 귀결된다.
- **명명**: 컴포넌트 이름은 `adapter-github-issue`로 확정한다. 이후 모든 파일 경로·참조는 이 이름을 일관되게 사용한다.
- **직접 Load되는 non-search adapter 선례**: 하네스의 `adapter-*`가 모두 skill-registry 발견 대상 search-adapter인 것은 아니다. `adapter-codex-review`(Codex CLI 래핑)와 `adapter-dependency-analysis`(knip·dependency-cruiser 래핑)는 둘 다 외부 도구를 감싸고 가용성 게이트를 가지며, skill-registry 발견이 아니라 `flow-*` 스킬이 이름으로 **직접 Load**하는 non-search adapter다. `adapter-github-issue`도 동일하게 소비자가 이름으로 직접 Load하는 non-search adapter다.

## Non-Goals

다음은 본 컴포넌트의 범위 밖이며 구현하지 않는다:

- **구버전 gh용 sub-issue fallback 경로**: `gh` < 2.94.0 환경에서 raw API 우회로 계층을 연결하는 작업. 계층 링크는 네이티브 `gh issue edit --add-sub-issue`(이슈 번호 입력) 단일 방식으로 확정했으며, gh ≥ 2.94.0 전제는 `flow-init` 부트스트랩 게이트가 검사·안내한다 (런타임 강제가 아니다 — §Availability Gate의 버전 미충족 처리 참조). 계층 링크 **연산 자체**는 범위 안이며 §Sub-Issue Link (G4)가 제공한다.
- **cross-repo PR 링크와 base branch 정책 전환**: `owner/repo#N` 형태의 다른 repo 이슈 auto-close는 closing keyword로 동작하지 않으므로 규정하지 않는다. base branch를 default branch로 전환·강제하는 정책 변경도 범위 밖이며 E3-S5 소관이다 — 본 컴포넌트는 불일치를 감지·경고까지만 수행한다. PR-story 링크 **연산 자체**는 범위 안이며 §PR-Story Link (G5)가 제공한다.
- **flow-spec/flow-pr 배선**: 소비자 스킬에 본 컴포넌트 호출을 삽입하는 작업. E3-S2·E3-S5 소관. S1은 독립 컴포넌트만 제공한다.
- **Projects 대시보드**: 폐기됨. 대시보드·상태 저장소는 MongoDB(E4) 소유다.
- **native 커스텀 Issue Types**: 폐기됨. 타입 표현은 라벨(`type:epic`·`type:story`) 단일 방식이다.
- **워크플로우 상태 저장**: 이슈에 phase:status 등 워크플로우 상태를 담지 않는다. 상태는 MongoDB 소유다.
- **기존 수동 이슈 마이그레이션·정리**: ad-hoc 생성된 기존 이슈의 재작성·정합화는 범위 밖이다.

> **Deferred to E3 (OQ4 — epic umbrella 트리거)**: umbrella 이슈를 언제·누가 mint하는가(hub가 신규 epic 감지 시 자동 vs 명시 호출)는 E3-S2 배선 시점에 확정한다. 본 컴포넌트는 mint **연산**만 제공하고 트리거 배선은 소비자 소관이다. (기록만 — S1 범위 밖)

## Operational Contract

모든 연산(라벨 부트스트랩·story 이슈·epic umbrella mint·sub-issue 계층 링크·PR-story 링크)이 공유하는 실행 계약이다. 이후 연산 섹션은 이 계약을 재정의하지 않고 "Operational Contract를 따른다"로 참조한다.

### Availability Gate

`gh` 명령을 실행하기 전에 두 조건을 확인한다:

1. `gh` CLI가 설치돼 있는가 — `command -v gh`.
2. 대상 repo에 쓰기 권한이 있는가 — `gh api repos/<owner>/<name> --jq .permissions.push`가 `true`를 반환하는가.

owner 핸들을 `gh auth status` 출력과 대조하는 방식은 사용하지 않는다. `gh auth status`는 인증된 **사용자 계정**을 나열할 뿐이고 `gh repo view --json owner`가 반환하는 org repo의 owner는 **조직 login**이므로, 이름 대조는 org repo를 (사용자가 write 권한을 가져도) 미인증으로 오판해 연산을 조용히 skip한다 — 개인/조직 균일 라우팅 목표를 훼손한다. 대신 대상 repo에 대한 실제 권한을 조회한다:

```bash
gh api repos/<owner>/<name> --jq '.permissions.push' 2>/dev/null
```

`true`면 커버로 간주하고 진행한다. `false`·빈 출력·비-0 exit(auth 오류·repo 미접근)면 커버 불충분으로 보아 skip 경로로 폴백한다. 이 검사는 owner가 개인 계정이든 조직 계정이든 동일하게 동작한다.

`GH_ISSUE_DRY_RUN=1`이면 이 게이트를 평가하기 전에 §Dry-run Contract가 우선한다 — `gh`를 호출하지 않으므로 미설치·미인증 환경에서도 조합 명령 출력이 동작한다.

둘 중 하나라도 실패하면 연산(mint·링크)을 **skip**하고 수동 명령을 안내한다. 하드 실패(비-0 exit)하지 않는다. 안내 명령의 전체 형태는 해당 연산 섹션을 따른다 (제목은 §Shell-Injection Defense의 HEREDOC 캡처 패턴 사용).

```
gh를 사용할 수 없어 연산을 건너뜁니다. 수동으로 실행하세요 (전체 명령은 각 연산 섹션 참조):
  gh label create type:epic  --repo <owner>/<name> --color 5319E7 --description "Epic anchor issue"
  gh label create type:story --repo <owner>/<name> --color 1D76DB --description "Story anchor issue"
  # story 이슈·epic umbrella: 제목을 단일따옴표 HEREDOC로 캡처한 뒤 --title "$TITLE" --body-file - 로 생성
  gh issue edit <parent> --repo <owner>/<name> --add-sub-issue <child>   # §Sub-Issue Link (G4)
  # PR-story 링크: PR 본문에 "Closes #<story-issue-number>" 라인 추가   # §PR-Story Link (G5)
```

### 버전 미충족 처리 (gh < 2.94.0)

위 두 조건은 gh **버전**을 보지 않는다. `flow-init` 게이트를 무시하고 진행한 gh < 2.94.0 환경은 설치·권한 조건을 모두 통과하지만 `gh issue edit --add-sub-issue`가 `unknown flag`로 실패한다.

§Sub-Issue Link 연산이 `unknown flag: --add-sub-issue`로 비-0 exit하면 skip으로 처리하고 exit 0으로 종료한다 — 버전 미충족은 환경 전제 결손이지 링크 형성 실패가 아니므로, §링크 후 검증의 하드 실패와 구별한다. stdout에 다음을 출력한다:

```
sub-issue 링크 skip: gh < 2.94.0 — 네이티브 sub-issue 미지원 (/flow-init 재실행으로 버전을 확인하세요)
```

이 경로는 부트스트랩 게이트가 이미 안내한 상태에 대한 잔여 방어(defense-in-depth)다.

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
- **브랜치·repo 참조 값** (`<head>`·`<base>`·`<owner>/<name>`): 명령 소스의 큰따옴표 리터럴에 직접 보간하지 않고 변수에 담아 `"$HEAD"`·`"$BASE"` 형태로 전달한다. git은 브랜치명에 백틱·`;`·`|`·`&`를 허용한다 (`git check-ref-format --branch 'a\`b\`'` 통과 — `$()`만 거부). 제목과 같은 이유로, 리터럴 보간은 값 안의 백틱을 gh 도달 전에 셸이 평가하게 만든다.

  현재 이 값들의 provenance는 하네스 자신(토픽 브랜치명)·운영자 설정(`config.git.baseBranch`)·이미 존재하는 PR의 `baseRefName`이므로 외부 공격자 경로가 없다. 위 규율은 provenance가 바뀌어도 계약이 유지되도록 두는 defense-in-depth다.
- **HEREDOC delimiter 충돌**: 단일따옴표 HEREDOC은 변수 확장·명령 치환은 막지만 **delimiter 조기 종료**는 막지 못한다. 본문·제목·story 목록 내용에 delimiter 리터럴(`BODY`·`TITLE_EOF`)과 정확히 일치하는 라인이 있으면, 그 첫 매칭 라인에서 HEREDOC이 조기 종료되고 이후 라인이 셸 명령으로 실행된다. delimiter는 고정·공개 리터럴이므로 내용에 영향을 줄 수 있는 주체가 매칭 라인을 심어 브레이크아웃할 수 있다.
  - **1차 완화 (신뢰불가 provenance 내용)**: 외부·미확인 출처 텍스트(raw issue/PR 본문, 웹훅 페이로드 등)를 본문으로 넘길 때는 HEREDOC 파이프 대신 Write 도구로 본문 바이트를 임시 파일에 쓰고 `--body-file <path>`(`-` 아님)로 전달한다. 내용이 셸 파싱에 재유입되지 않아 이 취약 클래스를 제거한다.
  - **2차 완화 (HEREDOC 유지 시)**: delimiter를 고정 리터럴 대신 호출별 nonce를 붙인 예측불가 문자열로 사용하거나, 내용에 delimiter와 정확히 일치하는 라인이 있으면 임베딩 전에 거부한다.
  - E3 소비자(E3-S2·E3-S5)가 less-trusted 텍스트를 이 어댑터로 흘리기 전에 1차 완화를 적용한다. S1 자체 흐름(spec 요약=semi-trusted)에서도 delimiter 매칭 라인 부재를 임베딩 전에 확인한다.

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

### flat 생성 (본문에 계층 링크 삽입 없음)

본문에 묶인 story id를 **텍스트로만** 나열한다. umbrella mint 연산 자체는 계층을 연결하지 **않는다** — 계층 연결은 §Sub-Issue Link (G4)의 별도 연산이 담당하며, 이 경계는 mint와 링크를 독립 호출 가능하게 유지한다.

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

story 목록의 각 항목은 사람이 읽는 텍스트 라인이다. 본문에 GitHub sub-issue 위젯 연결을 삽입하지 않는다 — 위젯에 나타나는 계층은 §Sub-Issue Link (G4) 연산이 형성한다.

> **중복 가드 이월**: story 이슈(§Story Issue Create)와 달리 epic umbrella는 재-mint 중복 가드를 두지 않는다. umbrella를 언제·누가 mint하는가(트리거)가 OQ4로 E3-S2에 이월됐으므로, 재-mint 멱등성도 트리거 배선과 함께 E3-S2에서 확정한다. 의도적 이월이며 누락이 아니다.

### stdout·dry-run

생성 성공 시 §stdout Return Convention에 따라 이슈 번호와 URL을 stdout으로 반환한다. `GH_ISSUE_DRY_RUN=1`이면 §Dry-run Contract에 따라 조합된 `gh issue create` 명령을 stdout에 출력하고 `gh`를 호출하지 않으며 exit 0으로 종료한다 — 이슈를 생성하지 않는다.

## Sub-Issue Link (G4 — 멱등·검증)

epic umbrella 이슈(parent)와 story 이슈(child)를 GitHub 네이티브 sub-issue 계층으로 연결한다. §Operational Contract(가용성 게이트·계정 라우팅·셸 인젝션 방어·dry-run)를 따르며 재정의하지 않는다. §stdout Return Convention은 생성 연산의 번호·URL 반환을 규정하므로 링크 연산에는 적용되지 않는다 — 링크 연산의 stdout 라인은 아래 §멱등성·§링크 후 검증이 정의한다.

전제는 `gh` ≥ 2.94.0이다. 이 전제는 `flow-init` 부트스트랩 게이트가 단일 지점에서 검사하므로 본 연산은 버전을 재검사하지 않는다.

### 연산

parent·child를 이슈 **번호**로 지정한다. 별도 내부 식별자 조회·변환 단계는 없다.

```bash
gh issue edit <parent> --repo <owner>/<name> --add-sub-issue <child>
```

### 입력 검증

셸에 도달하기 전에 형식을 검증한다 (§Shell-Injection Defense의 제약 식별자 방어와 같은 목적 — 백틱·`$()` 유입 차단).

- **이슈 번호** (parent·child 각각): `^[0-9]+$`에 매칭하지 않으면 연산을 **skip**한다. 하드 실패하지 않고 exit 0으로 종료한다 (skip-not-fail). skip 사유를 stdout에 한 줄로 출력해 멱등 no-op skip과 구별한다: `sub-issue 링크 skip: 이슈 번호 형식 불일치 (parent=<parent> child=<child>)`.
- **story-id를 입력으로 받는 경로**: `^E[0-9]+-S[0-9]+$` 검증을 재사용한다 (§Story Issue Create와 동일 어서션). 미매칭 시 같은 형태로 skip 사유를 출력하고 skip한다. story-id에 대응하는 이슈 번호는 §Story Issue Create 중복 가드 검색의 `number` 출력에서 얻는다.

### 번호 매칭 규율 (정확 일치)

이 규율은 이슈 번호를 번호 목록에서 찾는 모든 게이트에 적용된다 — §Sub-Issue Link의 선체크·링크 후 검증(자식 번호 목록에서 child)과 §PR-Story Link의 멱등 선체크·링크 검증(`closingIssuesReferences` 번호 목록에서 story 이슈)이 해당한다. 매칭은 **정확 일치**로 수행하고 부분 문자열 포함 검사(`grep <n>`)를 쓰지 않는다.

부분 문자열 검사는 선체크와 검증을 같은 방향으로 깨뜨린다 — `child=7`이고 기존 자식에 `37`이 있으면 선체크가 false-positive로 판정해 링크 명령을 건너뛰고, 이어지는 검증도 같은 `37`에 false-pass하므로 형성되지 않은 링크가 연결됨으로 보고된다. §Story Issue Create가 bare-prefix 매칭을 거부하는 것과 같은 이유다.

정확 일치 형태 두 가지 중 하나를 사용한다:

```bash
# (a) jq에서 판정 — true / false를 반환
gh issue view <parent> --repo <owner>/<name> --json subIssues \
  --jq 'any(.subIssues.nodes[].number == <child>; .)'

# (b) 번호 목록을 받아 전체 라인 고정 매칭
gh issue view <parent> --repo <owner>/<name> --json subIssues \
  --jq '.subIssues.nodes[].number' | grep -Fxq '<child>'
```

### 멱등성 (선체크 — skip-not-fail)

링크 **전**에 parent의 현재 자식 목록을 조회하고 §번호 매칭 규율의 정확 일치로 child가 이미 연결됐는지 확인한다.

- 정확 일치가 성립하면 `gh issue edit`를 호출하지 않고 **no-op skip**한 뒤 exit 0으로 종료한다 (skip-not-fail). 재실행이 하드 실패하지 않는다. stdout에 `sub-issue 링크 no-op: <parent> ← <child> (이미 연결됨)`을 출력해 입력 검증 skip과 구별한다.
- 성립하지 않으면 child의 **현재 부모**를 확인한다. GitHub 이슈는 부모를 하나만 가지므로, child가 다른 이슈의 자식이면 `--add-sub-issue`가 요청한 계층이 그대로 성립하지 않는다.

  ```bash
  gh issue view <child> --repo <owner>/<name> --json parent --jq '.parent.number'
  ```

  - 빈 출력(부모 없음) → §Sub-Issue Link 연산으로 진행한다.
  - `<parent>`와 다른 번호가 나오면 **skip**하고 exit 0으로 종료한다 (skip-not-fail). stdout에 `sub-issue 링크 skip: <child>가 이미 <other-parent>의 자식입니다 (parent 이동은 본 연산 범위 밖)`을 출력한다. 부모 재지정은 기존 계층을 끊는 파괴적 변경이므로 자동 수행하지 않는다.

**선체크 결과 테이블** (exhaustive):

| 선체크 결과 | 동작 | stdout | exit |
|-------------|------|--------|------|
| 이슈 번호 형식 불일치 | skip | `sub-issue 링크 skip: 이슈 번호 형식 불일치 …` | 0 |
| child가 이미 `<parent>`의 자식 | no-op skip | `sub-issue 링크 no-op: <parent> ← <child> (이미 연결됨)` | 0 |
| child가 다른 이슈의 자식 | skip | `sub-issue 링크 skip: <child>가 이미 <other-parent>의 자식입니다 …` | 0 |
| child에 부모 없음 | 링크 연산 진행 | (§링크 후 검증이 정의) | (§링크 후 검증이 정의) |

### 링크 후 검증

링크 직후 같은 조회를 재실행하고 §번호 매칭 규율의 정확 일치로 child가 자식 목록에 존재하는지 assert한다.

`subIssues`는 `nodes` 배열과 `totalCount`를 담은 객체로 반환되며 각 원소가 `number`를 직접 노출한다 (gh 2.96.0 실측, 2026-07-26). 위 jq 경로가 자식 이슈 번호를 그대로 산출한다. 역방향 확인은 child 쪽에서 `gh issue view <child> --repo <owner>/<name> --json parent --jq '.parent.number'`가 parent 번호를 반환한다.

조회 출력 구조가 이와 다르면(gh 버전 차이로 필드 shape가 변한 경우) 위 jq 경로를 그대로 쓰지 않고, 관찰된 구조에 맞춰 child 번호를 정확 일치로 매칭한다.

정확 일치가 성립하면 stdout에 `sub-issue 링크 완료: <parent> ← <child>`를 출력하고 exit 0으로 종료한다. 성립하지 않으면 링크가 형성되지 않은 것이므로 `sub-issue 링크 검증 실패: <parent> ← <child>`를 출력하고 **비-0 exit**으로 호출자에게 보고한다 — 이 경우만 하드 실패이며, 위 두 skip 경로와 종료 코드로 구별된다.

### dry-run

`GH_ISSUE_DRY_RUN=1`이면 §Dry-run Contract에 따라 조합된 `gh issue edit --add-sub-issue` 명령을 stdout에 출력하고 `gh`를 호출하지 않으며 exit 0으로 종료한다 — 계층을 연결하지 않는다. 자식 목록 선체크(`gh issue view --json subIssues`)·부모 확인(`gh issue view --json parent`)·링크 후 검증 조회도 gh 호출이므로 dry-run에서는 모두 건너뛰고 edit 명령만 출력한다.

## PR-Story Link (G5 — closing keyword)

PR을 대응 story 이슈에 GitHub closing keyword로 연결한다. PR 본문에 `Closes #<story-issue-number>` 라인을 넣으면 GitHub가 PR↔이슈 링크를 형성하고, PR 머지 시 이슈를 자동 close한다. §Operational Contract(가용성 게이트·계정 라우팅·셸 인젝션 방어·dry-run)를 따르며 재정의하지 않는다.

§stdout Return Convention은 생성 연산(story 이슈·epic umbrella)의 번호·URL 반환을 규정하므로 링크 연산에는 적용되지 않는다 — G5의 stdout 라인과 종료 코드는 아래 §링크 검증이 정의한다. `gh pr create`가 반환한 PR 번호·URL을 호출자에게 되돌리는 책임은 PR을 만드는 소비자(E3-S5)의 몫이다. 본 연산은 그 번호를 §링크 검증 입력으로 **일시 보유**하며(값 소유가 아니라 통과 사용), 본문에 넣을 closing keyword 라인과 그 검증을 소유한다.

### 연산 (같은 repo `Closes #N`)

closing keyword는 **같은 repo 구문** `Closes #<story-issue-number>`만 사용한다. cross-repo 구문(`owner/repo#N`)은 GitHub이 auto-close를 발동하지 않으므로 규정하지 않는다 (§Non-Goals).

본문은 stdin(`--body-file -`) 또는 임시 파일(`--body-file <path>`)로 전달한다 (§Shell-Injection Defense — `-m "$VAR"` 금지). 두 경로의 전달 방식이 다르며 그 근거는 각 경로에 적는다.

**신규 PR 생성 경로** — 본문이 하네스가 조립한 semi-trusted 텍스트이므로 단일따옴표 HEREDOC로 파이프한다. 제목은 §Shell-Injection Defense에 따라 단일따옴표 HEREDOC로 변수에 캡처한 뒤 `--title "$TITLE"`로 전달한다.

```bash
TITLE=$(cat <<'TITLE_EOF'
<PR 제목>
TITLE_EOF
)
gh pr create --repo <owner>/<name> --base <base> --head <head> \
  --title "$TITLE" --body-file - <<'BODY'
<PR 요약>

Closes #<story-issue-number>
BODY
```

PR 번호·URL은 `gh pr create` stdout에서 얻어 §링크 검증의 `<pr-number>` 입력으로 사용한다.

**기존 PR 추가 경로** — 기존 본문은 §Shell-Injection Defense가 "신뢰불가 provenance"로 명시한 raw PR 본문이므로 HEREDOC 파이프를 쓰지 않고 **1차 완화**를 적용한다.

**호출 트리거**: 기존 PR 경로를 실행할 때, 기존 본문을 리다이렉션으로 임시 파일에 직접 받아 `Closes #<story-issue-number>` 라인을 append한 뒤 `--body-file <path>`(`-` 아님)로 전달한다. 본문 바이트가 셸 파싱에 재유입되지 않아 delimiter 조기 종료 취약 클래스가 제거된다.

본문을 에이전트 컨텍스트로 읽어들였다가 Write 도구로 재작성하지 않는다 — 전문을 바이트 단위로 재현해야 하는데 `gh pr edit --body-file`이 교체 연산이므로, 재현 과정의 절삭·공백 변형이 그대로 PR 설명 손실이 된다. 아래 경로는 본문이 셸 변수·모델 컨텍스트 어디도 거치지 않고 파일에서 파일로 흐른다.

각 `gh` 호출을 검사하고 실패 시 **fail-closed**로 중단한다. `>` 리다이렉션은 명령이 실패해도 대상 파일을 먼저 0바이트로 truncate하므로, 조회 실패를 무시하고 진행하면 빈 파일에 `Closes #N`만 붙어 `gh pr edit`가 PR 설명 전체를 그 한 줄로 **교체**한다 — 복구 불가능한 데이터 손실이다.

```bash
TMP_BODY=$(mktemp -t gh-pr-body)   # 저장소 트리 밖 (커밋 유입 방지)
trap 'rm -f "$TMP_BODY"' EXIT      # 중단·오류 경로에서도 정리

# 1. 기존 본문을 파일로 직접 수신 (--jq가 raw 문자열을 출력 — JSON 인용 없음)
if ! gh pr view <pr-number> --repo <owner>/<name> --json body --jq '.body' > "$TMP_BODY"; then
  echo "PR-story 링크 중단: 기존 본문 조회 실패 (PR #<pr-number>) — 본문을 수정하지 않았습니다" >&2
  exit 1
fi

# 2. base 조회 (§base branch 감지 비교용 — 기존 PR은 base가 입력으로 주어지지 않는다)
if ! PR_BASE=$(gh pr view <pr-number> --repo <owner>/<name> --json baseRefName --jq '.baseRefName'); then
  echo "PR-story 링크 중단: base 조회 실패 (PR #<pr-number>) — 본문을 수정하지 않았습니다" >&2
  exit 1
fi

# 3. closing keyword append
printf '\nCloses #%s\n' "<story-issue-number>" >> "$TMP_BODY"

# 4. 파일 경로로 전달
gh pr edit <pr-number> --repo <owner>/<name> --body-file "$TMP_BODY"
```

두 조회 중 하나라도 실패하면 `gh pr edit`에 도달하지 않는다 — 본문 수정 없이 비-0 exit으로 종료한다. 이 중단은 §링크 검증의 하드 실패와 별개이며, 링크가 형성되지 않은 게 아니라 **시도조차 하지 않은** 상태다.

임시 파일은 `mktemp`로 저장소 트리 밖에 만들고 `trap ... EXIT`로 정리한다. 저장소 안에 두면 PR 본문이 `git status`에 노출되거나 커밋에 휩쓸리고, `trap` 없이 명시 `rm`만 두면 중단 경로에서 파일이 남는다.

`gh pr edit --body-file`은 본문을 **교체**한다 (append 아님 — `gh pr edit --help`의 `--body`가 "Set the new body"로 규정). 전문 재공급 없이 `Closes #N`만 넘기면 PR 설명이 소실된다. 위 1단계가 `baseRefName`을 함께 조회하는 이유는 기존 PR의 base가 입력으로 주어지지 않아 §base branch 감지 비교에 필요하기 때문이다.

### 입력 검증

- **story 이슈 번호**: `^[0-9]+$`에 매칭하지 않으면 연산을 **skip**한다. 하드 실패하지 않고 exit 0으로 종료한다 (skip-not-fail). skip 사유를 stdout에 한 줄로 출력한다: `PR-story 링크 skip: 이슈 번호 형식 불일치 (issue=<story-issue-number>)`.
- **PR 번호** (기존 PR 추가 경로): 같은 `^[0-9]+$` 검증을 적용하고 미매칭 시 같은 형태로 skip한다.

### 멱등성 (선체크 — skip-not-fail)

두 경로 모두 본문을 쓰기 **전**에 재실행 여부를 확인한다.

- **신규 PR 생성 경로**: `gh pr list --repo <owner>/<name> --head <head> --state open --json number,url`로 같은 head 브랜치의 **열린** PR을 조회한다. 결과가 있으면 `gh pr create`를 호출하지 않고 기존 PR 추가 경로로 전환한다 — `gh pr create`는 같은 head의 열린 PR이 있을 때 하드 실패하므로 선체크로 그 실패를 회피한다.

  `--state all`을 쓰지 않는다. GitHub은 이전 PR이 closed·merged된 head 브랜치에서 새 PR 생성을 허용하므로, `--state all`은 merged PR을 히트시켜 생성을 건너뛰고 **merged PR의 본문을 덮어쓰는** 경로로 잘못 전환한다 (`gh pr edit --body-file`은 교체 연산이다). §Story Issue Create가 `--state all`을 쓰는 것(162행)은 closed 이슈의 재생성 방지가 목적이라 반대 방향이며, 같은 플래그를 이 선체크로 옮기지 않는다.

- **기존 PR 추가 경로**: `gh pr view <pr-number> --repo <owner>/<name> --json closingIssuesReferences --jq '.closingIssuesReferences[].number'`를 조회하고 §번호 매칭 규율의 정확 일치로 story 이슈 번호가 이미 있으면 `gh pr edit`를 호출하지 않고 **no-op skip**한 뒤 exit 0으로 종료한다. stdout에 `PR-story 링크 no-op: PR #<pr-number> → issue #<story-issue-number> (이미 연결됨)`을 출력한다. 선체크 없이 재실행하면 `Closes #N` 라인이 본문에 중복 누적된다.

  본문 텍스트에서 `Closes #N` 라인을 찾는 방식은 쓰지 않는다. §번호 매칭 규율이 정의한 정확 일치(`grep -Fxq '<number>'`·jq 수치 `==`)는 번호 목록에 적용되는 형태라 본문 라인에 성립하지 않고, 텍스트 매칭으로 대체하면 `Closes #7`이 `Closes #70`에 false-positive를 낸다. GitHub closing keyword는 대소문자 무시이며 `Fixes`·`Resolves`·`Close`·`Fixed`·`Resolved` 변형도 링크를 형성하므로, 본문에 `Fixes #12`가 이미 있어도 `Closes #12` 텍스트 검색은 이를 놓치고 중복 keyword를 덧붙인다. `closingIssuesReferences` 조회는 keyword 변형·대소문자·표기 방식과 무관하게 **형성된 링크 자체**를 보므로 이 실패 모드가 없다.

  **2차 가드 (base != default 전용)**: base가 default branch가 아니면 `closingIssuesReferences`가 항상 빈 배열이라 위 선체크가 no-op을 판정하지 못한다. 이 상태에서 1차 선체크만 두면 재실행마다 `Closes #N`이 본문에 누적되고 매번 exit 0으로 끝나므로 멱등이 깨진다. 1차 선체크가 비었고 base != default일 때만 조회한 본문에 대해 **앵커 매칭**으로 2차 가드를 적용한다.

  **실행 시점**: 이 가드는 본문을 입력으로 받으므로 §연산 1단계(본문 조회) **뒤**, 4단계(`gh pr edit`) **앞**에 둔다. 1·2단계는 읽기 전용이므로 가드는 여전히 변경 이전(pre-mutation)에 성립한다. 1차 선체크(`closingIssuesReferences`)는 본문에 의존하지 않으므로 §연산보다 먼저 단독 실행한다.

  ```bash
  grep -Eiq '^[[:space:]]*(close[sd]?|fix(e[sd])?|resolve[sd]?)[[:space:]]+#<story-issue-number>[[:space:]]*$' "$TMP_BODY"
  ```

  라인 전체를 `^...$`로 고정하므로 `#7`이 `Closes #70`에 매칭하지 않고, 문장 중간의 우연한 언급도 잡히지 않는다. `-i`와 keyword 변형(`close`/`closes`/`closed`/`fix`/`fixes`/`fixed`/`resolve`/`resolves`/`resolved`)을 함께 다뤄 GitHub이 링크를 형성하는 표기 집합과 일치시킨다. 매칭하면 no-op skip + exit 0으로 종료하고 stdout에 `PR-story 링크 no-op: PR #<pr-number> → issue #<story-issue-number> (본문에 closing keyword 존재, base != default로 링크 미형성)`을 출력한다.

  이 2차 가드는 base == default 경로에는 적용하지 않는다 — 그 경로는 `closingIssuesReferences`가 링크 형성 여부를 직접 알려주므로 본문 텍스트를 볼 이유가 없고, 텍스트 매칭은 keyword 표기 변형에 취약한 열등한 신호다.

두 선체크와 2차 가드 모두 skip-not-fail이며, 재실행이 하드 실패하지 않는다.

### base branch 감지 (불일치 경고)

closing keyword는 PR base가 repo **default branch**일 때만 링크·auto-close를 발동한다. base가 default branch가 아니면 GitHub이 keyword를 무시한다.

`gh repo view`는 대상 repo를 **위치 인자**로 받는다 — `--repo` 플래그가 없으며 붙이면 `unknown flag: --repo`로 실패한다 (gh 2.96.0 실측). 다른 연산의 `gh issue`·`gh pr` 하위 명령이 `--repo`를 받는 것과 다르다.

```bash
gh repo view <owner>/<name> --json defaultBranchRef --jq .defaultBranchRef.name
```

조회 결과를 PR base와 비교한다. base는 신규 PR 생성 경로에서는 `--base <base>` 입력값이고, 기존 PR 추가 경로에서는 §연산 1단계가 조회한 `baseRefName`이다.

- 일치하면 그대로 진행한다.
- 불일치하면 stdout에 경고를 출력하고 진행한다: `PR-story 링크 경고: base=<base>가 default branch=<default>와 달라 closing keyword가 무시됩니다 (링크·auto-close 미형성)`.
- 조회가 빈 출력·비-0 exit으로 실패하면 default branch를 알 수 없으므로 base 비교를 수행하지 않는다. 이때는 §링크 검증의 `base == default` 행(하드 실패 가능 경로)을 적용하지 않고 `PR-story 링크 경고: default branch 조회 실패 — base 비교를 건너뜁니다`를 출력한 뒤 exit 0으로 종료한다. 조회 실패를 불일치로 오판하면 `base == default`인 정상 PR이 매번 경고를 받고 검증 실패 행이 도달 불가가 된다.

감지·경고까지만 수행한다. base branch를 default branch로 전환하거나 정책을 변경하지 않는다 (§Non-Goals — E3-S5 소관).

### 링크 검증

PR 본문 전달 직후 링크 형성 여부를 조회한다.

```bash
gh pr view <pr-number> --repo <owner>/<name> --json closingIssuesReferences \
  --jq '.closingIssuesReferences[].number'
```

번호 매칭은 §번호 매칭 규율 (정확 일치)를 따른다 — `grep -Fxq '<story-issue-number>'` 또는 jq `any(.closingIssuesReferences[].number == <story-issue-number>; .)`. 부분 문자열 검사(`grep <n>`)는 이슈 `#7`이 `#37`에 false-pass하므로 쓰지 않는다.

판정은 base branch 상태에 따라 갈린다:

| base 상태 | `closingIssuesReferences` | 판정 | stdout | exit |
|-----------|---------------------------|------|--------|------|
| base == default | story 번호 정확 일치 | 성공 | `PR-story 링크 완료: PR #<pr-number> → issue #<story-issue-number>` | 0 |
| base == default | story 번호 부재 (빈 배열 포함) | **검증 실패** | `PR-story 링크 검증 실패: PR #<pr-number> → issue #<story-issue-number>` | **비-0** |
| base != default | 빈 배열 | **정상** (경고만) | `PR-story 링크 미형성(정상): base=<base>가 default branch가 아닙니다` | 0 |
| base != default | story 번호 정확 일치 | 성공 | `PR-story 링크 완료: PR #<pr-number> → issue #<story-issue-number>` | 0 |

4행(`base != default` + 정확 일치)은 도달 가능하다 — PR 사이드바 "Development"에서 수동 연결한 이슈는 base와 무관하게 `closingIssuesReferences`에 나타난다. closing keyword가 non-default base에서 동작한다는 뜻이 아니며, 본문 keyword 외 경로로 링크가 이미 형성된 상태다.

`base != default`에서 빈 배열은 **정상 상태**다 — GitHub이 keyword를 무시한 예상된 결과이므로 하드 실패하지 않는다. 입력 검증 skip·멱등 no-op·base 불일치 경고는 모두 exit 0이다.

G5의 비-0 exit은 두 가지뿐이다:

| 비-0 exit | 시점 | 본문 상태 |
|-----------|------|-----------|
| 링크 검증 실패 (`base == default` + 번호 부재) | 본문 전달 **후** | 수정됨 — `Closes #N`이 들어갔으나 링크가 형성되지 않음 |
| 의존 조회 실패 중단 (§연산 1·2단계) | 본문 전달 **전** | 미수정 — `gh pr edit`에 도달하지 않음 |

호출자는 이 둘을 stdout 라인으로 구별한다 (`PR-story 링크 검증 실패:` vs `PR-story 링크 중단:`). §Sub-Issue Link는 링크 검증 실패 한 가지만 비-0 exit이며, 나머지 skip 경로는 모두 exit 0이다.

### dry-run

`GH_ISSUE_DRY_RUN=1`이면 §Dry-run Contract에 따라 조합된 `gh pr create` 또는 `gh pr edit` 명령과 본문에 삽입될 `Closes #<story-issue-number>` 라인을 stdout에 출력하고 `gh`를 호출하지 않으며 exit 0으로 종료한다 — PR을 만들거나 수정하지 않는다. 아래 조회도 모두 gh 호출이므로 dry-run에서는 건너뛴다:

- 열린 PR 선체크 (`gh pr list --head <head> --state open`)
- 멱등 선체크·링크 검증 조회 (`gh pr view --json closingIssuesReferences`)
- 기존 본문 조회 (`gh pr view --json body`)·base 조회 (`gh pr view --json baseRefName`)
- default branch 조회 (`gh repo view <owner>/<name> --json defaultBranchRef`)

임시 파일 생성(`mktemp`)·append·삭제도 수행하지 않는다 — 본문 전달 자체가 일어나지 않기 때문이다.

따라서 dry-run에서는 멱등 선체크(1차·2차)·base 비교·링크 검증이 모두 평가되지 않는다 — 불일치 경고와 위 §링크 검증 판정 표는 dry-run에서 도달하지 않는다. 의존 조회를 하지 않으므로 §연산의 조회 실패 중단(비-0 exit)도 도달하지 않는다. dry-run은 §Dry-run Contract대로 항상 exit 0이며, 출력은 조합 명령과 `Closes #N` 라인에 한정된다.

## Standalone Verification (G6 — 무오염 dry-run)

소비자(E3) 배선 없이 컴포넌트를 독립 검증한다. 검증은 `GH_ISSUE_DRY_RUN=1` 하에서만 수행하며, §Dry-run Contract가 gh 미호출(zero gh calls)을 보장하므로 대상 repo(예: `smalljiny/tack`)를 오염시키지 않는다 — 무오염은 실행이 아니라 **구조적으로** 성립한다.

### 검증 절차

G6 검증은 두 확인 행위로 구성되며 서로 다른 주체가 수행한다:

- **(a) dry-run 출력 확인** — 계약을 실행하는 에이전트/소비자가 `GH_ISSUE_DRY_RUN=1` 하에서 다섯 연산의 bash를 해석·echo해 조합된 gh 명령이 stdout에 나오는지 확인한다. 본 컴포넌트는 실행 코드 없는 프롬프트 문서이므로 `GH_ISSUE_DRY_RUN`을 읽는 러너가 별도로 존재하지 않는다 — 라이브 dry-run 실행은 소비자(E3)가 컴포넌트를 구동할 때 일어난다.
- **(b) 무오염 보장** — §Dry-run Contract의 zero gh calls로 **구조적으로** 성립하며, 실 repo 조회·생성 없이 계약 텍스트의 정적 점검(reasoning)으로 확인한다. S1의 코드 없는 범위에서 G6은 이 구조적·정적 확인이다.

**검증 가능성의 비대칭**: 링크 형성 자체를 실측할 수 있는 범위는 두 링크 연산에서 다르다. §Sub-Issue Link (G4)는 읽기 전용 `gh issue view --json subIssues` 조회로 기존 계층의 필드 shape와 매칭 결과를 repo 오염 없이 실측할 수 있다. §PR-Story Link (G5)는 그렇지 않다 — 링크·auto-close는 default branch를 base로 하는 실 PR을 만들어야 발동하므로 무오염 조건에서 라이브 검증이 **불가**하다. 따라서 G5는 조합된 `gh pr create`/`gh pr edit`/`gh pr view --json closingIssuesReferences` 명령 형태와 base≠default 분기 계약 텍스트의 **정적 계약 점검**으로 성립시킨다. default-base 임시 PR을 만들어 auto-close를 확인하는 절차는 수행하지 않는다.

다섯 연산을 `GH_ISSUE_DRY_RUN=1`로 해석했을 때 stdout에 조합된 gh 명령이 출력되는지 확인한다:

1. **라벨 부트스트랩** (§Label Bootstrap) — dry-run 시 두 `gh label create` 명령(`type:epic`·`type:story`)이 출력되고 라벨은 생성되지 않는다.
2. **story 이슈** (§Story Issue Create) — dry-run 시 조합된 `gh issue create --label type:story` 명령이 출력되고 이슈·중복 검색(`gh issue list`) 모두 gh를 호출하지 않는다.
3. **epic umbrella** (§Epic Umbrella Mint) — dry-run 시 조합된 `gh issue create --label type:epic` 명령이 출력되고 이슈는 생성되지 않는다.
4. **sub-issue 계층 링크** (§Sub-Issue Link) — dry-run 시 조합된 `gh issue edit <parent> --add-sub-issue <child>` 명령이 출력되고, 선체크·링크 후 검증 조회(`gh issue view`)를 포함해 gh를 전혀 호출하지 않으며 계층이 연결되지 않는다.
5. **PR-story 링크** (§PR-Story Link) — dry-run 시 조합된 `gh pr create` 또는 `gh pr edit` 명령과 `Closes #<story-issue-number>` 라인이 출력되고, 열린 PR 선체크(`gh pr list --head <head> --state open`)·멱등 선체크·링크 검증 조회(`gh pr view --json closingIssuesReferences`)·기존 본문 조회(`gh pr view --json body`)·base 조회(`gh pr view --json baseRefName`)·default branch 조회(`gh repo view <owner>/<name> --json defaultBranchRef`)를 포함해 gh를 전혀 호출하지 않으며 PR이 생성·수정되지 않는다. 임시 파일도 만들지 않고, base 비교가 일어나지 않으므로 불일치 경고도 출력되지 않는다.

### 무오염 확인

다섯 연산 모두 dry-run에서 gh를 호출하지 않으므로(§Dry-run Contract) 대상 repo에 실 이슈·라벨·계층·PR이 생성되지 않는다. 이 성질은 gh 미호출로 구조적으로 보장되며, 실 repo에 대한 조회·생성 없이 계약 텍스트의 정적 점검으로 확인한다. 실 이슈·라벨·PR을 만들지 않는 것이 검증의 전제이므로 검증 자체가 repo를 변경하지 않는다.
