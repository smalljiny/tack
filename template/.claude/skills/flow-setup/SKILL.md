---
version: 2
name: flow-setup
description: Configure project-level settings in dev-context.json. Subcommand `git` auto-detects git remotes and saves config.git.* fields used by /flow-pr, /flow-docs, and /flow-review.
origin: harness
user-invocable: true
---

# /flow-setup

Configure project-level settings in `dev-context.json`.

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
- Must NOT be exactly `true`, `false`, or a bare integer string — these would be coerced to boolean/number by `set-field` (via `dev-context.js coerceConfigValue`)
- Must be a valid regular expression. Claude validates this internally without shell interpolation: attempt `new RegExp(<branchPattern>)` as a JS expression. If it throws, show the error and stop without calling `set-field`. Do NOT use shell commands to validate regex — avoids shell metacharacter injection from user-provided pattern values.
- Note: ReDoS-vulnerable patterns (e.g. `^(a+)+$`) pass syntactic validation. Document scope is branch-name patterns — guide users toward simple anchored patterns like `^(feature|fix|chore)/`.

If any validation fails, show the invalid value and expected format, then stop without calling `set-field`.

### 7. Check existing config

Read the current values:
```bash
node .harness/scripts/dev-context.js read --field=config.git.pushRemote
node .harness/scripts/dev-context.js read --field=config.git.pullRemote
node .harness/scripts/dev-context.js read --field=config.git.baseBranch
node .harness/scripts/dev-context.js read --field=config.git.branchPattern
```

When reading each field, an empty line from `dev-context.js read` (trimmed to `""`) means the field is unset — render as `(미설정)`. "All four are empty" means all four reads returned empty strings.

If any of the four values is non-empty, show the current block (unset fields display as `(미설정)`):
```
현재 저장된 config.git 값:
  pushRemote   : <value or (미설정)>
  pullRemote   : <value or (미설정)>
  baseBranch   : <value or (미설정)>
  branchPattern: <value or (미설정)>

덮어쓰시겠습니까? (y/n)
```
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

### 9. Save to dev-context.json

```bash
node .harness/scripts/dev-context.js set-field --field=config.git.pushRemote   --value='<pushRemote>'
node .harness/scripts/dev-context.js set-field --field=config.git.pullRemote   --value='<pullRemote>'
node .harness/scripts/dev-context.js set-field --field=config.git.baseBranch   --value='<baseBranch>'
node .harness/scripts/dev-context.js set-field --field=config.git.branchPattern --value='<branchPattern>'
```

No `--topic` flag — these are global project settings.

If any `set-field` call fails, show the error and stop. The fields saved before the failure remain in dev-context.json; run `/flow-setup git` again to complete or correct all four fields.

### 10. Confirm saved values

Read back and display the saved values so the user can verify:
```bash
node .harness/scripts/dev-context.js read --field=config.git.pushRemote
node .harness/scripts/dev-context.js read --field=config.git.pullRemote
node .harness/scripts/dev-context.js read --field=config.git.baseBranch
node .harness/scripts/dev-context.js read --field=config.git.branchPattern
```

Show:
```
저장 완료:
  pushRemote   : <value>
  pullRemote   : <value>
  baseBranch   : <value>
  branchPattern: <value>

이제 /flow-pr, /flow-docs, /flow-review가 이 값을 사용합니다.
```

## Key Principles

- **Validation before save** — remote names and branch name are validated before any `set-field` call; never write an invalid value
- **Explicit confirmation required** — the user must type `y` before values are saved
- **Overwrite protection** — if existing values are present, the user is shown them and must confirm before overwriting
- **No SessionStart automation** — `/flow-setup git` must be run explicitly; no hook auto-detection
- **Global config** — `set-field` calls use no `--topic` flag; these values are project-wide
- **Fork detection heuristic** — presence of `upstream` remote is the sole fork signal; other remote names are ignored
