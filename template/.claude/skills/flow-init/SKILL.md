---
version: 13
name: flow-init
description: Initialize or update project section of CLAUDE.md and AGENTS.md. Detects the gh CLI version, records config.gh.*, and blocks the harness bootstrap when native sub-issue support (gh >= 2.94.0) is unavailable.
origin: harness
user-invocable: true
---

# /flow-init

루트 `CLAUDE.md`와 `AGENTS.md`의 프로젝트 섹션을 초기화하거나 업데이트한다.

`deploy-harness.sh`로 하네스 파일을 배포한 후, 루트 `CLAUDE.md`와 `AGENTS.md`를 프로젝트 정보와 `.tack/rules/` 공유 규칙으로 구성하는 환경 설정 단계다.

두 파일 모두 `<!-- shared-rules:begin -->` / `<!-- shared-rules:end -->` 마커로 공유 규칙 블록을 감싼다. 마커 사이 시맨틱은 파일별로 다르다:

- **CLAUDE.md** — 마커 사이에 `@.tack/rules/<rel>` **@import 포인터** 목록을 생성한다.
- **AGENTS.md** — Codex는 `@import`를 지원하지 않으므로, 마커 사이에 `.tack/rules/` 규칙 **본문을 인라인**한다.

## Usage

```
/flow-init    CLAUDE.md와 AGENTS.md를 생성 또는 업데이트
```

## Execution Flow

### Step 1: 모드 분기

루트 `CLAUDE.md`와 `AGENTS.md` 각각 독립적으로 판정한다. 두 파일 모두 `<!-- shared-rules:begin -->` 마커를 경계 anchor로 사용한다.

**CLAUDE.md 모드**:

| 상태 | 모드 |
|------|------|
| `CLAUDE.md` 파일 없음 | **신규 생성** (`<!-- shared-rules:begin/end -->` 마커 포함 작성) |
| `<!-- shared-rules:begin -->` 마커 존재 | **업데이트** (begin/end 마커 사이만 재생성, 마커 외부는 일체 손대지 않음) |
| `<!-- shared-rules:begin -->` 마커 없음 | **경계 탐지 불가** → 경고 출력 + `AskUserQuestion`: `(Recommended) CLAUDE.md.bak.<timestamp> 백업 후 재생성 모드로 진행` / `중단` |

`shared-rules` 마커가 없는 기존 파일은 재생성의 안전한 경계를 정할 anchor가 없다. 레퍼런스 하네스가 쓰던 별도 마커·가이드 import anchor는 tack 레이아웃에 존재하지 않으므로 마이그레이션 경로를 두지 않고, 마커 부재 파일은 백업 후 재생성으로 처리한다.

Step 1은 흐름 분기(신규 / 업데이트 / 경계 탐지 불가)만 결정한다. 터미널 "변경 없음" 판정은 Step 3 작성 흐름의 SHA-256 hash 비교가 단일 권위자다 — 업데이트 모드는 항상 Step 2(프로젝트 정보 수집)·Step 3 작성 흐름(파싱→조립)·hash 비교를 그대로 진행한다.

판정 입력:
- `.tack/rules/` glob 결과: `find .tack/rules -name "*.md" -type f | sort`의 출력 (디렉토리 부재 시 빈 목록).
- `<!-- shared-rules:begin -->` / `<!-- shared-rules:end -->` 마커 사이 라인 집합 (업데이트 모드에서만 의미 있음). 마커 외부의 `@.tack/rules/<rel-path>` 접두사 라인은 사용자 콘텐츠로 간주되어 손대지 않는다 — 사용자가 메모·예시·체크리스트·커스텀 레이아웃에 rules import를 보존할 수 있도록 보장한다.

**AGENTS.md 모드**:
- `AGENTS.md`가 없으면 → **신규 생성**
- 있고 `<!-- shared-rules:begin -->` 마커가 있으면 → **업데이트**
- 있지만 마커가 없으면 → **경계 탐지 불가** → 경고 출력 + `AskUserQuestion`:
  - `(Recommended) AGENTS.md.bak.<timestamp> 백업 후 재생성 모드로 진행`
  - `중단`

각 파일의 모드는 독립적으로 결정되며, 한 파일이 "중단"을 선택해도 다른 파일은 계속 진행할 수 있다.

### Step 2: 프로젝트 정보 수집

`AskUserQuestion` 도구로 아래 4개 항목을 순서대로 질문한다. 각 질문의 첫 번째 옵션은 `(Recommended)` 레이블로 표시한다.

업데이트 모드에서는 기존 `CLAUDE.md`에서 읽은 값을 권장 옵션으로 제시한다.

1. **프로젝트명** — 짧은 이름 (예: `my-app`)
   - `(Recommended)` 현재 디렉토리명: `$(basename "$PWD")`
   - 직접 입력

