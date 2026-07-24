# GitHub 이슈 앵커 (adapter-github-issue)

> `gh` CLI를 감싸 epic·story를 GitHub 이슈로 프로그램적으로 mint하는 외부-도구 어댑터. 이슈는 딜리버러블 앵커일 뿐 워크플로우 상태를 담지 않는다.

## 개요

`adapter-github-issue`는 tack 하네스가 배포하는 스킬(`template/.claude/skills/adapter-github-issue/SKILL.md`)로, epic·story를 GitHub 이슈로 앵커링하는 mint 연산을 정의한다. 컴포넌트는 실행 코드 없는 단일 프롬프트 문서이며, 소비자(LLM·에이전트)가 문서의 bash 패턴을 해석해 실행한다.

세 mint 연산을 제공한다 — `type:epic`·`type:story` 라벨 멱등 부트스트랩, story 이슈 생성, epic umbrella 이슈 flat mint. 대상 repo owner가 개인 계정이든 조직 계정이든 분기 없이 균일 처리하며, `gh` 미설치·대상 owner 미인증 시 mint를 skip하고 수동 명령을 안내한다(하드 실패 아님).

**tier**: 외부 도구(`gh`)를 래핑하고 미가용 시 자체 skip/fallback을 선택하므로 5-tier 체계의 `adapter-*`다. 하네스의 여느 `adapter-*`(search-adapter)와 달리 skill-registry 발견 대상이 아니라 소비자 스킬이 이름으로 직접 Load하는 non-search adapter다 — `adapter-codex-review`·`adapter-dependency-analysis`와 같은 선례를 따른다.

**소비자와 경계**: 실제 호출 배선은 소비자 스킬(`flow-spec`·`flow-pr`)이 수행하며 E3-S2·E3-S5 소관이다. 본 컴포넌트는 mint 연산만 제공한다. 이슈는 앵커 역할만 하며 phase:status 등 워크플로우 상태 저장소는 MongoDB(E4)가 소유한다.

## 구조 / 스키마

```
template/.claude/skills/adapter-github-issue/
└── SKILL.md        # 운영 계약 + 세 mint 연산 + standalone 검증
```

### 연산과 gh 명령

| 연산 | gh 명령 | 라벨 | 반환 |
|------|---------|------|------|
| 라벨 부트스트랩 | `gh label create type:epic` / `type:story` | — | (멱등 no-op) |
| story 이슈 생성 | `gh issue create --label type:story` | `type:story` | 이슈 번호·URL (stdout) |
| epic umbrella | `gh issue create --label type:epic` | `type:epic` | 이슈 번호·URL (stdout) |

### 라벨 스키마

| 라벨 | color | description |
|------|-------|-------------|
| `type:epic` | `5319E7` | Epic anchor issue |
| `type:story` | `1D76DB` | Story anchor issue |

## 동작

### 운영 계약 (공유)

세 연산이 공유하는 실행 계약이다. 각 연산 섹션은 이를 재정의하지 않고 참조한다.

- **가용성 게이트**: `gh` 실행 전 두 조건을 확인한다 — (1) `command -v gh`로 설치 확인, (2) `gh api repos/<owner>/<name> --jq .permissions.push`가 `true`를 반환하는지로 대상 repo write 권한 확인. 권한 조회는 owner 핸들을 `gh auth status` 출력과 대조하지 않는다 — `gh auth status`는 인증된 사용자 계정만 나열하므로, 조직 repo owner(조직 login)와 이름 대조 시 사용자가 write 권한을 가져도 미인증으로 오판한다. 실제 권한 조회는 개인·조직 owner에서 동일하게 동작한다. `true`면 진행, `false`·빈 출력·비-0 exit면 skip 경로로 폴백한다.
- **계정 라우팅**: 라벨이 개인·조직 repo에서 균일 동작하므로 타입 표현에 owner별 분기가 없다. owner는 `gh repo view --json owner`로 감지하며 특정 핸들을 하드코딩하지 않는다. 모든 연산은 `--repo <owner>/<name>`를 명시하거나 현재 repo 컨텍스트로 해석한다.
- **셸 인젝션 방어**: 이슈 제목·본문 동적 문자열을 셸 인자로 보간하지 않는다. 본문은 `--body-file -`로 stdin 전달하고, 여러 줄 본문은 단일따옴표 HEREDOC(`<<'BODY'`)으로 파이프해 변수 확장·명령 치환을 비활성화한다. 제목은 단일따옴표 HEREDOC로 변수에 캡처한 뒤 `--title "$TITLE"`로 전달한다. 신뢰불가 텍스트를 명령 소스의 큰따옴표 리터럴에 직접 보간하는 패턴과 `-m "$VAR"` 인라인 패턴은 금지한다. 본문·제목에 HEREDOC delimiter 리터럴과 정확히 일치하는 라인이 있으면 조기 종료로 이후 라인이 셸 명령으로 실행되므로, 신뢰불가 provenance 내용은 Write로 임시 파일에 써 `--body-file <path>`로 전달한다.
- **dry-run**: `GH_ISSUE_DRY_RUN=1`이면 모든 연산이 echo-not-execute로 동작한다 — 조합된 `gh` 명령을 stdout에 출력하고 `gh`를 전혀 호출하지 않으며 exit 0으로 종료한다. dry-run은 가용성 게이트에 우선하므로 `gh` 미설치·미인증 환경에서도 성립한다.
- **stdout 규약**: 생성 연산(story·epic)은 성공 시 이슈 번호와 URL을 stdout으로 반환한다. 호출자는 이를 파싱해 후속 배선에 사용한다.

