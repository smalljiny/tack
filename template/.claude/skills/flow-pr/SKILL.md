---
version: 2
name: flow-pr
description: Push the current branch and create a GitHub Pull Request. Publish-only — run after /flow-docs so the reference document is included.
origin: harness
user-invocable: true
---

# /flow-pr

Push the current branch to the remote and create a GitHub Pull Request using the topic's spec and plan as context. This skill is **publish-only** — it performs no local file changes. All local work (including the reference document) must be committed before running this skill.

## Usage

```
/flow-pr    Push and open a PR for the current topic
```

Always operates on `current_topic`.

## Execution Flow

### 1. Read current topic and gate check

```bash
python3 .tack/scripts/dev_context.py read --field=current_topic
```

If `current_topic` is empty, stop:
```
PR을 생성할 토픽이 없습니다.
```

Read `phase` and `status`:
```bash
python3 .tack/scripts/dev_context.py read --topic=<topic> --field=phase
python3 .tack/scripts/dev_context.py read --topic=<topic> --field=status
```

Determine the entry mode based on `phase:status`:

| `phase:status` | Mode |
|---|---|
| `docs:generated` | First-run (create PR) |
| `pr:created` | Re-entry (update PR via `gh pr edit`) |
| anything else | Stop |

**Re-entry** (pr:created): before proceeding, confirm:
```
이미 PR이 생성되어 있습니다 (pr:created).
PR 제목과 body를 업데이트하시겠습니까? (y/n)
```
- `n`: stop
- `y`: proceed to Step 3 in update mode

**Stop** (any other state):
```
/flow-pr를 실행할 수 없습니다.
현재 상태: <phase>:<status>
docs:generated 상태여야 합니다.
먼저 /flow-docs를 실행하세요.
```

### 2. Gate: working tree clean and branch check

Check working tree:
```bash
git status --porcelain
```
If output is non-empty, stop:
```
⚠ 커밋되지 않은 변경사항이 있습니다.
git status를 확인하고 모든 변경사항을 commit한 후 다시 실행하세요.

삭제된 파일이 unstaged 상태인 경우:
  1. git status 로 삭제된 파일 목록 확인
  2. git rm <path>  또는  git add -u  로 삭제를 stage
  3. git commit -m "chore: remove <파일명>"
  4. /flow-pr 재실행

(세션 시작 전부터 존재하던 미커밋 파일 삭제도 동일한 방법으로 처리합니다.)
```

Read branch name:
```bash
git rev-parse --abbrev-ref HEAD
```

Read `config.git.branchPattern` (default: `^(feature|fix|chore)/`):
```bash
python3 .tack/scripts/dev_context.py read --field=config.git.branchPattern
```

If the current branch does not match the pattern, warn:
```
⚠ 현재 브랜치 '<branch>'가 허용 패턴 '<pattern>'에 맞지 않습니다.
계속하시겠습니까? (y/n)
```
- `n`: stop
- `y`: continue

### 3. Read config

```bash
python3 .tack/scripts/dev_context.py read --field=config.git.pushRemote
python3 .tack/scripts/dev_context.py read --field=config.git.pullRemote
python3 .tack/scripts/dev_context.py read --field=config.git.baseBranch
python3 .tack/scripts/dev_context.py read --topic=<topic> --field=baseBranch
```

Defaults:
- `pushRemote`: `origin`
- `pullRemote`: `origin`
- `baseBranch`: `main` (topic-level override takes precedence if set)

**Validate config-derived values before use**:
- Remote names (`pushRemote`, `pullRemote`): must match `^[a-zA-Z0-9_.-]+$` and must not start with `-`. Verify existence with `git remote get-url <remote>`; stop with an error if not found.
- Branch names (`baseBranch`, topic-level `baseBranch`): must match `^[a-zA-Z0-9][a-zA-Z0-9_/.-]*$` (leading `-` rejected). Verify with `git rev-parse --verify -- <branch>` before use in diff or PR creation commands.
- If any validation fails, stop immediately and show the invalid value and expected format.

### 4. Draft PR title

Read the implementation plan to extract Story Commit fields:
```bash
python3 .tack/scripts/dev_context.py read --topic=<topic> --field=plan
```

From the plan's Story blocks, extract all `**Commit**:` values. Parse `type` and `scope` from each. Find the most frequent `type` and `scope`.

Draft the PR title as:
```
<most-frequent-type>(<most-frequent-scope>): <topic-name-as-description>
```

If no Commit fields are found in the plan (pre-contract plans), use:
```
feat(<topic>): <topic-name-as-description>
```

Present the draft and ask for confirmation:
```
PR 제목 초안:
  <draft-title>

이 제목으로 진행하시겠습니까? (y/수정할 제목 입력)
```
- `y`: use draft
- Other input: use the entered title

Validate the confirmed title against Conventional Commits format:
`^(feat|fix|docs|refactor|test|chore|perf|ci)(\([a-z0-9_,.-]+\))?: .{1,72}$`
If invalid, warn and re-prompt.

