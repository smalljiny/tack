---
version: 2
name: flow-docs
description: Reconcile spec with implementation, update existing docs/specs/ files (or create new ones), and commit. Run before /flow-pr.
origin: harness
user-invocable: true
---

# /flow-docs

Reconcile the topic spec with actual implementation, update existing `docs/specs/` files that were affected, and commit all changes in a single commit. Run before `/flow-pr`.

## Usage

```
/flow-docs    Run for the current topic
```

Always operates on `current_topic`.

## Execution Flow

### 1. Read current topic and gate check

```bash
node .harness/scripts/dev-context.js read --field=current_topic
```

If `current_topic` is empty, stop:
```
참조 문서를 생성할 토픽이 없습니다.
```

Read `phase` and `status`:

```bash
node .harness/scripts/dev-context.js read --topic=<topic> --field=phase
node .harness/scripts/dev-context.js read --topic=<topic> --field=status
```

Determine the entry mode based on `phase:status`:

| `phase:status` | Mode |
|---|---|
| `review:in-progress` | First-run |
| `docs:generated` | Re-entry (re-run entire flow) |
| anything else | Stop |

**Re-entry** (`docs:generated`):
```
docs:generated 상태입니다. 다시 실행하시겠습니까? (y/n)
```
- `n`: stop
- `y`: proceed (will create a new commit — amend is forbidden)

### 2. Check /flow-verify status

Look for evidence that `/flow-verify` has recently passed (e.g., a recent passing run in the session context).
If no passing verification is found:
```
⚠ /flow-verify가 통과되지 않았습니다. 계속하시겠습니까? (y/n)
```
- `n`: stop
- `y`: continue

### 3. Collect changed files (git diff)

Read git config:
```bash
node .harness/scripts/dev-context.js read --field=config.git.baseBranch
node .harness/scripts/dev-context.js read --field=config.git.pullRemote
```

Use defaults if not set: `baseBranch=main`, `pullRemote=origin`.

Read the source filter configuration:
```bash
node .harness/scripts/dev-context.js read --field=config.docs.sourceFilter
```
Parse the output as a line-by-line list of path prefixes: split by `\n`, filter out empty strings. Store as `sourceFilter`. If no non-empty lines remain, `sourceFilter` is an empty list (no filter).

> **Migration note**: If `config.docs.sourceFilter` has never been set (e.g., upgrading from a version without this feature), the result is an empty `sourceFilter` and all changed files are included. For harness repositories, run `/flow-init` once to auto-configure the correct filter.

**sourceFilter application rule** (used at both filter points below):
- If `sourceFilter` is empty: include all files (no filtering).
- If `sourceFilter` is non-empty: keep only files whose path starts with at least one of the listed prefixes.

Collect changed files from all three sources and deduplicate:

1. `git diff <pullRemote>/<baseBranch>...HEAD --name-only` — committed changes
2. `git diff --name-only` — unstaged working tree changes
3. `git diff --cached --name-only` — staged changes

Merge the three lists and remove duplicates. Apply the **sourceFilter application rule**.

**If all three sources are empty**:
```
git diff 결과가 비어 있습니다.
베이스 브랜치를 입력하세요 (기본값: <baseBranch>):
```
Validate the user-provided branch name against `^[a-zA-Z0-9][a-zA-Z0-9_/.-]*$` before using it (leading `-` is rejected to prevent option injection). If invalid, re-prompt. Then verify the branch exists (`git rev-parse --verify -- <branch>`); if not found, show an error and stop. Then re-run the three diff sources with this branch as base and re-apply the **sourceFilter application rule**.

**If no files found after filtering**:

- If `sourceFilter` was empty (no filter applied):
  ```
  ⚠ 변경된 파일이 없습니다.
  계속하시겠습니까? (y/n)
  ```
- If `sourceFilter` was non-empty (filter applied):
  ```
  ⚠ 변경된 파일이 없습니다 (sourceFilter 적용됨).
  계속하시겠습니까? (y/n)
  ```
- `n`: stop
- `y`: proceed to Step 4 with an empty change set

### 4. Spec reconciliation

Read `docs/_local/active/<topic>/spec.md`. Compare its contents against the collected changed files to identify discrepancies — things implemented but not described in the spec, or spec items that were not implemented.

**If discrepancies found**: first classify each discrepancy — mark items that would alter implementation goals with `⚠ 구현 목표 변경`. Then present the list:

```
스펙-구현 불일치 항목:
  - [불일치 항목 1]
  - [불일치 항목 2]  ⚠ 구현 목표 변경
```

If any item is marked `⚠ 구현 목표 변경`, stop immediately without showing the approval prompt:
```
⚠ 스펙 수정이 구현 목표를 변경합니다.
/flow-docs를 중단합니다. /flow-plan 또는 /flow-review부터 재검토하세요.
```

If no goal-level changes exist, show the approval prompt:
```
spec.md에 반영하시겠습니까? (y/n)
```
- `y`: apply all listed discrepancies to `spec.md` and save. Note: corrections only (typos, missing details, wording) do not require re-running `specReview`, `planReview`, or `implementation-plan.md`.
- `n`: skip spec update and proceed to Step 5

**If no discrepancies**: print `스펙-구현 불일치 없음.` and proceed to Step 5 automatically.

### 5. Identify docs/specs/ files to update

Analyze the collected changed files and the (updated) spec to infer which existing `docs/specs/` files need updating. Present candidates with brief reasoning:

