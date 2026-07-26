# GitHub 이슈 앵커 (adapter-github-issue)

> `gh` CLI를 감싸 epic·story를 GitHub 이슈로 mint하고, epic↔story 계층과 PR↔story 링크를 연결하는 외부-도구 어댑터. 이슈는 딜리버러블 앵커일 뿐 워크플로우 상태를 담지 않는다.

## 개요

`adapter-github-issue`는 tack 하네스가 배포하는 스킬(`template/.claude/skills/adapter-github-issue/SKILL.md`)로, epic·story를 GitHub 이슈로 앵커링하고 그 사이의 관계를 연결하는 연산을 정의한다. 컴포넌트는 실행 코드 없는 단일 프롬프트 문서이며, 소비자(LLM·에이전트)가 문서의 bash 패턴을 해석해 실행한다.

다섯 연산을 제공한다 — `type:epic`·`type:story` 라벨 멱등 부트스트랩, story 이슈 생성, epic umbrella 이슈 flat mint, epic↔story sub-issue 계층 링크, PR↔story closing-keyword 링크. 대상 repo owner가 개인 계정이든 조직 계정이든 분기 없이 균일 처리하며, `gh` 미설치·대상 owner 미인증 시 연산을 skip하고 수동 명령을 안내한다(하드 실패 아님).

**tier**: 외부 도구(`gh`)를 래핑하고 미가용 시 자체 skip/fallback을 선택하므로 5-tier 체계의 `adapter-*`다. 하네스의 여느 `adapter-*`(search-adapter)와 달리 skill-registry 발견 대상이 아니라 소비자 스킬이 이름으로 직접 Load하는 non-search adapter다 — `adapter-codex-review`·`adapter-dependency-analysis`와 같은 선례를 따른다.

**소비자와 경계**: 실제 호출 배선은 소비자 스킬(`flow-spec`·`flow-pr`)이 수행하며 E3-S2·E3-S5 소관이다. 본 컴포넌트는 연산만 제공한다. 이슈는 앵커 역할만 하며 phase:status 등 워크플로우 상태 저장소는 MongoDB(E4)가 소유한다.

**전제조건**: sub-issue 계층 링크는 네이티브 `gh issue edit --add-sub-issue`를 사용하므로 `gh` ≥ 2.94.0을 요구한다. 이 전제는 `flow-init` 부트스트랩 게이트가 단일 지점에서 검사·안내하며(`config.gh.*` 기록 + 미충족 시 미완료 종료), 어댑터는 연산 시점에 버전을 재검사하지 않는다. 게이트를 무시하고 진행한 환경에 대한 잔여 방어는 §제약사항 참조.

## 구조 / 스키마

```
template/.claude/skills/adapter-github-issue/
└── SKILL.md        # 운영 계약 + 다섯 연산 + standalone 검증
```

### 연산과 gh 명령

| 연산 | 섹션 라벨 | gh 명령 | 반환·종료 |
|------|----------|---------|----------|
| 라벨 부트스트랩 | G1 | `gh label create type:epic` / `type:story` | (멱등 no-op) |
| story 이슈 생성 | G2 | `gh issue create --label type:story` | 이슈 번호·URL (stdout) |
| epic umbrella | G3 | `gh issue create --label type:epic` | 이슈 번호·URL (stdout) |
| sub-issue 계층 링크 | G4 | `gh issue edit <parent> --add-sub-issue <child>` | 링크 결과 라인. 검증 실패 시 비-0 exit |
| PR-story 링크 | G5 | `gh pr create` / `gh pr edit --body-file` + `Closes #N` | 링크 결과 라인. 검증 실패·조회 실패 시 비-0 exit |

파일 내부 섹션 라벨은 G1~G6 수열을 쓰며 G6은 standalone 검증이다.

### 라벨 스키마

| 라벨 | color | description |
|------|-------|-------------|
| `type:epic` | `5319E7` | Epic anchor issue |
| `type:story` | `1D76DB` | Story anchor issue |

### gh 전제조건 캐시 (`config.gh.*`)

`flow-init`이 부트스트랩 시점에 기록하는 진단 필드다. 어댑터는 이 값을 읽지 않는다 — 소비 배선은 E3 소관이다.