2. **한 줄 설명** — 프로젝트 또는 저장소의 목적
   - `(Recommended)` 기존 값 (업데이트 모드) 또는 예시
   - 직접 입력

3. **기술 스택** — 핵심 언어·프레임워크 목록 (쉼표 구분)
   - `(Recommended)` 기존 값 (업데이트 모드) 또는 예시
   - 직접 입력

4. **언어 규칙** — 문서/코드/컴포넌트 파일 언어
   - `(Recommended)` 기본값: 문서·주석·커밋 메시지 **한국어** / 코드 식별자 **영어** / 컴포넌트 파일 **영어**
   - 직접 입력

### Step 3: CLAUDE.md 작성

수집한 프로젝트 정보로 프로젝트 섹션과 import 블록을 구성한다. 전체 CLAUDE.md 구조:

```markdown
---
version: N
---

# CLAUDE.md

Claude Code가 이 저장소에서 작업할 때의 안내 파일.

## 프로젝트 개요

[한 줄 설명]

## 기술 스택

[기술 스택 — 각 항목을 bullet로]

## 언어 규칙

[언어 규칙]

<!-- shared-rules:begin -->
@.tack/rules/coding-style.md
@.tack/rules/git-workflow.md
@.tack/rules/security.md
@.tack/rules/testing.md
@.tack/rules/typescript/patterns.md
@.tack/rules/typescript/testing.md
<!-- shared-rules:end -->

[사용자 정의 영역 — 보존, 마커 외부는 손대지 않음]
```

**import 블록 경계 규칙** (marker-bounded):

- import 블록은 `<!-- shared-rules:begin -->` 마커부터 시작한다. 프로젝트 섹션은 이 begin 마커 직전까지로 정의된다.
- begin/end 마커 사이에 `.tack/rules/**/*.md` glob 결과로 자동 생성된 `@.tack/rules/<rel-path>` 라인 N개가 정렬된 순서로 이어진다.
- `<!-- shared-rules:end -->` 마커가 import 블록의 끝을 표시한다. end 마커 뒤에 newline `\n` 1개로 블록을 종료한다 — trailing 빈 줄은 포함하지 않는다. 사용자 영역과의 구분 빈 줄 1개는 Step 3 조립 식의 `+ [빈 줄]`이 단독 소유한다 (이중 빈 줄 방지).
- begin/end 마커 사이는 매 실행마다 glob 결과로 완전 재생성된다 (기존 사이 콘텐츠는 폐기). 마커 외부의 `@.tack/rules/<rel-path>` 접두사 라인은 사용자 콘텐츠로 간주해 **검사·수정·삭제 모두 하지 않는다** — 사용자가 메모·예시·체크리스트·커스텀 레이아웃에 의도적으로 유지한 라인을 silently 이동·삭제하지 않는다.
- 마커 외부의 모든 라인(비-`.tack/rules` `@import`, 일반 마크다운, 사용자 추가 콘텐츠)은 **그대로 보존**된다.

**import 블록 정렬·생성 규칙**:

- **수집**: `find .tack/rules -name "*.md" -type f | sort` 명령으로 룰 파일 목록을 수집한다. `.tack/rules/`로 시작하는 상대 경로로 변환한다.
- **정렬**: `sort`의 lexicographic 결과를 그대로 사용한다 — top-level 파일이 sub-dir 파일보다 alphabetically 앞서므로 자연스럽게 top-level 우선.
- **변환**: 각 경로 앞에 `@` 접두사를 부여한다. 결과 라인 형식은 `@.tack/rules/<rel-path>`.
- **삽입 위치**: `<!-- shared-rules:begin -->` 마커 직후부터 차례로 삽입하고, 마지막 라인 뒤에 `<!-- shared-rules:end -->` 마커를 둔다. import 블록 자체에는 trailing 빈 줄을 포함하지 않는다 (구분 빈 줄은 조립 식이 단독 소유).

**`.tack/rules/` 부재 시**:

- `.tack/rules/` 디렉토리가 없거나 glob 결과가 0건이면 begin/end 마커 사이를 **빈 상태**로 둔다 (마커 자체는 유지 — 차후 실행이 marker 기반 업데이트 모드로 진입하도록 idempotency 보장).
- Step 8 결과 안내에 `[정보] .tack/rules/ 부재로 마커 사이 비움` 1줄을 추가한다.

**Step 3 작성 흐름**:

1. **파싱** — 기존 CLAUDE.md를 세 부분으로 나눈다 (marker-bounded):
   - frontmatter + 프로젝트 섹션 (파일 시작 ~ `<!-- shared-rules:begin -->` 마커 직전)
   - 마커 블록 (`<!-- shared-rules:begin -->` 마커 + 마커 사이 라인 + `<!-- shared-rules:end -->` 마커). **업데이트 모드**에서만 추출되며 매 실행마다 폐기·재생성된다.
   - 사용자 정의 영역 (`<!-- shared-rules:end -->` 마커 직후부터 파일 끝까지의 모든 라인. 마커 외부 라인은 `@.tack/rules/<rel-path>` 접두사를 포함해 **검사·수정·삭제 없이 그대로 보존**한다). 마커 블록과 사용자 영역 사이의 선두 빈 줄 1개만 구분자로 흡수한다.