### 5. Draft PR body

Load `.tack/templates/pr-body.md` and substitute placeholders:

| Placeholder | Value |
|---|---|
| `{{topic}}` | current topic name |
| `{{spec_link}}` | `topics[topic].spec` from dev-context.json |
| `{{reference_doc}}` | read from `topics[topic].refDoc` in dev-context.json (set by `/flow-docs` on save). If absent, fall back to `git log --diff-filter=AM -- docs/specs/ -1 --name-only` and validate the result matches `^docs/specs/[a-zA-Z0-9_-]+\.md$` before use. |
| `{{branch}}` | current branch |
| `{{base_branch}}` | resolved `baseBranch` |

Present the body and ask for confirmation:
```
PR body 초안 (아래에 표시):
---
<body content>
---

이 body로 진행하시겠습니까? (y/수정 사항 입력 또는 'edit'으로 직접 수정)
```
- `y`: use draft
- `edit`: open the draft in the user's editor or present a structured edit prompt
- Other input: append the input as additional context to the body

### 6. Push branch (first-run only)

**Skip this step entirely in re-entry (`pr:created`) mode.** In re-entry mode, jump directly to Step 7 to update the PR title/body via `gh pr edit`. Any new local commits must be published by returning to `docs:generated` state first:
```bash
python3 .tack/scripts/dev_context.py update-state --topic=<topic> --phase=docs --status=generated
```
Then re-run `/flow-docs` and `/flow-pr` in sequence.

**First-run only** (`docs:generated` mode):
```bash
git push -u <pushRemote> <branch>
```

**Failure handling**:
- If push fails due to authentication: show `gh auth status` output and stop. Do not transition state.
- If push fails for other reasons: show the error, suggest `git pull --rebase` if behind, and stop. Do not transition state.

### 7. Create or update PR

To extract `<pullRemote-owner>/<repo>`: run `git remote get-url <pullRemote>` and parse the GitHub path from the URL (supports HTTPS and SSH formats). Validate the extracted path against `^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$`.

**First run** (`docs:generated` mode) — use HEREDOC to avoid shell metacharacter injection:
```bash
gh pr create \
  --repo <pullRemote-owner>/<repo> \
  --base <baseBranch> \
  --title "<confirmed-title>" \
  --body "$(cat <<'PR_BODY'
<confirmed-body>
PR_BODY
)"
```

**Re-entry** (`pr:created` mode):
```bash
gh pr edit \
  --title "<confirmed-title>" \
  --body "$(cat <<'PR_BODY'
<confirmed-body>
PR_BODY
)"
```

**Never interpolate the title or body directly into a shell argument string.** Always use HEREDOC for `--body`. For `--title`, ensure the value is stripped of shell metacharacters (`"`, `$`, backticks) before use.

**Failure handling**:
- If `gh pr create` or `gh pr edit` fails:
  - If the error suggests authentication: run `gh auth status` and display the output.
  - Show the full error message.
  - Do not transition state. Stop.
  - Suggest: `gh auth login` if not authenticated.
- If PR already exists (conflict on create): detect and switch to `gh pr edit` automatically.

**Success**: Show the PR URL:
```
PR이 생성되었습니다: <pr-url>
```

### 8. Update state

```bash
python3 .tack/scripts/dev_context.py update-state \
  --topic=<topic> --phase=pr --status=created
```

Show completion:
```
완료되었습니다.
  PR:    <pr-url>
  상태:  pr:created

다음: PR이 병합되면 /flow-done 으로 아카이브하세요.
PR 수정이 필요하면 /flow-pr 을 다시 실행하세요 (docs:generated로 복귀 후 재push).
```

## Key Principles

- **Gate: docs:generated** — requires reference document to be committed before PR is created
- **Publish-only** — no local file changes; all commits must be done before this skill
- **Working tree must be clean** — stops if uncommitted changes are detected
- **Branch pattern check** — warns if branch name does not match `config.git.branchPattern`
- **Re-entry safe** — `pr:created` state triggers `gh pr edit` mode
- **Failure does not change state** — push or PR failures leave the topic at `docs:generated`
- **auth failure guidance** — `gh auth status` / `gh auth login` suggested on authentication errors

## Next Steps

After `/flow-pr` completes (`pr:created`):

- **PR 제목·body만 수정**: `/flow-pr` 재실행 — `pr:created` 상태에서 자동으로 re-entry(update) 모드로 진입해 `gh pr edit`을 실행한다.
- **참조 문서도 수정 필요**: `pr:created → docs:generated`로 상태를 복귀시킨 뒤 `/flow-docs`와 `/flow-pr`을 순서대로 실행한다.
  ```bash
  python3 .tack/scripts/dev_context.py update-state \
    --topic=<topic> --phase=docs --status=generated
  ```
  그 다음 `/flow-docs` (참조 문서 재생성 + commit) → `/flow-pr` (재push + PR 업데이트).
- **병합 후**: `/flow-done` 으로 아카이브하고 토픽을 제거한다.