| 필드 | 값 타입 | 의미 |
|------|---------|------|
| `config.gh.available` | bool-as-string | `command -v gh` 성공 여부 |
| `config.gh.native_subissue` | bool-as-string | 파싱된 버전이 2.94.0 이상인지 |
| `config.gh.version` | semver 문자열 또는 빈 문자열 | `gh --version` 첫 줄에서 파싱한 `X.Y.Z` |
| `config.gh.checked_at` | ISO8601 문자열 | 감지 시각 (마지막에 기록 — 부분 실패 판별용) |

값은 `dev_context.py`의 `coerce_config_value`가 `true`/`false` 리터럴을 JSON boolean으로 변환해 저장하고, `read`가 다시 문자열로 출력한다. 소비자는 `read` 출력을 문자열 비교하는 `config.codex.*` 선례를 따른다.

## 동작

### 운영 계약 (공유)

다섯 연산이 공유하는 실행 계약이다. 각 연산 섹션은 이를 재정의하지 않고 참조한다.

- **가용성 게이트**: `gh` 실행 전 두 조건을 확인한다 — (1) `command -v gh`로 설치 확인, (2) `gh api repos/<owner>/<name> --jq .permissions.push`가 `true`를 반환하는지로 대상 repo write 권한 확인. 권한 조회는 owner 핸들을 `gh auth status` 출력과 대조하지 않는다 — `gh auth status`는 인증된 사용자 계정만 나열하므로, 조직 repo owner(조직 login)와 이름 대조 시 사용자가 write 권한을 가져도 미인증으로 오판한다. 실제 권한 조회는 개인·조직 owner에서 동일하게 동작한다. `true`면 진행, `false`·빈 출력·비-0 exit면 skip 경로로 폴백한다. 이 게이트는 gh **버전**을 보지 않는다.
- **계정 라우팅**: 라벨이 개인·조직 repo에서 균일 동작하므로 타입 표현에 owner별 분기가 없다. owner는 `gh repo view --json owner`로 감지하며 특정 핸들을 하드코딩하지 않는다. 모든 연산은 `--repo <owner>/<name>`를 명시하거나 현재 repo 컨텍스트로 해석한다. 단 `gh repo view`는 대상 repo를 **위치 인자**로 받는다 — `--repo` 플래그가 없으며 붙이면 `unknown flag`로 실패한다.
- **셸 인젝션 방어**: 이슈 제목·본문 동적 문자열을 셸 인자로 보간하지 않는다. 본문은 `--body-file -`로 stdin 전달하고, 여러 줄 본문은 단일따옴표 HEREDOC(`<<'BODY'`)으로 파이프해 변수 확장·명령 치환을 비활성화한다. 제목은 단일따옴표 HEREDOC로 변수에 캡처한 뒤 `--title "$TITLE"`로 전달한다. 신뢰불가 텍스트를 명령 소스의 큰따옴표 리터럴에 직접 보간하는 패턴과 `-m "$VAR"` 인라인 패턴은 금지한다. 본문·제목에 HEREDOC delimiter 리터럴과 정확히 일치하는 라인이 있으면 조기 종료로 이후 라인이 셸 명령으로 실행되므로, 신뢰불가 provenance 내용은 파일로 받아 `--body-file <path>`로 전달한다. 브랜치·repo 참조 값(`<head>`·`<base>`·`<owner>/<name>`)도 리터럴 보간 대신 변수로 전달한다 — git은 브랜치명에 백틱·`;`·`|`·`&`를 허용한다.
- **번호 매칭 규율**: 이슈 번호를 번호 목록에서 찾는 모든 게이트는 **정확 일치**로 판정하고 부분 문자열 검사를 쓰지 않는다. `grep -Fxq '<number>'` 또는 jq 수치 `==`를 사용한다. 부분 문자열 검사는 선체크와 검증을 같은 방향으로 깨뜨린다 — `child=7`이고 기존 자식에 `37`이 있으면 선체크가 false-positive로 링크를 건너뛰고 검증도 같은 `37`에 false-pass해, 형성되지 않은 링크가 연결됨으로 보고된다.
- **dry-run**: `GH_ISSUE_DRY_RUN=1`이면 모든 연산이 echo-not-execute로 동작한다 — 조합된 `gh` 명령을 stdout에 출력하고 `gh`를 전혀 호출하지 않으며 exit 0으로 종료한다. 선체크·검증 조회도 gh 호출이므로 함께 건너뛴다. dry-run은 가용성 게이트에 우선하므로 `gh` 미설치·미인증 환경에서도 성립한다.
- **stdout 규약**: 생성 연산(story·epic)은 성공 시 이슈 번호와 URL을 stdout으로 반환한다. 링크 연산(G4·G5)은 이 규약 대상이 아니며 각자 링크 결과 라인과 종료 코드를 정의한다.