2. **신규 프로젝트 섹션 작성** — Step 2 수집 정보로 frontmatter·프로젝트 섹션을 구성한다. 프로젝트 섹션 본문 끝에 trailing blank 1줄을 둔다.
3. **신규 import 블록 생성** — 위 정렬·생성 규칙으로 `<!-- shared-rules:begin -->` + `@.tack/rules/<rel-path>` N개 라인 + `<!-- shared-rules:end -->`을 만든다. `.tack/rules/` 부재 시 마커 사이는 비워둔다 (마커 자체는 유지).
4. **조립** — [frontmatter] + [프로젝트 섹션 (trailing blank 1줄 포함)] + [import 블록 (마커 포함)] + [빈 줄] + [사용자 정의 영역] 순서로 연결한다. 파일 끝은 trailing newline `\n` 1개로 정규화한다.
5. **변경 감지 (SHA-256 hash 비교)** — 조립된 신규 CLAUDE.md와 기존 CLAUDE.md의 SHA-256 hash를 1회 비교한다. hash 비교 범위에서 frontmatter `version: N` 라인은 제외한다. hash가 동일하면 파일을 건드리지 않고 `[변경 없음]`으로 표기한다. 다르면 `version` 값을 기존 +1로 증가시키고 원자적 쓰기를 수행한다.

**신규 생성**: 위 흐름에서 1·5단계를 skip하고 2·3·4단계로 새 CLAUDE.md를 생성한다 (사용자 정의 영역은 빈 상태이며, 빈 사용자 영역 슬롯 앞 구분자 빈 줄은 drop하고 파일은 `<!-- shared-rules:end -->` 마커 뒤 trailing newline `\n` 1개로 끝난다).

### Step 4: AGENTS.md 작성

AGENTS.md는 CLAUDE.md와 동일한 `<!-- shared-rules:begin/end -->` 마커를 쓰되, 마커 사이에 `.tack/rules/` 규칙 **본문을 인라인**한다 (Codex는 `@import` 미지원).

**인라인 대상**: `find .tack/rules -name "*.md" -type f | sort` — `.tack/rules/` 전체(재귀, `typescript/` 하위 포함) 규칙 본문을 인라인한다. CLAUDE.md의 @import 집합과 동일 세트를 보장한다 (base-layout §8, 규칙 집합 대칭 · `AGENTS.md.jinja`와 정합). 각 파일은 읽은 뒤 YAML frontmatter 블록(`---\nversion: N\n---`)을 제외한 본문만 삽입하고, 파일 간 빈 줄 1개로 구분한다.

**신규 생성**:

```markdown
# AGENTS.md

Codex CLI가 이 저장소에서 작업할 때의 안내 파일. Claude Code는 `CLAUDE.md`를 사용한다.

## 프로젝트 개요

[한 줄 설명]

## 기술 스택

[기술 스택]

## 언어 규칙

[언어 규칙]

<!-- shared-rules:begin -->
[.tack/rules/ 전체(재귀) 본문 인라인 — 파일 간 빈 줄 1개로 구분]
<!-- shared-rules:end -->
```

`.tack/rules/` 규칙 파일이 존재하면 정렬 순서대로 본문을 인라인한다. 디렉토리가 없거나 glob 결과가 0건이면 마커 사이를 빈 상태로 생성하고 경고를 출력한다.

**업데이트**:
- `<!-- shared-rules:begin -->` 이전 모든 내용을 새 프로젝트 섹션으로 교체한다.
- begin/end 마커 사이 내용을 현재 `.tack/rules/`(재귀) 본문 인라인으로 교체한다 (point-in-time 갱신).
- 마커 라인 자체(`<!-- shared-rules:begin -->`, `<!-- shared-rules:end -->`)는 그대로 유지한다.
- `<!-- shared-rules:end -->` **이후의 내용도 그대로 보존**한다.
- **trailing 줄바꿈 정규화**: 인라인 본문을 삽입할 때 마지막 본문 끝의 공백/줄바꿈을 rstrip한 뒤 정확히 `\n`(한 줄)을 붙여 end 마커 앞에 놓는다. end 마커 앞에 빈 줄이 생기지 않도록 한다.
- **변경 감지**: 조립된 전체 AGENTS.md 내용이 기존과 동일하면 파일을 건드리지 않는다 (`[변경 없음]` 표기).

### Step 5: docs.sourceFilter 자동 감지·설정

