---
version: 9
name: flow-init
description: Initialize or update project section of CLAUDE.md and AGENTS.md.
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
- Step 7 결과 안내에 `[정보] .tack/rules/ 부재로 마커 사이 비움` 1줄을 추가한다.

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

**인라인 대상**: `find .tack/rules -maxdepth 1 -name "*.md" -type f | sort` — top-level `.tack/rules/*.md` 파일만 인라인한다. `typescript/` 하위 규칙(patterns·testing)은 Claude 전용 언어 규칙이므로 인라인하지 않는다 (AGENTS.md.jinja와 정합). 각 파일은 읽은 뒤 YAML frontmatter 블록(`---\nversion: N\n---`)을 제외한 본문만 삽입하고, 파일 간 빈 줄 1개로 구분한다.

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
[top-level .tack/rules/*.md 본문 인라인 — 파일 간 빈 줄 1개로 구분]
<!-- shared-rules:end -->
```

top-level `.tack/rules/*.md`가 존재하면 정렬 순서대로 본문을 인라인한다. 디렉토리가 없거나 top-level glob 결과가 0건이면 마커 사이를 빈 상태로 생성하고 경고를 출력한다.

**업데이트**:
- `<!-- shared-rules:begin -->` 이전 모든 내용을 새 프로젝트 섹션으로 교체한다.
- begin/end 마커 사이 내용을 현재 top-level `.tack/rules/*.md` 본문 인라인으로 교체한다 (point-in-time 갱신).
- 마커 라인 자체(`<!-- shared-rules:begin -->`, `<!-- shared-rules:end -->`)는 그대로 유지한다.
- `<!-- shared-rules:end -->` **이후의 내용도 그대로 보존**한다.
- **trailing 줄바꿈 정규화**: 인라인 본문을 삽입할 때 마지막 본문 끝의 공백/줄바꿈을 rstrip한 뒤 정확히 `\n`(한 줄)을 붙여 end 마커 앞에 놓는다. end 마커 앞에 빈 줄이 생기지 않도록 한다.
- **변경 감지**: 조립된 전체 AGENTS.md 내용이 기존과 동일하면 파일을 건드리지 않는다 (`[변경 없음]` 표기).

### Step 5: docs.sourceFilter 자동 감지·설정

Step 1에서 두 파일(`CLAUDE.md`, `AGENTS.md`) 모두 "중단"을 선택한 경우 이 단계를 건너뛴다.

`scripts/deploy-harness.sh` 파일 존재 여부로 저장소 유형을 감지하고 `config.docs.sourceFilter`를 설정한다.

**보존 정책 (선결 조건)**: 기존 `config.docs.sourceFilter`가 **존재하면서 빈 배열·null·미설정이 아닌 경우** 감지 결과를 적용하지 않고 기존 값을 그대로 유지한다. `/flow-init`은 imports 재생성을 위해 재실행될 수 있으므로 (`/add-language-rules` 안내), 사용자가 명시적으로 설정한 sourceFilter를 재실행마다 덮어쓰지 않는다. 보존이 발동하면 Step 7에 `[보존] config.docs.sourceFilter 기존 값 유지`를 출력한다.

기존 값이 부재(미설정·빈 배열·null)일 때만 아래 감지 로직을 적용한다.

**감지 로직** (기존 값 부재 시):

`scripts/deploy-harness.sh`가 존재하면 (하네스 저장소):
```bash
node .tack/scripts/dev-context.js set-field \
  --field=config.docs.sourceFilter \
  --value='[".claude/",".codex/",".tack/","CLAUDE.md","AGENTS.md"]'
```
출력: `하네스 저장소로 감지: config.docs.sourceFilter를 하네스 기본값으로 설정했습니다.`

`scripts/deploy-harness.sh`가 없으면 (일반 프로젝트):
```bash
node .tack/scripts/dev-context.js set-field \
  --field=config.docs.sourceFilter \
  --value='[]'
```
출력: `일반 프로젝트로 감지: config.docs.sourceFilter를 빈 배열로 설정했습니다 (필터 없음).`

**수동 재설정**: 자동 감지값으로 강제 초기화하려면 사용자가 직접 빈 값으로 reset한 뒤 `/flow-init`을 재실행하거나, `dev-context.js set-field`로 임의 값을 지정한다:
```bash
node .tack/scripts/dev-context.js set-field \
  --field=config.docs.sourceFilter --value='["src/","lib/"]'
```

### Step 6: config.graphify.targets 추천·확정

Step 1에서 두 파일(`CLAUDE.md`, `AGENTS.md`) 모두 "중단"을 선택한 경우 이 단계를 건너뛴다.

`config.graphify.targets`는 `/graphify` 풀 빌드의 분석 대상 디렉토리 배열이다. 본 Step은 배포 직후 미설정·빈 배열·null 상태일 때 저장소 유형별 추천값을 제시하고 `AskUserQuestion`으로 확정한다. 이미 비어 있지 않은 배열이 설정돼 있으면 보존한다 (멱등).

**보존 정책 (선결 조건)**: 먼저 다음 명령으로 현재 값을 조회한다.

```bash
node .tack/scripts/dev-context.js read --field=config.graphify.targets
```

`dev-context.js read`는 배열 원소를 한 줄당 하나씩 newline-delimited로 출력하며, 빈 배열·null·미설정은 빈 stdout을 낸다. `config.graphify.targets`는 문자열 배열로만 의미가 있지만 `dev-context.js`는 동일 키에 boolean·number·문자열 같은 scalar 값도 저장 가능하다. 다음 케이스로 분기한다:

- 명령이 비-0 exit으로 종료: Step 7에 `[감지 실패] config.graphify.targets`를 출력한다.
- stdout이 비어 있음 (빈 배열·null·미설정): 아래 추천 분기로 진입한다.
- stdout에 한 줄 이상의 라인이 있고 모든 라인이 비어 있지 않은 문자열 원소처럼 보인다 (배열이 비어 있지 않은 문자열 배열): 추천을 건너뛰고 Step 7에 `[보존] config.graphify.targets 기존 값 유지`를 출력한다.
- stdout에 한 줄 이상의 라인이 있지만 저장된 값이 scalar(예: `true`, `42`, 단일 문자열 `"docs"` 등)로 의심된다: 잘못된 상태로 간주해 Step 7에 `[감지 실패] config.graphify.targets`를 출력하고 사용자에게 재설정 여부를 `AskUserQuestion`으로 묻는다. scalar 의심 신호는 — 라인 1개 + 값이 `true`/`false`/숫자/디렉토리로 해석되지 않는 단일 토큰 — 같은 휴리스틱으로 판정한다.

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
node .tack/scripts/dev-context.js set-field --field=config.graphify.targets --value='<JSON 배열>'
```

옵션 2(건너뛰기)를 선택하면 `set-field`를 호출하지 않고 Step 7에 `[정보] config.graphify.targets 미설정 유지`를 출력한다. 추후 `/graphify` 호출 시 hard error로 안내된다.

### Step 7: 결과 안내

작성된 파일 경로와 결과를 출력한다:

```
완료:
  [신규/업데이트/변경 없음] CLAUDE.md
  [신규/업데이트/변경 없음] AGENTS.md
  [감지] config.docs.sourceFilter = [".claude/",".codex/",".tack/","CLAUDE.md","AGENTS.md"]
  [감지] config.graphify.targets = ["./src","./docs/specs","scripts"]
```
(일반 프로젝트의 경우: `[감지] config.docs.sourceFilter = [] (필터 없음)`)

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

## 오류 처리

| 상황 | 처리 |
|------|------|
| `<!-- shared-rules:begin -->` 마커 없는 기존 CLAUDE.md 또는 AGENTS.md | Step 1에서 경고 + AskUserQuestion → 백업 후 재생성 or 중단 |
| `.tack/rules/` 없음 | CLAUDE.md·AGENTS.md begin/end 마커 사이를 빈 상태로 생성, 경고 출력 |
| 쓰기 권한 없음 | 오류 메시지 출력 후 종료 |
| Step 5: `dev-context.js` 미존재 또는 `set-field` 실패 | 경고 출력 + Step 5 스킵, Step 7에서 `[감지 실패] config.docs.sourceFilter` 표기 |
| Step 6: `dev-context.js` 미존재 또는 `set-field` 실패 | 경고 출력 + Step 6 스킵, Step 7에서 `[감지 실패] config.graphify.targets` 표기 |

## Key Principles

- **항상 루트 대상** — `src/` 여부와 관계없이 항상 루트 `CLAUDE.md`, `AGENTS.md`를 수정한다.
- **AskUserQuestion 사용 필수** — 선택이 포함된 모든 질문에 적용. 첫 옵션에 `(Recommended)` 레이블.
- **shared-rules 마커 기준 업데이트** — 두 파일 모두 공유 규칙 블록을 `<!-- shared-rules:begin -->` / `<!-- shared-rules:end -->` 마커 쌍으로 bound한다. 프로젝트 섹션은 begin 마커 직전까지로 정의되고, 마커 외부는 사용자 영역으로 보존된다. 마커 사이 시맨틱은 파일별로 다르다 — CLAUDE.md는 `@.tack/rules/<rel>` @import 포인터 목록, AGENTS.md는 `.tack/rules/` 본문 인라인.
- **`.tack/rules/` 단일 소스** — CLAUDE.md import 블록과 AGENTS.md 인라인 블록 모두 `.tack/rules/` glob 결과로 재생성된다. CLAUDE.md는 재귀 glob(typescript/ 포함), AGENTS.md는 top-level만 인라인한다.
- **저장소 유형 자동 감지** — `scripts/deploy-harness.sh` 존재 여부로 `config.docs.sourceFilter` 기본값을 결정한다 (하네스: prefix 목록 / 일반: 빈 배열). **기존 non-empty 값은 보존**한다 — `/flow-init`은 imports 재생성을 위해 재실행 가능하므로, 사용자 명시 설정을 재실행마다 덮어쓰지 않는다 (빈 배열·null·미설정일 때만 감지값 적용).
- **graphify targets 추천** — 배포 직후 `config.graphify.targets`가 미설정·빈 배열일 때 추천값을 `AskUserQuestion`으로 확정한다. 비어 있지 않은 기존 값은 보존한다 (멱등).
