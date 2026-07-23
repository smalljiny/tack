---
version: 1
name: flow-worktree
description: Manage a topic's isolated worktree lifecycle — provision + launch a worktree-rooted Claude session (start), or sync-back documents and remove the worktree (teardown). Delegates provisioning/teardown to wf-worktree-context; owns cmux launch, completion gate, and main dev-context reconciliation.
origin: harness
user-invocable: true
---

# /flow-worktree

지정한 토픽의 격리 worktree 생애주기를 관리한다 — **start**(프로비저닝 + worktree 세션 기동)와 **teardown**(문서 sync-back + worktree 제거). 프로비저닝·제거 스크립트는 `wf-worktree-context` 에 위임하고, 이 스킬은 cmux 세션 기동·완료 게이트·브랜치 안전·main dev-context 정합화를 소유한다.

## Usage

```
/flow-worktree <topic>                        (start) 프로비저닝 + 오른쪽 새 pane 에 세션 기동
/flow-worktree <topic> --surface <ref>        start — 기존 surface(예: surface:71)에 기동
/flow-worktree <topic> --base <branch>        start — worktree base 브랜치(기본 develop)

/flow-worktree teardown <topic>               문서 sync-back + worktree 제거 + main dev-context 정합화
/flow-worktree teardown <topic> --delete-branch   + 머지된 feature/<topic> 브랜치 삭제
/flow-worktree teardown <topic> --surface <ref>   + worktree 세션 pane 닫기
/flow-worktree teardown <topic> --force           done 아카이브 없거나 미커밋 변경 있어도 제거
```

첫 인자가 `teardown` 이면 Teardown 을, 아니면 Start 를 실행한다. `<topic>` 을 생략하면 `current_topic` 을 쓴다.

## Start (기본)

### S1. 토픽 해석

`<topic>` 인자가 있으면 그것을, 없으면 `current_topic` 을 읽는다:

```bash
node .tack/scripts/dev-context.js read --field=current_topic
```

토픽 이름이 `^[a-zA-Z0-9_-]+$` 에 맞지 않으면 중단한다:
```
유효하지 않은 토픽 이름입니다. 영문자, 숫자, 하이픈, 언더스코어만 허용됩니다.
```

### S2. Gate — 확정 단계 확인

토픽의 `phase:status` 를 읽는다:

```bash
node .tack/scripts/dev-context.js read --topic=<topic> --field=phase
node .tack/scripts/dev-context.js read --topic=<topic> --field=status
```

`spec:confirmed` 이상(spec:confirmed·plan:* ·impl:* ·review:* 등)이면 진행한다. `spec:drafting`·`spec:reviewing` 이면 중단한다:
```
worktree 작업은 스펙 확정 이후에 시작합니다.
현재 상태: <phase>:<status>
먼저 /flow-spec 으로 스펙을 확정하세요.
```

### S3. 프로비저닝 — wf-worktree-context 위임

Load `.claude/skills/wf-worktree-context/SKILL.md` and follow its Procedure — Provision (Step 1 전제 확인 → Step 2 `provision.sh <topic>` → Step 3 검증). `--base` 인자가 주어졌으면 `provision.sh <topic> --base <branch>` 로 전달한다.

provision 출력 마지막 줄에서 worktree 경로를 잡는다:
```bash
bash .claude/skills/wf-worktree-context/scripts/provision.sh <topic> 2>&1 | tee /tmp/flow-worktree-provision.log
WT=$(grep -oE 'provisioned: .*$' /tmp/flow-worktree-provision.log | sed 's/^provisioned: //')
```

검증 두 줄을 확인한다 — isolation probe 가 `<topic>` 로 나오고 git status 가 clean 이면 통과. 둘 중 하나라도 어긋나면 provision 출력을 그대로 보여주고 중단한다(cmux 기동으로 넘어가지 않는다).

### S4. 대상 surface 해석

cmux 환경 여부를 확인한다:

```bash
printf 'workspace=%s\nsurface=%s\n' "${CMUX_WORKSPACE_ID:-}" "${CMUX_SURFACE_ID:-}"
cmux ping
```

`cmux ping` 이 실패하거나 `CMUX_WORKSPACE_ID` 가 비어 있으면 **수동 폴백**(아래)을 출력하고 중단한다.

대상 surface 를 정한다:

- `--surface <ref>` 가 주어졌으면 그 ref 를 쓴다. 단 그 surface 가 caller surface(`CMUX_SURFACE_ID`)와 같으면 중단한다(현재 에이전트 세션에 `claude` 를 보내면 세션이 중첩된다):
  ```
  대상 surface 가 현재 세션과 같습니다. 다른 surface 를 지정하거나 --surface 를 생략하세요.
  ```
- `--surface` 가 없으면 caller workspace 오른쪽에 새 terminal pane 을 additive 로 만들고(focus 이동 없음) 그 surface ref 를 잡는다:
  ```bash
  cmux --id-format both new-pane --workspace "$CMUX_WORKSPACE_ID" --type terminal --direction right --focus false --json
  ```
  출력 JSON 에서 생성된 surface 의 ref(`surface_ref`, 형태 `surface:<N>`)를 `TARGET` 으로 잡는다. 출력에 surface ref 가 없으면 직후 `cmux list-pane-surfaces --workspace "$CMUX_WORKSPACE_ID" --json` 으로 새 pane 의 surface ref 를 확인한다.

### S5. 세션 기동

대상 surface 에 worktree 진입 + Claude 기동 명령을 보낸다(focus 이동 없음):

```bash
cmux send --surface <TARGET> "cd $WT && claude
"
```

### S6. 보고

```
worktree 준비 완료: <WT>
  브랜치: feature/<topic> (base <branch>)
  세션 기동: <TARGET>

이 토픽의 /flow-impl·/flow-review 등은 그 worktree 세션에서만 실행하세요.
main hub 에서 실행하면 dev-context 격리가 깨집니다.

완료 후: /flow-worktree teardown <topic>
```

**수동 폴백**(cmux 불가 시 — provision 은 이미 성공):
```
worktree 준비 완료: <WT>
cmux 를 쓸 수 없어 세션은 수동으로 여세요. 대상 터미널에서:
  cd <WT> && claude
```

## Teardown 서브커맨드

worktree 작업이 끝났을 때(`/flow-pr`·`/flow-done` 후) 문서를 main 으로 이관하고 worktree 를 제거한다. **문서 이관은 두 갈래**다:

- `docs/specs/*.md`·코드(git-tracked) → **PR 머지**로 이관(파일 복사 아님, 브랜치에 커밋됨).
- `.tack/local/done/<topic>/`(git-ignored, worktree 에만 존재) → **sync-back**(teardown.sh). 이후 main 의 stale 원본 backlog/active 핸드오프본은 폐기된다.

### T1. 실행 위치 가드 — main hub 에서만

worktree 안에서 실행하면 자기가 앉은 디렉토리를 제거하려다 실패한다. 현재 git 루트가 worktree 면 중단한다:

```bash
TOP=$(git rev-parse --show-toplevel)
case "$TOP" in
  *.worktrees/*) echo "worktree 안에서 실행 중입니다. main hub 로 이동 후 teardown 하세요: cd \$(git rev-parse --git-common-dir)/.. "; exit 1 ;;
esac
MAIN="$TOP"
WT="$(dirname "$MAIN")/$(basename "$MAIN").worktrees/<topic>"
```

worktree 디렉토리(`$WT`)가 없으면 중단한다:
```
worktree 가 없습니다: <WT> (이미 제거됐거나 토픽 이름이 틀림)
```

### T2. 완료 게이트 — done 아카이브 확인

`<WT>/.tack/local/done/<topic>/` 존재를 확인한다. 있으면 `/flow-done` 이 실행돼 아카이브가 만들어진 것 → 진행한다.

없으면 worktree 의 `.tack/local/active/<topic>/`(미아카이브 산출물)가 제거로 유실된다. `--force` 없이 실행됐으면 중단한다:
```
아직 /flow-done 전입니다 (done 아카이브 없음).
worktree 의 active 산출물이 제거로 유실됩니다.
worktree 세션에서 /flow-pr → /flow-done 을 먼저 완료하거나,
버리려면 --force 를 붙이세요.
```

### T3. 브랜치 머지 확인

`feature/<topic>` 가 base(기본 develop)에 머지됐는지 확인한다. remote 반영을 위해 먼저 fetch 한다:

```bash
git -C "$MAIN" fetch --quiet origin develop 2>/dev/null || true
if git -C "$MAIN" merge-base --is-ancestor "feature/<topic>" "origin/develop" 2>/dev/null \
   || git -C "$MAIN" merge-base --is-ancestor "feature/<topic>" "develop" 2>/dev/null; then
  MERGED=1
else
  MERGED=""
fi
```