Step 1에서 두 파일(`CLAUDE.md`, `AGENTS.md`) 모두 "중단"을 선택한 경우 이 단계를 건너뛴다.

`scripts/deploy-harness.sh` 파일 존재 여부로 저장소 유형을 감지하고 `config.docs.sourceFilter`를 설정한다.

**보존 정책 (선결 조건)**: 기존 `config.docs.sourceFilter`가 **존재하면서 빈 배열·null·미설정이 아닌 경우** 감지 결과를 적용하지 않고 기존 값을 그대로 유지한다. `/flow-init`은 imports 재생성을 위해 재실행될 수 있으므로 (`/meta-add-language-rules` 안내), 사용자가 명시적으로 설정한 sourceFilter를 재실행마다 덮어쓰지 않는다. 보존이 발동하면 Step 8에 `[보존] config.docs.sourceFilter 기존 값 유지`를 출력한다.

기존 값이 부재(미설정·빈 배열·null)일 때만 아래 감지 로직을 적용한다.

**감지 로직** (기존 값 부재 시):

`scripts/deploy-harness.sh`가 존재하면 (하네스 저장소):
```bash
python3 .tack/scripts/dev_context.py set-field \
  --field=config.docs.sourceFilter \
  --value='[".claude/",".codex/",".tack/","CLAUDE.md","AGENTS.md"]'
```
출력: `하네스 저장소로 감지: config.docs.sourceFilter를 하네스 기본값으로 설정했습니다.`

`scripts/deploy-harness.sh`가 없으면 (일반 프로젝트):
```bash
python3 .tack/scripts/dev_context.py set-field \
  --field=config.docs.sourceFilter \
  --value='[]'
```
출력: `일반 프로젝트로 감지: config.docs.sourceFilter를 빈 배열로 설정했습니다 (필터 없음).`

**수동 재설정**: 자동 감지값으로 강제 초기화하려면 사용자가 직접 빈 값으로 reset한 뒤 `/flow-init`을 재실행하거나, `dev-context.js set-field`로 임의 값을 지정한다:
```bash
python3 .tack/scripts/dev_context.py set-field \
  --field=config.docs.sourceFilter --value='["src/","lib/"]'
```

### Step 6: config.graphify.targets 추천·확정

Step 1에서 두 파일(`CLAUDE.md`, `AGENTS.md`) 모두 "중단"을 선택한 경우 이 단계를 건너뛴다.

`config.graphify.targets`는 `/graphify` 풀 빌드의 분석 대상 디렉토리 배열이다. 본 Step은 배포 직후 미설정·빈 배열·null 상태일 때 저장소 유형별 추천값을 제시하고 `AskUserQuestion`으로 확정한다. 이미 비어 있지 않은 배열이 설정돼 있으면 보존한다 (멱등).

**보존 정책 (선결 조건)**: 먼저 다음 명령으로 현재 값을 조회한다.

```bash
python3 .tack/scripts/dev_context.py read --field=config.graphify.targets
```

`dev-context.js read`는 배열 원소를 한 줄당 하나씩 newline-delimited로 출력하며, 빈 배열·null·미설정은 빈 stdout을 낸다. `config.graphify.targets`는 문자열 배열로만 의미가 있지만 `dev-context.js`는 동일 키에 boolean·number·문자열 같은 scalar 값도 저장 가능하다. 다음 케이스로 분기한다:

- 명령이 비-0 exit으로 종료: Step 8에 `[감지 실패] config.graphify.targets`를 출력한다.
- stdout이 비어 있음 (빈 배열·null·미설정): 아래 추천 분기로 진입한다.
- stdout에 한 줄 이상의 라인이 있고 모든 라인이 비어 있지 않은 문자열 원소처럼 보인다 (배열이 비어 있지 않은 문자열 배열): 추천을 건너뛰고 Step 8에 `[보존] config.graphify.targets 기존 값 유지`를 출력한다.
- stdout에 한 줄 이상의 라인이 있지만 저장된 값이 scalar(예: `true`, `42`, 단일 문자열 `"docs"` 등)로 의심된다: 잘못된 상태로 간주해 Step 8에 `[감지 실패] config.graphify.targets`를 출력하고 사용자에게 재설정 여부를 `AskUserQuestion`으로 묻는다. scalar 의심 신호는 — 라인 1개 + 값이 `true`/`false`/숫자/디렉토리로 해석되지 않는 단일 토큰 — 같은 휴리스틱으로 판정한다.

**저장소 유형별 추천값 분기** (기존 값 부재 시):

`scripts/deploy-harness.sh` 존재 여부로 저장소 유형을 감지해 추천 후보를 결정한다.

- 존재 (본 하네스 저장소): 추천 후보 `["./src", "./docs/specs", "scripts"]`
- 미존재 (배포된 하네스 또는 일반 프로젝트): 추천 후보 `["./.claude", "./.tack", "./docs"]`