### 라벨 부트스트랩 (G1)

`type:epic`·`type:story` 두 라벨을 대상 repo에 생성한다. 멱등성은 `gh label list` 선체크(없는 라벨만 생성) 또는 `gh label create ... 2>/dev/null || true`(exists-error tolerate)로 보장한다. 선체크가 auth·network 실 오류를 함께 흡수하지 않으므로 우선한다. 재실행 시 두 라벨이 모두 존재하면 no-op이며, 수동 생성분과 충돌하지 않는다.

### story 이슈 생성 (G2 — 중복 가드 포함)

`type:story` 라벨을 단 이슈를 생성한다. 제목은 `<story-id> — <요약>`, 본문은 spec 요약과 링크다.

중복 가드는 컴포넌트가 소유한다. 생성 전 story-id 형식을 `^E[0-9]+-S[0-9]+$`로 검증하고(위험 문자 유입 차단), `gh issue list --search "<story-id> in:title" --label type:story --state all`로 기존 이슈를 검색한다. GitHub 검색의 하이픈 토크나이즈로 fuzzy 매칭되므로 결과를 title로 post-filter한다 — 제목이 `<story-id> —`(구분자 포함)로 정확히 시작하는 이슈만 중복으로 판정한다(`E5-S1`이 `E5-S10`을 오탐하지 않음). 중복이면 생성을 skip하고 기존 이슈 번호·URL을 stdout에 출력한 뒤 exit 0으로 종료한다(skip-not-fail). `--state all`로 closed 이슈까지 감지한다.

### epic umbrella mint (G3 — flat)

`type:epic` 라벨을 단 flat umbrella 이슈를 생성한다. 본문에 epic 요약과 묶인 story 목록을 기술하되, story는 사람이 읽는 텍스트 라인으로만 나열하고 본문에 계층 위젯 연결을 삽입하지 않는다 — 위젯에 나타나는 계층은 §sub-issue 계층 링크(G4)의 별도 연산이 형성한다. mint와 링크를 독립 호출 가능하게 유지하는 경계다. epic umbrella는 story 이슈와 달리 재-mint 중복 가드를 두지 않는다 — umbrella 트리거 배선이 E3-S2 소관이므로 재-mint 멱등성도 그 시점에 확정한다.

### sub-issue 계층 링크 (G4 — 멱등·검증)

epic umbrella(parent)와 story 이슈(child)를 GitHub 네이티브 sub-issue 계층으로 연결한다. 이슈 **번호**로 지정하며 내부 식별자 조회·변환 단계가 없다.

```
gh issue edit <parent> --repo <owner>/<name> --add-sub-issue <child>
```

**입력 검증**: parent·child 번호가 `^[0-9]+$`에 매칭하지 않으면 skip한다(exit 0). story-id를 입력으로 받는 경로는 `^E[0-9]+-S[0-9]+$` 검증을 재사용한다.

**선체크**: 네 가지 결과를 갖는 exhaustive 게이트다 — 번호 형식 불일치 → skip, child가 이미 `<parent>`의 자식 → no-op skip, child가 **다른** 이슈의 자식 → skip(GitHub 이슈는 부모를 하나만 가지므로 재지정은 기존 계층을 끊는 파괴적 변경이며 자동 수행하지 않는다), 부모 없음 → 링크 진행. 셋 다 exit 0이다.

**링크 후 검증**: 같은 조회를 재실행해 child가 자식 목록에 있는지 정확 일치로 assert한다. `subIssues`는 `nodes` 배열과 `totalCount`를 담은 객체로 반환되며 각 원소가 `number`를 직접 노출한다(gh 2.96.0 실측). 역방향은 `gh issue view <child> --json parent --jq '.parent.number'`가 parent 번호를 반환한다. 정확 일치가 성립하지 않으면 링크가 형성되지 않은 것이므로 **비-0 exit**으로 보고한다 — G4에서 하드 실패는 이 한 가지이며, 위 skip 경로들과 종료 코드로 구별된다.