```
업데이트 대상 후보:
  1. docs/specs/foo.md — [이유]
  2. docs/specs/bar.md — [이유]
  3. (신규 생성 필요) baz.md — [이유: 기존 파일 없음]

승인하시겠습니까?
  y          : 위 목록대로 진행
  - <번호>   : 해당 후보 제거 (예: `- 2`)
  + <경로>   : 후보 추가 (예: `+ docs/specs/qux.md`)
  edit       : 목록 전체 재입력
```

- `y`: proceed with the proposed list
- `- <번호>`: remove that candidate and re-confirm
- `+ <경로>`: add a file and re-confirm
- `edit`: user provides a new list from scratch, then re-confirm

**If zero existing-file candidates** (all content is new): use the same new-file flow as below.

**If new file creation is needed** (no existing file covers the content): for each new file, sequentially propose a filename:
```
신규 파일명을 제안합니다: <suggested-name>.md
이 이름으로 저장하시겠습니까? (y/다른 이름 입력)
```
Validate against `^[a-zA-Z0-9_-]+\.md$` — if invalid, re-prompt.
If `docs/specs/<name>.md` already exists:
```
docs/specs/<name>.md가 이미 존재합니다.
덮어쓰시겠습니까? (y/다른 이름 입력)
```
- `y`: overwrite
- Other input: use new name (re-validate)

### 6. Update each file

For each file in the approved list, apply the following heuristic in order:

**Partial update** (apply when ALL of the following hold):
- Affected headings are 1–2 or fewer
- The existing document's section structure (heading hierarchy) is preserved
- Changes are confined to specific sections

**Full rewrite** (apply when ANY of the following holds):
- The target heading cannot be found in the existing document — switch to full rewrite immediately, **no fuzzy matching**
- Half or more of the document's headings are affected
- The section structure itself must change

Full rewrite format (present tense, no migration guides, change history, Open Questions, or Before/After comparisons):

```markdown
# <System Subject Name>

> <One-line summary>

## 개요
[What the system is and what role it plays]

## 구조 / 스키마
[Current directory structure, data formats, etc.]

## 동작
[How commands, skills, and rules work]

## 제약사항
[Current constraints]
```

For full rewrites where the scope is large, invoke the `doc-updater` agent (reads spec, plan, and `git diff`) to produce the initial draft instead of drafting directly.

### 7. Select representative document and record refDoc

After all files are updated or created, select the representative document for `refDoc`:

- **1 file updated/created**: select it automatically without prompting.
- **2 or more files**: call `AskUserQuestion` with one option per updated/created file. The first option carries the `(Recommended)` marker — assign it to a newly created file if one exists, otherwise to the file with the largest diff size. Use the file path as the option label.

Record the selected path:
```bash
node .harness/scripts/dev-context.js set-field \
  --topic=<topic> --field=refDoc \
  --value=docs/specs/<selected>.md
```

Show:
```
대표 문서: docs/specs/<selected>.md
```

### 8. Commit

Stage all updated and newly created `docs/specs/` files. Do **not** stage `spec.md` (it lives in `docs/_local/` which is git-ignored).

```bash
git add docs/specs/<file1>.md docs/specs/<file2>.md ...
```

Determine commit message:
- **First-run** (`review:in-progress`): `docs: add <representative-name> reference`
- **Re-entry** (`docs:generated`): `docs: update <representative-name> reference`

**amend is forbidden** — always create a new commit. Use HEREDOC to avoid shell metacharacter injection:

```bash
git commit -m "$(cat <<'COMMIT_MSG'
docs: add <representative-name> reference
COMMIT_MSG
)"
```

**Failure behavior**: If `git add` or `git commit` fails, do not transition state. Show the error and stop. The skill is re-entrant safe — run `/flow-docs` again after resolving the issue.

### 9. Update state

```bash
node .harness/scripts/dev-context.js update-state \
  --topic=<topic> --phase=docs --status=generated
```

Show completion:
```
완료되었습니다.
  업데이트된 파일: docs/specs/foo.md, docs/specs/bar.md
  대표 문서:      docs/specs/<representative-name>.md
  상태:           docs:generated

다음: /flow-pr 로 PR을 생성하세요.
```

## Key Principles

- **Gate: review:in-progress** — `/flow-docs` only proceeds when `phase=review && status=in-progress` (or re-entry from `docs:generated`)
- **Spec reconciliation first** — update `spec.md` before touching `docs/specs/`, so the corrected spec drives the document update
- **Existing files first** — update existing `docs/specs/` files before creating new ones; create new files only when no existing file covers the content
- **Partial update preferred** — use section-level edits when 1–2 headings are affected and structure is preserved; full rewrite otherwise
- **No fuzzy matching** — if a target heading is not found exactly, switch to full rewrite immediately
- **Single commit** — all `docs/specs/` changes in one atomic commit; `spec.md` is git-ignored and never committed here
- **Goal-change aborts** — if spec reconciliation would alter implementation goals, stop immediately and redirect to `/flow-plan` or `/flow-review`
- **refDoc is a single path** — always one representative document; `/flow-pr` contract requires a single path
- **amend forbidden** — re-entry creates a new commit, never amends
- **Failure is safe** — state does not transition on error; re-run after fixing
- **diff base from config** — uses `config.git.pullRemote`/`config.git.baseBranch` (defaults: `origin`/`main`)
- **sourceFilter from config** — file filter is externalized to `config.docs.sourceFilter`; unset or empty array means no filter (full diff used); both are treated identically

## Next Steps

After `/flow-docs` completes (`docs:generated`): run `/flow-pr` to push and open the PR.