**확정 (`AskUserQuestion`)**: 위 추천 후보를 다음 2개 옵션으로 사용자에게 제시한다. `AskUserQuestion` 도구는 자동으로 "Other" 옵션을 추가하므로, 사용자가 자유 텍스트로 JSON 배열을 직접 작성하는 흐름은 "Other" 입력으로 처리한다.

- 옵션 1 `(Recommended)` — 추천 후보를 그대로 사용
- 옵션 2 — 건너뛰기 (값 미설정 유지, 추후 `/graphify` 호출 시 hard error로 안내)

**입력 유효성**: 사용자가 "Other"로 입력한 디렉토리 경로에 single-quote(`'`) 또는 newline이 포함되면 JSON 배열로 직렬화한 뒤 single-quoted 셸 인자로 전달할 때 인용 부호 종결 문제가 발생한다. 이런 경우 `AskUserQuestion`으로 재입력을 요구한다.

**기록 동작**: 확정값을 JSON 배열로 직렬화한 뒤 다음 명령으로 기록한다.

```bash
python3 .tack/scripts/dev_context.py set-field --field=config.graphify.targets --value='<JSON 배열>'
```

옵션 2(건너뛰기)를 선택하면 `set-field`를 호출하지 않고 Step 8에 `[정보] config.graphify.targets 미설정 유지`를 출력한다. 추후 `/graphify` 호출 시 hard error로 안내된다.

### Step 7: gh 버전 게이트 (≥ 2.94.0)

Step 1에서 두 파일(`CLAUDE.md`, `AGENTS.md`) 모두 "중단"을 선택한 경우 이 단계를 건너뛴다.

하네스의 GitHub 이슈 앵커 연산(`adapter-github-issue` §Sub-Issue Link)은 네이티브 sub-issue 명령 `gh issue edit --add-sub-issue`를 사용하며, 이 명령은 `gh` 2.94.0에서 도입됐다. 본 Step은 `gh` 설치·버전을 감지해 `config.gh.*` 4필드에 기록하고, 2.94.0 미만이면 하네스 부트스트랩을 차단한다.

**단일 지점 원칙**: 버전 차단 판정은 `/flow-init` 이 한 지점에서만 성립한다. 개별 `flow-*` 스킬이나 `adapter-github-issue` 연산에 per-op 버전 게이트를 분산하지 않는다 — 부트스트랩을 통과한 환경에서는 연산 시점에 버전이 보장되므로, 어댑터의 가용성 게이트는 기존 graceful skip 계약을 그대로 유지한다. 차단은 부트스트랩 단계의 안내이지 후속 커맨드에 대한 런타임 강제가 아니다 — `[차단]`을 보고도 계속 진행한 사용자에게는 `config.gh.native_subissue`가 진단 기록으로 남고, 어댑터의 gh 미설치·권한 미충족 skip 경로가 잔여 방어로 동작한다.

**실행 순서**: 가용성 감지 → 버전 파싱 → 버전 비교 → 4필드 기록 → (차단 판정 시) Step 8 인계. 먼저 `gh` 설치 여부를 확인한다.

```bash
command -v gh >/dev/null 2>&1
```

비-0 exit이면 미설치 상태로 확정하고 버전 파싱·비교를 건너뛴 뒤 4필드 기록으로 진행한다.

**감지 상태 테이블** (exhaustive — 4행이 gh 감지의 모든 경우를 덮는다):

| 상태 | `available` | `native_subissue` | `version` | 판정 |
|------|-------------|-------------------|-----------|------|
| `command -v gh` 실패 (미설치) | `false` | `false` | `""` | **차단** |
| gh 설치, `gh --version` 파싱 실패 | `true` | `false` | `""` | **차단** (fail-closed) |
| gh 설치, 파싱 버전 < 2.94.0 | `true` | `false` | `X.Y.Z` | **차단** |
| gh 설치, 파싱 버전 ≥ 2.94.0 | `true` | `true` | `X.Y.Z` | proceed |

**버전 파싱**:

`gh --version` 첫 줄은 `gh version 2.96.0 (2026-07-02)` 형식이다 (gh 2.96.0 실측). 첫 줄에서 `X.Y.Z`를 추출한다.

```bash
GH_VERSION=$(gh --version 2>/dev/null | head -1 | sed -E 's/^gh version ([0-9]+\.[0-9]+\.[0-9]+).*/\1/')
```

**파싱 성공 판정은 추출 결과가 `^[0-9]+\.[0-9]+\.[0-9]+$`에 매칭하는지로 한다** — 명령의 exit code로 판정하지 않는다. `sed`는 패턴이 매칭하지 않아도 exit 0으로 종료하며 입력 라인을 그대로 되돌려주므로, exit code를 신뢰하면 파싱 실패 행이 발동하지 않고 쓰레기 문자열이 버전 비교로 흘러든다. 미매칭이면 파싱 실패 상태(`version=""`, `native_subissue=false`)로 fail-closed 처리한다.