### PR-story 링크 (G5 — closing keyword)

PR 본문에 `Closes #<story-issue-number>` 라인을 넣어 PR↔이슈 링크를 형성한다. GitHub에 명시적 링크 API가 없어 closing keyword가 유일한 프로그램적 수단이다. **같은 repo 구문만** 사용한다 — cross-repo `owner/repo#N`은 auto-close를 발동하지 않는다.

**신규 PR 경로**: `gh pr create --body-file -`에 단일따옴표 HEREDOC로 본문을 파이프한다(하네스가 조립한 semi-trusted 텍스트). 같은 head의 열린 PR을 `gh pr list --head <head> --state open`으로 선체크해 중복 생성 실패를 회피한다. `--state all`을 쓰지 않는다 — GitHub은 이전 PR이 closed·merged된 head에서 새 PR 생성을 허용하므로, merged PR을 히트시켜 그 본문을 덮어쓰는 경로로 잘못 전환된다.

**기존 PR 경로**: 기존 본문은 신뢰불가 provenance(fork PR 본문은 공격자 저작)이므로 HEREDOC 파이프를 쓰지 않는다. 본문을 리다이렉션으로 임시 파일에 직접 받아 keyword 라인을 append한 뒤 `--body-file <path>`로 전달한다 — 본문 바이트가 셸 파싱에 재유입되지 않는다. 임시 파일은 `mktemp`로 저장소 트리 밖에 만들고 `trap ... EXIT`로 정리한다.

`gh pr edit --body-file`은 본문을 **교체**한다(append 아님). 두 선행 조회(`--json body`, `--json baseRefName`)를 각각 검사하고 실패 시 본문을 수정하지 않고 비-0 exit으로 중단한다 — `>` 리다이렉션은 명령이 실패해도 대상 파일을 먼저 truncate하므로, 미검사 진행은 PR 설명을 keyword 한 줄로 교체하는 데이터 손실을 낳는다.

**base branch 감지**: closing keyword는 PR base가 repo default branch일 때만 링크·auto-close를 발동한다. `gh repo view <owner>/<name> --json defaultBranchRef`로 default를 조회해 base와 비교하고, 불일치 시 경고를 출력하되 진행한다. base 정책 전환은 하지 않는다(E3-S5 소관). 조회 자체가 실패하면 비교를 건너뛰고 exit 0으로 종료한다 — 조회 실패를 불일치로 오판하면 정상 PR이 매번 경고를 받고 검증 실패 경로가 도달 불가가 된다.

**멱등성**: 1차로 `closingIssuesReferences` 번호 목록을 정확 일치 검사한다. 본문 텍스트에서 `Closes #N`을 찾지 않는다 — GitHub closing keyword는 대소문자 무시이며 `Fixes`·`Resolves` 변형도 링크를 형성하므로 텍스트 검색은 변형을 놓치고 중복을 덧붙인다. base != default에서는 이 목록이 항상 비어 1차 선체크가 무력하므로, 본문에 대한 앵커 매칭(`^\s*(close[sd]?|fix(e[sd])?|resolve[sd]?)\s+#N\s*$`, 대소문자 무시) 2차 가드로 keyword 누적을 막는다.

**링크 검증**: `gh pr view <n> --json closingIssuesReferences --jq '.closingIssuesReferences[].number'`를 조회해 정확 일치로 판정한다.

| base 상태 | `closingIssuesReferences` | 판정 | exit |
|-----------|---------------------------|------|------|
| base == default | story 번호 정확 일치 | 성공 | 0 |
| base == default | 번호 부재 (빈 배열 포함) | 검증 실패 | 비-0 |
| base != default | 빈 배열 | 정상 (경고만) | 0 |
| base != default | story 번호 정확 일치 | 성공 | 0 |

4행은 도달 가능하다 — PR 사이드바 "Development"로 수동 연결한 이슈는 base와 무관하게 목록에 나타난다. closing keyword가 non-default base에서 동작한다는 뜻이 아니다.

G5의 비-0 exit은 두 가지다 — 링크 검증 실패(본문 수정됨, 링크 미형성)와 의존 조회 실패 중단(본문 미수정, 시도 안 함). 호출자는 stdout 라인으로 구별한다.

### standalone 검증 (G6)