미머지(`MERGED` 비어 있음)면 경고한다 — worktree 제거는 진행(브랜치가 커밋을 보존)하되 브랜치는 삭제하지 않는다:
```
경고: feature/<topic> 가 develop 에 아직 머지되지 않았습니다.
worktree 는 제거하지만 브랜치는 보존합니다(docs/specs·코드가 브랜치에만 있음).
PR 머지 후 git branch -d feature/<topic> 로 별도 삭제하세요.
```

### T4. sync-back + 제거 — wf-worktree-context 위임

Load `.claude/skills/wf-worktree-context/SKILL.md` and follow its Procedure — Teardown. 미커밋 변경이 있거나 `--force` 면 `--force` 를 전달한다:

```bash
bash .claude/skills/wf-worktree-context/scripts/teardown.sh <topic>   # 또는 + --force
```

teardown.sh 가 `.tack/local/done/<topic>/` → main sync-back → main 원본 backlog/active 폐기 → `git worktree remove` 한다. 원본을 보존하려면 `--keep-original` 을 전달한다.

### T5. 브랜치 삭제 (선택)

`--delete-branch` 이고 T3 에서 머지 확인됐으면 안전 삭제(`-d`, 미머지면 자동 거부):

```bash
git -C "$MAIN" branch -d "feature/<topic>"
```

`--delete-branch` 인데 미머지면 삭제하지 않고 안내한다(강제 삭제는 하지 않는다).

### T6. main dev-context 정합화

worktree 의 `/flow-done` 은 worktree dev-context 에서만 토픽을 제거한다. main hub 의 dev-context 에는 프로비저닝 시점 상태(예: plan:confirmed)로 stale 하게 남는다. 토픽이 main 에 아직 있으면 제거한다:

```bash
node .tack/scripts/dev-context.js read --topic=<topic> --field=phase 2>/dev/null \
  && node .tack/scripts/dev-context.js remove-topic --topic=<topic>
```

### T7. cmux pane 정리 (선택)

`--surface <ref>` 가 주어졌으면 그 worktree 세션 surface 를 닫는다:

```bash
cmux close-surface --workspace "${CMUX_WORKSPACE_ID}" --surface <ref>
```

`--surface` 가 없으면 닫지 않고 안내만 한다(어느 pane 인지 확실치 않으면 닫지 않는다).

### T8. 보고

```
teardown 완료: <topic>
  문서 sync-back: .tack/local/done/<topic>/ → main
  원본 폐기: .tack/local/{backlog,active}/<topic> <폐기됨 / 보존됨(--keep-original)>
  docs/specs·코드: PR 머지 경로로 이관 (브랜치 머지 상태: <머지됨/미머지>)
  worktree 제거: <WT>
  브랜치 feature/<topic>: <삭제됨 / 보존됨>
  main dev-context: 토픽 제거 <됨/해당 없음>
```

## Operating Rule

worktree 프로비저닝 후 그 토픽의 `/flow-*`(plan 이후 — `/flow-impl`·`/flow-review`·`/flow-verify`·`/flow-docs`·`/flow-pr`·`/flow-done`)는 **worktree-rooted 세션에서만** 실행한다. main hub 세션에서 그 토픽의 flow 를 돌리면 main dev-context 를 건드려 격리가 깨진다. main hub 는 `/flow-spec` 과 `/flow-worktree`(start·teardown)만 담당한다. teardown 은 worktree 를 제거하므로 반드시 main hub 에서 실행한다.

## Notes

- 프로비저닝·sync-back·제거 로직은 `wf-worktree-context` 소유다. 이 스킬은 중복 정의하지 않고 위임하며, 완료 게이트·브랜치 안전·main dev-context 정합화·cmux 만 소유한다.
- cmux 는 별도 설치 대상(에이전트용 터미널 스킬)이다. 미설치 시 start 는 수동 폴백을 안내하고, teardown 의 cmux pane 정리(T7)는 건너뛴다.
- cmux 제어(pane 생성·send·close)는 focus 를 바꾸지 않는다 — `new-pane --focus false`, `send`·`close-surface` 는 focus 이동 없음. 사용자는 별도 workspace 를 보고 있을 수 있으므로 focus 를 뺏지 않는다.
- teardown 은 미머지 브랜치를 강제 삭제하지 않는다 — `-d`(안전 삭제)만 쓰고, docs/specs·코드가 브랜치에만 있는 상태에서 유실을 막는다.