**버전 비교**:

major·minor·patch를 각각 분리해 **정수로 비교**한다. 문자열 비교(`[[ "$GH_VERSION" < "2.94.0" ]]`)는 `2.100.0`을 `2.94.0`보다 낮게 판정한다 — `1` < `9`가 문자 단위로 성립하기 때문이며, 실제로는 2.100.0이 더 높은 버전이다. 이 오판은 최신 gh를 쓰는 환경을 잘못 차단하므로 문자열 비교를 사용하지 않는다.

```bash
GH_MAJOR=$(echo "$GH_VERSION" | cut -d. -f1)
GH_MINOR=$(echo "$GH_VERSION" | cut -d. -f2)
if [ "$GH_MAJOR" -gt 2 ] || { [ "$GH_MAJOR" -eq 2 ] && [ "$GH_MINOR" -ge 94 ]; }; then
  GH_NATIVE_SUBISSUE=true
else
  GH_NATIVE_SUBISSUE=false
fi
```

minor를 비교하기 전에 major 동등을 먼저 확정한다 — major 확인 없이 minor만 비교하면 `1.99.0`이 통과한다. 임계값 patch가 `0`이므로 patch 성분은 판정에 영향을 주지 않는다.

`declare -A`·`mapfile` 같은 bash 전용 구문은 사용하지 않는다 (zsh 이식성 — `development-workflow.md` §Shell Portability).

**4필드 기록**:

Step 5·6과 동일한 형태로 기록한다. 기록은 **4개 상태 모두에서 수행한다** — 차단 상태도 먼저 기록한 뒤 차단한다.

```bash
python3 .tack/scripts/dev_context.py set-field --field=config.gh.available --value="$GH_AVAILABLE"
python3 .tack/scripts/dev_context.py set-field --field=config.gh.native_subissue --value="$GH_NATIVE_SUBISSUE"
python3 .tack/scripts/dev_context.py set-field --field=config.gh.version --value="$GH_VERSION"
python3 .tack/scripts/dev_context.py set-field --field=config.gh.checked_at --value="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

**쓰기 순서와 부분 실패**: 네 호출은 각각 독립 CLI 호출이므로 중간 실패 시 `config.gh`가 반쯤 갱신된 상태로 남는다. `checked_at`을 **마지막에** 기록해 이 상태를 판별 가능하게 만든다 — `checked_at`이 같은 실행에서 갱신되지 않았으면 나머지 세 필드는 이전 실행의 잔존 값일 수 있으므로 신뢰하지 않는다. 네 호출 중 하나라도 비-0 exit이면 Step 8에 `[감지 실패] config.gh.*`를 표기하고, 남아 있는 값은 유효하지 않은 것으로 안내한다.

| 필드 | 값 타입 | 의미 |
|------|---------|------|
| `config.gh.available` | bool-as-string (`true`/`false`) | `command -v gh` 성공 여부 |
| `config.gh.native_subissue` | bool-as-string (`true`/`false`) | 파싱된 버전이 2.94.0 이상인지 |
| `config.gh.version` | semver 문자열 (`2.96.0`) 또는 빈 문자열 | `gh --version` 첫 줄에서 파싱한 `X.Y.Z` |
| `config.gh.checked_at` | ISO8601 문자열 | 감지 시각 — `date -u +%Y-%m-%dT%H:%M:%SZ` |

**차단 처리**:

차단 3개 상태(미설치 / 파싱 실패 / < 2.94.0)에서는 4필드를 기록한 뒤 **이 Step에서 종료하지 않고** 차단 판정을 들고 Step 8로 진행한다. Step 8이 `[차단]` 라인과 업그레이드 안내를 출력한 다음 `/flow-init`을 **미완료 종료**한다. Step 7에서 곧바로 종료하면 사용자가 차단 사유와 복구 방법을 보지 못한다.

미완료 종료는 파일 롤백을 수반하지 않는다 — Step 3·4가 이미 작성한 `CLAUDE.md`·`AGENTS.md`는 그대로 둔다. 차단은 하네스 워크플로우 진입 차단이지 파일 작성 취소가 아니다.

**상태별 복구 안내**: 차단 3개 상태는 원인이 서로 다르므로 Step 8이 출력할 복구 문구도 상태별로 갈린다. 세 상태 모두 조치 후 `/flow-init` 재실행으로 게이트를 다시 통과시킨다.

| 차단 상태 | 진단 라인 | 복구 안내 |
|-----------|----------|----------|
| 미설치 | `감지된 버전: 없음 (gh 미설치)` | `설치: brew install gh  또는  https://cli.github.com` |
| 파싱 실패 | `감지된 버전: 파싱 실패 (gh --version 출력 형식 불일치)` | `gh --version 출력을 확인하세요. 버전 문자열이 'gh version X.Y.Z' 형식이 아닙니다` |
| < 2.94.0 | `감지된 버전: <X.Y.Z>` | `업그레이드: brew upgrade gh  또는  https://cli.github.com` |