### 라벨 부트스트랩

`type:epic`·`type:story` 두 라벨을 대상 repo에 생성한다. 멱등성은 `gh label list` 선체크(없는 라벨만 생성) 또는 `gh label create ... 2>/dev/null || true`(exists-error tolerate)로 보장한다. 선체크가 auth·network 실 오류를 함께 흡수하지 않으므로 우선한다. 재실행 시 두 라벨이 모두 존재하면 no-op이며, 수동 생성분과 충돌하지 않는다.

### story 이슈 생성 (중복 가드 포함)

`type:story` 라벨을 단 이슈를 생성한다. 제목은 `<story-id> — <요약>`, 본문은 spec 요약과 링크다.

중복 가드는 컴포넌트가 소유한다. 생성 전 story-id 형식을 `^E[0-9]+-S[0-9]+$`로 검증하고(위험 문자 유입 차단), `gh issue list --search "<story-id> in:title" --label type:story --state all`로 기존 이슈를 검색한다. GitHub 검색의 하이픈 토크나이즈로 fuzzy 매칭되므로 결과를 title로 post-filter한다 — 제목이 `<story-id> —`(구분자 포함)로 정확히 시작하는 이슈만 중복으로 판정한다(`E5-S1`이 `E5-S10`을 오탐하지 않음). 중복이면 생성을 skip하고 기존 이슈 번호·URL을 stdout에 출력한 뒤 exit 0으로 종료한다(skip-not-fail). `--state all`로 closed 이슈까지 감지한다.

### epic umbrella mint

`type:epic` 라벨을 단 flat umbrella 이슈를 생성한다. 본문에 epic 요약과 묶인 story 목록을 기술하되, story는 사람이 읽는 텍스트 라인으로만 나열하고 GraphQL node ID·sub-issue 계층 링크는 포함하지 않는다. epic umbrella는 story 이슈와 달리 재-mint 중복 가드를 두지 않는다 — umbrella 트리거 배선이 E3-S2 소관이므로 재-mint 멱등성도 그 시점에 확정한다.

### standalone 검증

소비자(E3) 배선 없이 컴포넌트를 독립 검증한다. 검증은 `GH_ISSUE_DRY_RUN=1` 하에서만 수행하며, dry-run 계약의 zero gh calls가 대상 repo 무오염을 구조적으로 보장한다. 세 연산(라벨·story·epic)을 dry-run으로 해석했을 때 조합된 gh 명령이 stdout에 출력되고 실 이슈·라벨이 생성되지 않음을 확인한다. 컴포넌트가 실행 코드 없는 프롬프트 문서이므로 라이브 dry-run 실행은 소비자가 컴포넌트를 구동할 때 일어나고, S1 범위에서 G6은 계약 텍스트의 정적 점검으로 성립한다.

## 제약사항

- **앵커 전용** — 이슈는 딜리버러블 앵커이며 워크플로우 상태(phase:status 등)를 담지 않는다. 상태 저장소는 MongoDB(E4)가 소유한다.
- **flat 생성까지** — epic umbrella 아래 story를 계층 연결하는 sub-issue 링크(GraphQL node ID)는 범위 밖이다(E5-S2).
- **PR 링크 없음** — PR을 story 이슈에 연결하는 작업은 범위 밖이다(E5-S3).
- **배선 없음** — 소비자 스킬(`flow-spec`·`flow-pr`)에 호출을 삽입하는 배선은 범위 밖이다(E3-S2·E3-S5). 본 컴포넌트는 독립 연산만 제공한다.
- **라벨 단일 타입 표현** — native 커스텀 Issue Types와 Projects 대시보드는 채택하지 않는다. 타입은 라벨(`type:epic`·`type:story`)로만 표현하고 대시보드는 MongoDB가 소유한다.
- **기존 이슈 불간섭** — ad-hoc 생성된 기존 수동 이슈의 재작성·정합화는 범위 밖이다.
- **canonical 규칙 우선** — 셸 방어의 강제 규칙은 `template/.tack/rules/security.md` Shell Injection Defense가, tier 판별은 `template/.claude/rules/common/component-boundaries.md`가 소유한다. 충돌 시 규칙이 우선한다.
