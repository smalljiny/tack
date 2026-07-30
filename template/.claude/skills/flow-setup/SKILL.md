---
version: 4
name: flow-setup
description: Configure project-level settings. Subcommand `git` auto-detects git remotes and saves config.git.* fields to the tracked shared config file .tack/config.json (a confirmed pullRemote of upstream goes to the local layer instead), used by /flow-pr, /flow-docs, and /flow-review.
origin: harness
user-invocable: true
---

# /flow-setup

Configure project-level settings. `config.git.*` is declared `shared` in the config schema, so values land in the tracked shared config file `.tack/config.json` (committed). One exception: a confirmed `pullRemote` of `upstream` is written to the git-ignored `.tack/local/dev-context.json` with `--layer=local`, because using a fork is that user's own circumstance (Step 9).

## Usage

```
/flow-setup git    Detect git remotes and save config.git.* fields
```

Running `/flow-setup` without a subcommand, or with an unrecognized subcommand, shows:
```
지원되는 서브커맨드: git
사용법: /flow-setup git
```

## Execution Flow

### 1. Subcommand dispatch

Read `$ARGUMENTS`. If the value is not `git`, print the supported-subcommand message and stop. No side effects.

If `$ARGUMENTS == "git"`, continue to Step 2.

### 2. Detect remotes

```bash
git remote -v
```

Parse the unique remote names from the output. If `origin` is not present, stop:
```
origin remote이 없습니다. git remote add origin <url> 로 먼저 추가하세요.
```

### 3. Classify pattern and propose values

**Fork pattern** — `upstream` remote exists alongside `origin`:

First verify that `upstream` is reachable:
```bash
git ls-remote --heads upstream 2>/dev/null
```
If the command exits 0 (reachable), propose:
```
원격 저장소 감지: Fork 패턴 (upstream 연결 확인됨)
  pushRemote  = origin   (feature 브랜치를 fork에 push)
  pullRemote  = upstream (PR diff 기준은 원본 레포 — 이 휴리스틱이 맞지 않으면 Step 8에서 수정 가능)
```
If `upstream` exists but is unreachable, warn and downgrade to Non-fork:
```
⚠ upstream remote가 존재하지만 연결할 수 없습니다. Non-fork 패턴으로 fallback합니다.
  원인 확인 후 /flow-setup git 을 다시 실행하세요.
```

**Non-fork pattern** — only `origin` (or `upstream` unreachable):
```
원격 저장소 감지: 단일 remote 패턴
  pushRemote  = origin
  pullRemote  = origin
```

### 4. Detect baseBranch (best-effort)

```bash
# Try cached ref first (no network)
git symbolic-ref refs/remotes/<pullRemote>/HEAD 2>/dev/null | sed 's|.*/||'
```

If the cached ref is present, use it. Otherwise try the network (may be slow on poor connections):
```bash
LC_ALL=C git remote show <pullRemote> 2>/dev/null | grep "HEAD branch" | sed 's/.*HEAD branch: //'
```

If either command succeeds and returns a non-empty value, use it as the proposed `baseBranch`. Otherwise propose `main`.

### 5. Propose branchPattern

Use `^(feature|fix|chore)/` as the default — same value used by `/flow-pr` when `config.git.branchPattern` is not set.

### 6. Validate detected values

Before presenting to the user, validate each value:

**Remote names** (`pushRemote`, `pullRemote`):
- Must match `^[a-zA-Z0-9_.-]+$` and must not start with `-`
- Must be reachable: `git remote get-url <remote>` must exit 0

**Branch name** (`baseBranch`):
- Must match `^[a-zA-Z0-9][a-zA-Z0-9_/.-]*$` (leading `-` rejected)
- Must NOT contain `..` (path traversal) — reject before any git command
- Must exist on the remote: `git rev-parse --verify -- refs/remotes/<pullRemote>/<baseBranch>` must exit 0
- If the ref is not cached locally, fetch first:
  ```bash
  git fetch <pullRemote> <baseBranch> --no-tags 2>/dev/null
  ```
  If fetch fails (e.g. network unavailable), warn and fall back to `main` with a note:
  ```
  ⚠ <pullRemote>/<baseBranch> 확인 실패. main을 기본값으로 제안합니다. Step 8에서 수정 가능합니다.
  ```