미설치·파싱 실패 상태에 `brew upgrade gh`를 안내하지 않는다 — 설치되지 않은 formula에 `brew upgrade`는 실패하고, 파싱 실패는 버전이 낮아서 생긴 문제가 아니므로 업그레이드로 해소되지 않는다.

### Step 8: 결과 안내

작성된 파일 경로와 결과를 출력한다:

```
완료:
  [신규/업데이트/변경 없음] CLAUDE.md
  [신규/업데이트/변경 없음] AGENTS.md
  [감지] config.docs.sourceFilter = [".claude/",".codex/",".tack/","CLAUDE.md","AGENTS.md"]
  [감지] config.graphify.targets = ["./src","./docs/specs","scripts"]
  [감지] config.gh.version = 2.96.0
```
(일반 프로젝트의 경우: `[감지] config.docs.sourceFilter = [] (필터 없음)`)

**차단 시 출력**: Step 7이 차단 판정을 넘긴 경우 헤더를 `완료:` 대신 `미완료:`로 출력한다 — 차단된 실행을 `완료:` 아래 표기하면 자기모순이다. `[차단]` 라인과 복구 안내를 함께 출력하고 `/flow-init`을 미완료 종료한다.

진단 라인·복구 안내는 Step 7 §상태별 복구 안내 표의 해당 행을 그대로 사용한다. 아래는 `< 2.94.0` 행 예시다.

```
미완료:
  [신규/업데이트/변경 없음] CLAUDE.md
  [신규/업데이트/변경 없음] AGENTS.md
  [차단] gh >= 2.94.0 미충족 — 네이티브 sub-issue 연산 불가
    감지된 버전: 2.90.0
    config.gh.*: 기록 완료
    업그레이드: brew upgrade gh  또는  https://cli.github.com
    업그레이드 후 /flow-init을 재실행하세요. 작성된 CLAUDE.md·AGENTS.md는 롤백되지 않습니다.
```

`config.gh.*` 라인은 실제 기록 결과를 반영한다 — 4필드 기록이 모두 성공했으면 `기록 완료`, 하나라도 실패했으면 `기록 실패 (아래 [감지 실패] 참조)`로 출력하고 `[감지 실패] config.gh.*` 라인을 함께 낸다. 기록 실패는 버전 판정을 바꾸지 않으므로 `[차단]`과 `[감지 실패]`는 동시에 나타날 수 있다.

- `[신규]`: 파일이 새로 생성됨
- `[업데이트]`: 내용이 달라져 파일을 다시 씀
- `[변경 없음]`: 내용이 동일하여 파일을 건드리지 않음
- `[감지]`: 기존 sourceFilter가 부재해 자동 감지값을 set한 경우
- `[보존] config.docs.sourceFilter 기존 값 유지`: 기존 sourceFilter가 존재(빈 배열·null·미설정 아님)해 감지값을 적용하지 않고 보존한 경우. `[감지]`와 상호 배타.
- `[정보] .tack/rules/ 부재로 마커 사이 비움`: `.tack/rules/` 디렉토리가 없거나 glob 결과가 0건이어서 begin/end 마커 사이에 import 라인·인라인 본문을 생성하지 않은 경우 추가 출력한다 (마커 자체는 유지). 그 외 경우 본 라인을 출력하지 않는다 (위 예시는 `.tack/rules/` 존재 시나리오이므로 본 라인을 포함하지 않는다).
- `[감지] config.graphify.targets = <배열>`: 기존 `config.graphify.targets`가 부재(빈 배열·null·미설정)해 추천값을 사용자 확정 후 set한 경우. 출력 배열은 `AskUserQuestion`으로 확정된 최종 값.
- `[보존] config.graphify.targets 기존 값 유지`: 기존 `config.graphify.targets`가 비어 있지 않은 배열이어서 추천을 건너뛰고 보존한 경우. `[감지]`와 상호 배타.
- `[정보] config.graphify.targets 미설정 유지`: 사용자가 추천 단계에서 옵션 2 "건너뛰기"를 선택한 경우. 추후 `/graphify` 호출 시 hard error로 안내된다.
- `[감지 실패] config.graphify.targets`: `dev-context.js read` 호출 실패, scalar 값이 배열 키에 저장된 잘못된 상태, `set-field` 실패 중 하나가 발생한 경우. 기존 값은 변경되지 않고 사용자에게 재설정 여부를 묻는다.
- `[감지] config.gh.version = X.Y.Z`: Step 7이 gh 버전을 파싱하고 2.94.0 이상으로 판정해 통과한 경우. `[차단]`과 상호 배타이며, `[감지 실패] config.gh.*`와도 상호 배타다 — 4필드가 모두 기록된 상태에서만 출력한다.
- `[차단] gh >= 2.94.0 미충족 — 네이티브 sub-issue 연산 불가`: Step 7의 차단 3개 상태(미설치 / 파싱 실패 / < 2.94.0) 중 하나가 발동한 경우. 4필드 기록을 시도한 뒤 차단되며, Step 7 §상태별 복구 안내의 해당 행과 함께 `/flow-init`이 미완료 종료한다. `[감지] config.gh.version`과 상호 배타. `[감지 실패] config.gh.*`와는 동시 출력 가능하다 (기록 실패가 버전 판정을 바꾸지 않는다).
- `[감지 실패] config.gh.*`: `dev_context.py` 미존재, 또는 4개 `set-field` 호출 중 하나 이상이 실패해 기록이 불완전한 경우. 감지 결과 자체는 유효하므로 버전 판정(통과·차단)은 그대로 적용하되, 저장된 `config.gh.*` 값은 신뢰하지 않는다 (Step 7 §쓰기 순서와 부분 실패).

