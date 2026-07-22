---
version: 1
name: wf-worktree-context
description: Provision an isolated sibling git worktree for a confirmed topic and inject the git-untracked harness context (shared tooling symlinks, .harness copy, per-worktree docs/_local, spec/plan handoff copy, env, dev-context isolation), then tear it down with a docs/_local/done sync-back. Use when a topic moves to worktree-rooted implementation so /flow-* runs isolated from the main hub's dev-context, or when removing such a worktree. Not for browser/cmux control — pane targeting stays with the caller.
origin: harness
---

# wf-worktree-context

토픽 하나를 repo 밖 sibling worktree 에서 격리 작업하기 위해, git-미추적 하네스 컨텍스트를 주입한다. 하네스(`.claude`·`.harness`·`.codex` 등)가 git-미추적인 프로젝트에서는 fresh worktree 체크아웃에 이들이 없다. 이 스킬이 실증 교정된 매니페스트대로 주입·핸드오프·부트스트랩하고, 종료 시 아카이브를 메인으로 sync-back 한다.

정본 근거: 원 출처 marketing-strategist(2026-07-03/07-06 실증 교정) → muhan → 하네스 정본. 프로젝트별 차이(어떤 컨텍스트가 tracked 인지, `.serena`·`.secrets` 유무 등)는 **자동 적응**되므로 매니페스트 하드코딩·분기가 없다(아래 참조).

Boundary: 이 스킬은 worktree 프로비저닝·teardown 만 한다. `git worktree add`/`remove`·컨텍스트 주입·생성물 복원·sync-back 이 범위다. 대상 터미널(cmux surface) 지정·Claude 세션 기동은 호출자 소관이다.

## When to Activate

- 토픽이 `spec:confirmed`·`plan:confirmed` 이후로 worktree-rooted 구현에 들어갈 때
- 병렬 토픽을 각자 worktree(dev-context 격리)로 진행할 때
- worktree 작업이 끝나(`pr:created`·`/flow-done` 후) worktree 를 제거할 때 — teardown 으로 아카이브 sync-back 선행

## Provisioning Manifest

각 대상의 주입 방식과 근거. 2개 실증 블로커가 방식을 결정하고, tracked 여부는 프로젝트마다 자동 적응된다.

| 대상 | 방식 | 근거 |
|------|------|------|
| `.claude`·`.codex`·`.agents`·`.mcp.json`·`AGENTS.md`·`CLAUDE.md`·`.serena` | symlink→main (자동) | 큰 공유 툴링. 읽기 전용/cwd 기준 경로라 symlink 안전. **자동 적응**: `git worktree add` 가 git-tracked 항목을 이미 체크아웃하므로, tracked 컨텍스트(예: 커밋된 `CLAUDE.md`)는 `link()` 의 존재 검사가 skip 하고 gitignored/absent 항목만 symlink 된다. main 에 없는 항목도 self-skip |
| `.harness` | copy | 🔴blocker-2: `.harness/scripts/dev-context.js` 가 `join(__dirname, '../../docs/_local/dev-context.json')` 로 경로 계산 → symlink 면 node 가 `__dirname` 을 main 으로 해석해 worktree 실행이 main dev-context 를 읽어 격리 붕괴. copy 면 실경로. tracked 면 worktree add 가 실파일로 제공 → skip |
| `.secrets` | copy | 값 변경 격리. never-tracked → 있으면 copy(멱등·guard) |
| `docs/_local/{backlog,active,done}` | per-worktree 실디렉토리 | 🔴blocker-1: codex `workspace-write` 샌드박스가 worktree 밖으로 나가는 symlink 쓰기를 차단. plan-review·adversarial 산출물을 여기 씀 |
| `docs/_local/<stage>/<topic>/` (spec·spec-review·plan…) | copy 핸드오프 | docs/_local 이 symlink 가 아니라 main→worktree copy. 토픽이 있는 stage 자동 탐지 |
| `docs/_local/dev-context.json` | per-worktree | flow 상태 격리. main 사본으로 init(상대경로 그대로 해석). main 에 없으면(`/flow-spec` 전) skip + WARN |
| `node_modules` | 재생성 | `pnpm install`. `package.json` 없으면 skip |

- **base = `develop`** (기본). 배치는 `<repo>.worktrees/<topic>`, 브랜치 `feature/<topic>`. base 브랜치가 없으면 `--base <branch>` 로 지정한다(스크립트가 `rev-parse --verify` 로 선체크).
- **git status 누출**: 공용 `$MAIN/.git/info/exclude`(브랜치 독립·전 worktree 적용)에 **실제 주입한 항목만** slash-less 로 등록해 `?? .claude` 노출을 막는다. 커밋된 `.gitignore` 상태와 무관하게 동작한다. tracked 항목은 주입되지 않으므로 exclude 에도 들어가지 않는다(정상 변경이 exclude 로 가려지는 사고 없음). `provision.sh` 가 멱등 보장.