**branchPattern** (regex string):
- Must not be empty
- Must NOT be exactly `true`, `false`, or a bare integer string — these would be coerced to boolean/number by `set-field` (via `dev_context.py coerce_config_value`). `set-field`도 같은 값을 거부한다 — `config.git.branchPattern`은 스키마에 `string` 타입으로 선언돼 있어 boolean·integer로 추론된 값이 타입 검사에서 non-zero exit으로 막힌다. 이 검증은 사용자에게 원인을 먼저 보여주기 위한 선행 게이트다.
- Must be a valid regular expression. Claude validates this internally without shell interpolation: attempt `new RegExp(<branchPattern>)` as a JS expression. If it throws, show the error and stop without calling `set-field`. Do NOT use shell commands to validate regex — avoids shell metacharacter injection from user-provided pattern values.
- Note: ReDoS-vulnerable patterns (e.g. `^(a+)+$`) pass syntactic validation. Document scope is branch-name patterns — guide users toward simple anchored patterns like `^(feature|fix|chore)/`.

If any validation fails, show the invalid value and expected format, then stop without calling `set-field`.

### 7. Check existing config

Read the current values:
```bash
python3 .tack/scripts/dev_context.py read --field=config.git.pushRemote
python3 .tack/scripts/dev_context.py read --field=config.git.pullRemote
python3 .tack/scripts/dev_context.py read --field=config.git.baseBranch
python3 .tack/scripts/dev_context.py read --field=config.git.branchPattern
```

When reading each field, an empty line from `dev_context.py read` (trimmed to `""`) means the field is unset — render as `(미설정)`. `read`는 local 층을 먼저 보고 없을 때만 공유 층을 보므로, 표시되는 값은 두 층이 병합된 결과다. "All four are empty" means all four reads returned empty strings.

If any of the four values is non-empty, show the current block (unset fields display as `(미설정)`):
```
현재 저장된 config.git 값:
  pushRemote   : <value or (미설정)>
  pullRemote   : <value or (미설정)>
  baseBranch   : <value or (미설정)>
  branchPattern: <value or (미설정)>

덮어쓰시겠습니까? (y/n)
```
덮어쓰기는 공유 층(`.tack/config.json`)에 적용된다 — 확정값이 `upstream`인 `pullRemote`만 개인 층에 적용된다. 개인 오버라이드가 있는 키는 `y`를 선택해도 표시 값이 바뀌지 않는다 (개인 층이 읽기 우선순위를 갖는다).
- `n`: stop without changes
- `y`: continue to Step 8

If all four are empty (all `(미설정)`), skip this step and go directly to Step 8.

### 8. Present and confirm

Show the proposed values and ask for confirmation:
```
감지된 git 설정:
  pushRemote   : <value>
  pullRemote   : <value>
  baseBranch   : <value>
  branchPattern: <value>

이 값으로 저장하시겠습니까? (y/n 또는 수정할 필드명=값 입력)
```

- `y`: save all four values (proceed to Step 9)
- `n`: stop without changes
- `<field>=<value>` input: update that field in the proposed set, re-validate, re-display. Repeat until `y` or `n`.

**Field edit parsing rules**:
- Allowed field names (whitelist): `pushRemote`, `pullRemote`, `baseBranch`, `branchPattern`
- Parse on the **first `=`** only — everything after the first `=` is the value. This handles `branchPattern=^(feature|fix)/` correctly (value contains `=` and `(`)
- Example: `branchPattern=^(feature|fix|chore)/` → field=`branchPattern`, value=`^(feature|fix|chore)/`
- Unknown field name (not in whitelist): show `알 수 없는 필드입니다. 허용 필드: pushRemote, pullRemote, baseBranch, branchPattern` and re-prompt
- Re-validate the updated value using the same rules from Step 6 before accepting. If validation fails, keep the previous proposed value unchanged and re-prompt