소비자(E3) 배선 없이 컴포넌트를 독립 검증한다. 검증은 `GH_ISSUE_DRY_RUN=1` 하에서만 수행하며, dry-run 계약의 zero gh calls가 대상 repo 무오염을 구조적으로 보장한다. 다섯 연산을 dry-run으로 해석했을 때 조합된 gh 명령이 stdout에 출력되고 실 이슈·라벨·계층·PR이 생성되지 않음을 확인한다. 컴포넌트가 실행 코드 없는 프롬프트 문서이므로 라이브 dry-run 실행은 소비자가 컴포넌트를 구동할 때 일어나고, G6은 계약 텍스트의 정적 점검으로 성립한다.

**검증 가능성의 비대칭**: G4는 읽기 전용 `gh issue view --json subIssues` 조회로 기존 계층의 필드 shape와 매칭 결과를 repo 오염 없이 실측할 수 있다. G5는 불가하다 — 링크·auto-close는 default branch를 base로 하는 실 PR을 만들어야 발동하므로 무오염 조건에서 라이브 검증이 성립하지 않는다. 따라서 G5는 조합 명령 형태와 base 분기 계약 텍스트의 정적 계약 점검으로만 확인하며, default-base 임시 PR을 만들어 auto-close를 확인하는 절차는 수행하지 않는다.

## 제약사항

- **앵커 전용** — 이슈는 딜리버러블 앵커이며 워크플로우 상태(phase:status 등)를 담지 않는다. 상태 저장소는 MongoDB(E4)가 소유한다.
- **배선 없음** — 소비자 스킬(`flow-spec`·`flow-pr`)에 호출을 삽입하는 배선은 범위 밖이다(E3-S2·E3-S5). 본 컴포넌트는 독립 연산만 제공한다.
- **gh ≥ 2.94.0 전제, 런타임 강제 아님** — 네이티브 sub-issue 명령이 요구하는 버전 전제는 `flow-init` 게이트가 단일 지점에서 검사·안내할 뿐 후속 커맨드를 강제하지 못한다. 가용성 게이트는 설치·권한만 보므로 구버전 gh는 두 조건을 통과한 뒤 `unknown flag: --add-sub-issue`로 실패한다. 어댑터는 이 실패를 skip(exit 0)으로 처리하는 잔여 방어를 둔다. 구버전용 REST database-id·GraphQL node-ID fallback 경로는 채택하지 않는다.
- **cross-repo PR 링크 없음** — `owner/repo#N` 형태의 다른 repo 이슈 auto-close는 closing keyword로 동작하지 않아 규정하지 않는다.
- **base branch 정책 불변** — closing keyword는 PR base가 default branch일 때만 링크를 형성한다. 본 컴포넌트는 불일치를 감지·경고할 뿐 base를 전환하거나 정책을 바꾸지 않는다(E3-S5 소관). tack은 default=`main`, 하네스 base=`develop`이므로 표준 PR에서 keyword는 무동작이며, 이는 플랫폼 제약이라 우회하지 않는다.
- **umbrella 재-mint 멱등 미정** — epic umbrella는 재-mint 중복 가드를 두지 않는다. 트리거 배선(E3-S2)과 함께 확정한다.
- **`config.gh.*` 소비자 부재** — 4필드는 부트스트랩 시점의 진단 기록이며 이를 읽는 컴포넌트가 아직 없다. 실행 시점 재검사를 대체하지 않으므로, 부트스트랩 이후 gh가 제거·다운그레이드되면 기록은 stale이 되고 감지 경로가 없다. 소비 배선은 E3 소관이다.
- **라벨 단일 타입 표현** — native 커스텀 Issue Types와 Projects 대시보드는 채택하지 않는다. 타입은 라벨(`type:epic`·`type:story`)로만 표현하고 대시보드는 MongoDB가 소유한다.
- **기존 이슈 불간섭** — ad-hoc 생성된 기존 수동 이슈의 재작성·정합화는 범위 밖이다.
- **canonical 규칙 우선** — 셸 방어의 강제 규칙은 `template/.tack/rules/security.md` Shell Injection Defense가, tier 판별은 `template/.claude/rules/common/component-boundaries.md`가, gh 버전 게이트는 `template/.claude/skills/flow-init/SKILL.md`가 소유한다. 충돌 시 규칙·소유 컴포넌트가 우선한다.