## Procedure — Provision

### Step 1 — 전제 확인

토픽이 dev-context 에 등록되고 확정 단계인지 확인한다. `phase:status` 가 `spec:confirmed` 이상이면 진행한다.

```bash
node .harness/scripts/dev-context.js read --topic=<topic> --field=phase
node .harness/scripts/dev-context.js read --topic=<topic> --field=status
```

### Step 2 — 프로비저닝 실행

번들 스크립트를 실행한다. 멱등이라 재실행 시 누락분만 채운다.

```bash
bash .claude/skills/wf-worktree-context/scripts/provision.sh <topic>
# 옵션: --base <branch>(기본 develop) --main <path>
```

스크립트가 수행: worktree 생성 → symlink/copy 주입(tracked 자동 skip) → 토픽 산출물+dev-context 핸드오프 → 공용 exclude 보정(주입분만) → `pnpm install`(package.json 있으면) → 알려진 stale lockfile drift revert → 격리 프로브+git status 출력.

### Step 3 — 검증

스크립트 말미 출력 두 줄을 확인한다.

- isolation probe: `current_topic` 이 대상 토픽으로 나오면 blocker-2 격리 정상(worktree 가 자신의 dev-context 를 읽음).
- git status: **clean** 이면 통과. `?? .claude` 등이 보이면 공용 exclude 보정 실패 — `.git/info/exclude` 에 slash-less 항목 확인.

### Step 4 — worktree-rooted 세션 기동 (호출자)

프로비저닝 후 그 worktree 디렉토리에서 Claude 세션을 연다. cmux 대상 pane 이 지정됐으면 호출자가 `cmux send`/`send-key` 로 `cd <worktree> && claude` 를 보낸다. 세션 상태줄에 토픽 pin 이 뜨면 dev-context 격리 확인.

## Operating Rule

worktree 프로비저닝 후 그 토픽의 `/flow-*` 는 **worktree-rooted 세션에서만** 실행한다. main hub 세션에서 그 토픽의 `/flow-plan`·`/flow-impl` 등을 돌리면 main dev-context 를 건드려 격리가 깨진다. main hub 는 `/flow-spec`(탐색적·리뷰 루프성) 까지만 담당하고, plan 이후는 worktree 세션이 소유한다.

## Procedure — Teardown

worktree 제거 전 아카이브를 메인으로 sync-back 한다. `docs/_local` 이 per-worktree 실디렉토리라, `/flow-done` 이 만든 `docs/_local/done/<topic>/`(spec·plan·review-report·spec-review·plan-review)가 worktree 에만 존재한다. 제거 시 유실되므로 sync-back 이 선행한다.

sync-back 성공 시 main 의 stale 원본 핸드오프본(`docs/_local/{backlog,active}/<topic>`)을 폐기한다 — done 아카이브가 정본이므로 원본 스펙을 남기지 않는다(`--keep-original` 로 보존).

```bash
bash .claude/skills/wf-worktree-context/scripts/teardown.sh <topic>
# 옵션: --force(미커밋 변경 있어도 제거) --keep-worktree(sync-back 만) --keep-original(원본 폐기 안 함)
```

스크립트가 수행: `docs/_local/done/<topic>` 를 메인으로 copy → main 원본 backlog/active 폐기 → `git worktree remove`. 브랜치 `feature/<topic>` 는 남으므로 필요 시 `git branch -D` 로 별도 삭제한다.

## Notes

- 스크립트는 zsh/bash 양쪽에서 실행되게 POSIX 지향으로 작성됐다(연상 배열·mapfile 미사용).
- 매니페스트 조정은 순수 프로비저닝이라 하네스 코드 변경 0 이다.
- 실증 이력: 원 매니페스트(docs/_local 전체 symlink + `.harness` symlink)는 2블로커로 실패 → 위 표로 교정(2026-07-03, marketing-strategist). plan:confirmed 핸드오프 변형은 2026-07-06 실증. muhan 이식 후 tracked-자동판별·exclude-주입파생으로 일반화해 하네스 정본에 편입.
- 배포 특성: 하네스가 git-미추적(`.claude`·`.harness` 등)인 프로젝트에서는 이 스킬 파일도 로컬 전용이라 커밋/PR 대상이 아니다. tracked 로 두는 프로젝트에서는 반대로 포함된다 — 두 경우 모두 provision 이 자동 적응한다.