### 9. Save to the tracked shared config file

`config.git.*` 4개 키는 스키마에서 `shared` layer로 선언돼 있으므로 `set-field`가 **`.tack/config.json`** 에 기록한다. 이 파일은 tracked이며 **커밋 대상**이다 — 저장한 값은 팀 전체가 공유한다. 라우팅은 스키마가 결정하므로 아래 세 호출은 플래그 없이 기본 라우팅을 쓴다.

```bash
python3 .tack/scripts/dev_context.py set-field --field=config.git.pushRemote   --value='<pushRemote>'
python3 .tack/scripts/dev_context.py set-field --field=config.git.baseBranch   --value='<baseBranch>'
python3 .tack/scripts/dev_context.py set-field --field=config.git.branchPattern --value='<branchPattern>'
```

`pullRemote`의 목적지는 **Step 8에서 확정된 값**이 결정한다. Step 3의 패턴 분류가 아니라 확정값을 본다 — Step 8의 `pullRemote=<value>` 편집이 분류를 뒤집을 수 있고, Step 3이 `upstream`을 감지했어도 연결 불가로 Non-fork로 fallback하면 확정값은 `origin`이다.

| 확정된 `pullRemote` | 호출 형태 | 목적지 |
|---|---|---|
| 문자열 `upstream`과 정확히 일치 | `--layer=local` 추가 | `.tack/local/dev-context.json` (git-ignored) |
| 그 외 모든 값 (`origin` 등) | 플래그 없음 (기본 라우팅) | `.tack/config.json` (tracked) |

두 호출은 배타적이다. 확정값에 해당하는 **한 쪽만** 실행한다.

확정값이 `upstream`이면 이 호출만 실행한다 — fork 사용은 그 사용자의 사정이므로 개인 층에 기록한다:

```bash
python3 .tack/scripts/dev_context.py set-field --field=config.git.pullRemote --layer=local --value='<pullRemote>'
```

확정값이 `upstream`이 아니면 이 호출만 실행한다 — 팀 공통 값이므로 공유 층에 기록한다:

```bash
python3 .tack/scripts/dev_context.py set-field --field=config.git.pullRemote --value='<pullRemote>'
```

`upstream`을 공유 층에 쓰지 않는 이유: tracked 파일에 들어가면 fork를 쓰지 않는 팀원이 `pullRemote=upstream`을 상속해 PR diff 기준이 어긋난다. 두 호출을 모두 실행하면 개인 층 값이 공유 층 값을 가려, tracked 파일에 `upstream`이 들어간 사실이 read-back에서 보이지 않는다.

**`--layer` 개인 오버라이드**: `--layer`는 `set-field`의 `config.<namespace>.<key>` 쓰기에만 쓰는 플래그이며 값은 `local`과 `shared` 둘뿐이다. `local`은 `.tack/local/dev-context.json`(git-ignored)에, `shared`는 `.tack/config.json`(tracked)에 기록한다. `shared` layer로 선언된 키는 두 값을 모두 받으므로, 팀 값을 건드리지 않고 자기 머신에서만 다른 값을 쓰려면 `--layer=local`을 붙인다.

예시 (이 스킬은 실행하지 않는다 — 사용자가 직접 쓰는 형태):

```bash
python3 .tack/scripts/dev_context.py set-field --field=config.git.baseBranch --layer=local --value='<value>'
```

`read`는 local을 먼저 보고 없을 때만 공유 층을 보므로 개인 오버라이드가 이긴다. `/flow-setup git` 재실행은 `pushRemote`·`baseBranch`·`branchPattern`의 경우 공유 층만 갱신하므로 **개인 오버라이드 값을 덮지 않는다**. `pullRemote`은 예외다 — 확정값이 `upstream`이면 이 스킬이 개인 층에 직접 쓰므로 기존 개인 값이 갱신된다. `local`·`cache` layer로 선언된 키에 `--layer=shared`를 붙이면 거부된다 — 개인 설정·감지 캐시가 커밋되는 것을 막는 장치다.