## 오류 처리

| 상황 | 처리 |
|------|------|
| `<!-- shared-rules:begin -->` 마커 없는 기존 CLAUDE.md 또는 AGENTS.md | Step 1에서 경고 + AskUserQuestion → 백업 후 재생성 or 중단 |
| `.tack/rules/` 없음 | CLAUDE.md·AGENTS.md begin/end 마커 사이를 빈 상태로 생성, 경고 출력 |
| 쓰기 권한 없음 | 오류 메시지 출력 후 종료 |
| Step 5: `dev_context.py` 미존재 또는 `set-field` 실패 | 경고 출력 + Step 5 스킵, Step 8에서 `[감지 실패] config.docs.sourceFilter` 표기 |
| Step 6: `dev_context.py` 미존재 또는 `set-field` 실패 | 경고 출력 + Step 6 스킵, Step 8에서 `[감지 실패] config.graphify.targets` 표기 |
| Step 7: `dev_context.py` 미존재 또는 `set-field` 실패 | 경고 출력 + 4필드 기록 스킵, Step 8에서 `[감지 실패] config.gh.*` 표기. 버전 판정(통과·차단)은 기록 실패와 무관하게 그대로 적용한다 |

## Key Principles

- **항상 루트 대상** — `src/` 여부와 관계없이 항상 루트 `CLAUDE.md`, `AGENTS.md`를 수정한다.
- **AskUserQuestion 사용 필수** — 선택이 포함된 모든 질문에 적용. 첫 옵션에 `(Recommended)` 레이블.
- **shared-rules 마커 기준 업데이트** — 두 파일 모두 공유 규칙 블록을 `<!-- shared-rules:begin -->` / `<!-- shared-rules:end -->` 마커 쌍으로 bound한다. 프로젝트 섹션은 begin 마커 직전까지로 정의되고, 마커 외부는 사용자 영역으로 보존된다. 마커 사이 시맨틱은 파일별로 다르다 — CLAUDE.md는 `@.tack/rules/<rel>` @import 포인터 목록, AGENTS.md는 `.tack/rules/` 본문 인라인.
- **`.tack/rules/` 단일 소스** — CLAUDE.md import 블록과 AGENTS.md 인라인 블록 모두 `.tack/rules/` 재귀 glob 결과(typescript/ 포함)로 재생성된다. 두 파일이 동일 규칙 집합을 보장한다 (base-layout §8 대칭). CLAUDE.md는 `@import` 포인터, AGENTS.md는 본문 인라인.
- **저장소 유형 자동 감지** — `scripts/deploy-harness.sh` 존재 여부로 `config.docs.sourceFilter` 기본값을 결정한다 (하네스: prefix 목록 / 일반: 빈 배열). **기존 non-empty 값은 보존**한다 — `/flow-init`은 imports 재생성을 위해 재실행 가능하므로, 사용자 명시 설정을 재실행마다 덮어쓰지 않는다 (빈 배열·null·미설정일 때만 감지값 적용).
- **graphify targets 추천** — 배포 직후 `config.graphify.targets`가 미설정·빈 배열일 때 추천값을 `AskUserQuestion`으로 확정한다. 비어 있지 않은 기존 값은 보존한다 (멱등).
- **gh ≥ 2.94.0 전제조건** — Step 7이 gh 설치·버전을 감지해 `config.gh.*` 4필드에 기록하고, 미충족 시 `[차단]` 안내와 함께 `/flow-init`을 미완료 종료한다. 버전 차단은 이 한 지점에서만 판정하며 개별 `flow-*`·`adapter-*` 연산에 분산하지 않는다. 차단은 이미 작성된 `CLAUDE.md`·`AGENTS.md`를 롤백하지 않는다.