No `--topic` flag — these are global project settings.

If any `set-field` call fails, show the error and stop. 이미 성공한 필드는 각자의 목적지 파일에 남는다 (`.tack/config.json`, `--layer=local`로 쓴 필드는 `.tack/local/dev-context.json`). `/flow-setup git`을 다시 실행해 남은 필드를 완료하거나 값을 고친다. 단, 공유 층 쓰기가 `.tack/config.json` 파싱 실패로 중단된 경우에는 재실행해도 같은 지점에서 멈추므로 그 파일을 먼저 고친다 — `set-field`는 파싱하지 못한 tracked 파일을 단일 키로 덮어쓰지 않고 중단한다.

### 10. Confirm saved values

Read back and display the saved values so the user can verify:
```bash
python3 .tack/scripts/dev_context.py read --field=config.git.pushRemote
python3 .tack/scripts/dev_context.py read --field=config.git.pullRemote
python3 .tack/scripts/dev_context.py read --field=config.git.baseBranch
python3 .tack/scripts/dev_context.py read --field=config.git.branchPattern
```

`read`가 내는 값은 local → shared 병합 결과다. **관측된 출처로 표기한다** — 방금 쓴 값과 관계없이, 네 키를 각각 다음 규칙으로 판정한다:

| 조건 | 표기 | 의미 |
|---|---|---|
| `read` 값이 방금 쓴 값과 같고 공유 층에 썼다 | 표기 없음 | `.tack/config.json` (tracked) |
| `read` 값이 방금 쓴 값과 같고 `--layer=local`로 썼다 | `(개인 층)` | `.tack/local/dev-context.json` — 커밋 대상 아님 |
| `read` 값이 방금 쓴 값과 **다르다** | `(개인 층 오버라이드 — 공유 층 값은 <written>)` | 기존 개인 오버라이드가 이기고 있다 |

세 번째 행은 공유 층 갱신이 성공했음에도 개인 값이 계속 서빙되는 상태다. 의도된 우선순위이지만 방치하면 stale이 된다 — 개인 오버라이드를 걷어내려면 `.tack/local/dev-context.json`의 `config.git.<key>` leaf를 지운다고 안내한다.

Show:
```
저장 완료:
  pushRemote   : <value>
  pullRemote   : <value>
  baseBranch   : <value>
  branchPattern: <value>

이제 /flow-pr, /flow-docs, /flow-review가 이 값을 사용합니다.
```

각 줄에 위 표의 표기를 덧붙인다. 표기 없는 줄이 `.tack/config.json`(tracked, 커밋 대상)에 저장된 값이다.

## Key Principles

- **Validation before save** — remote names and branch name are validated before any `set-field` call; never write an invalid value
- **Explicit confirmation required** — the user must type `y` before values are saved
- **Overwrite protection** — if existing values are present, the user is shown them and must confirm before overwriting
- **No SessionStart automation** — `/flow-setup git` must be run explicitly; no hook auto-detection
- **Global config** — `set-field` calls use no `--topic` flag; these values are project-wide
- **Shared destination by schema** — `config.git.*`는 `shared` layer라 `.tack/config.json`(tracked, 커밋 대상)에 기록된다. 라우팅은 스키마가 결정하므로 팀 공통 값 3개는 플래그 없이 호출한다
- **Fork pullRemote stays personal** — 확정된 `pullRemote`이 문자열 `upstream`과 정확히 일치하면 `--layer=local`로 기록해 개인 fork 사정이 팀 파일에 들어가지 않게 한다. 판정 기준은 Step 3의 분류가 아니라 Step 8에서 확정된 값이며, 두 호출 중 한 쪽만 실행한다
- **Read-back marks the observed layer** — Step 10은 방금 쓴 값이 아니라 `read` 결과와의 일치 여부로 층을 표기한다. 기존 개인 오버라이드가 공유 층 갱신을 가리는 상태를 사용자가 볼 수 있어야 한다
- **Fork detection heuristic** — presence of `upstream` remote is the sole fork signal; other remote names are ignored
