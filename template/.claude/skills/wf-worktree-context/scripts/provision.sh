#!/usr/bin/env bash
# wf-worktree-context — sibling worktree 프로비저닝 (멱등·프로젝트 무관)
#
# 하네스(.claude·.tack·.codex 등)가 git-미추적인 프로젝트에서 fresh worktree
# 체크아웃엔 이들이 없다. 이 스크립트가 git-미추적 컨텍스트를 주입한다.
# 원 출처: marketing-strategist(2026-07-03/07-06 실증 교정) → muhan → 하네스 정본.
#
# 프로젝트별 자동 적응 (분기·하드코딩 없음):
#   `git worktree add <base>` 는 base 트리의 git-tracked 파일을 worktree 에 실제로
#   체크아웃한다. 따라서 tracked 컨텍스트(예: 커밋된 CLAUDE.md)는 이미 worktree 에
#   존재하고, symlink 주입 함수(link)의 존재 검사가 그것을 자동 skip 한다. 반대로
#   gitignored/absent 항목만 주입된다. 그래서 아래 symlink 후보는 superset 으로 두고,
#   실제 주입 여부는 각 프로젝트의 tracked 상태가 결정한다. exclude 보정도 실제 주입한
#   항목(INJECTED)에서만 파생하므로, tracked 항목을 exclude 로 가리는 사고가 없다.
#
# Usage:
#   provision.sh <topic> [--base <branch>] [--main <path>]
#
#   <topic>   dev-context.json 에 등록된 토픽명(^[A-Za-z0-9_-]+$)
#   --base    worktree base 브랜치 (기본: develop). 없으면 --base 로 지정.
#   --main    메인 리포 경로 (기본: 이 스크립트에서 git 루트 자동 탐지)
#
# 각 주입 단계는 대상이 이미 있으면 skip 한다(멱등). 재실행하면 누락분만 채운다.
set -euo pipefail

TOPIC=""
BASE="develop"
MAIN=""

while [ $# -gt 0 ]; do
  case "$1" in
    --base) BASE="$2"; shift 2 ;;
    --main) MAIN="$2"; shift 2 ;;
    --*) echo "unknown flag: $1" >&2; exit 2 ;;
    *) if [ -z "$TOPIC" ]; then TOPIC="$1"; shift; else echo "unexpected arg: $1" >&2; exit 2; fi ;;
  esac
done

if [ -z "$TOPIC" ]; then
  echo "usage: provision.sh <topic> [--base <branch>] [--main <path>]" >&2
  exit 2
fi
if ! printf '%s' "$TOPIC" | grep -qE '^[A-Za-z0-9_-]+$'; then
  echo "invalid topic name: $TOPIC (allowed: A-Za-z0-9_-)" >&2
  exit 2
fi

# MAIN 리포 루트 확정
if [ -z "$MAIN" ]; then
  MAIN="$(git rev-parse --show-toplevel)"
fi
MAIN="$(cd "$MAIN" && pwd)"

# worktree 는 repo 밖 sibling (repo 내부는 부모 CLAUDE.md·rules 이중 로드)
WT="$(dirname "$MAIN")/$(basename "$MAIN").worktrees/$TOPIC"
BRANCH="feature/$TOPIC"

echo "[wf-worktree-context] MAIN=$MAIN"
echo "[wf-worktree-context] WT=$WT"
echo "[wf-worktree-context] base=$BASE branch=$BRANCH"

# INJECTED: 실제로 symlink 주입한 항목(공백 구분). exclude 보정의 원천.
INJECTED=""

# --- 1. worktree 생성 (없을 때만) ---
if [ -d "$WT" ]; then
  echo "[1] worktree exists — skip create"
else
  if ! git -C "$MAIN" rev-parse --verify --quiet "$BASE" >/dev/null; then
    echo "base 브랜치 '$BASE' 가 없습니다. --base <branch> 로 지정하세요." >&2
    exit 2
  fi
  git -C "$MAIN" worktree add "$WT" -b "$BRANCH" "$BASE"
  echo "[1] worktree added (base=$BASE)"
fi

# --- 2. symlink 주입 (abs→main): 큰 공유 툴링. 읽기 전용/cwd 기준이라 안전 ---
# git-tracked 항목은 worktree add 가 이미 체크아웃 → 아래 존재 검사가 자동 skip.
# main 에 없는 항목도 self-skip. 실제 주입분만 INJECTED 에 모은다.
link() { # link <rel-target>
  local rel="$1"
  [ -e "$MAIN/$rel" ] || return 0                        # main 에 없음 → skip
  if [ -e "$WT/$rel" ] || [ -L "$WT/$rel" ]; then        # 체크아웃 제공(tracked) 또는 기주입(멱등) → skip
    return 0
  fi
  mkdir -p "$(dirname "$WT/$rel")"
  ln -s "$MAIN/$rel" "$WT/$rel"
  INJECTED="$INJECTED $rel"
}
for s in .claude .codex .agents .mcp.json AGENTS.md CLAUDE.md .serena; do link "$s"; done
echo "[2] symlinks injected:${INJECTED:- (none — all tracked/absent)}"

# --- 3. .tack copy (blocker-2: dev-context.js __dirname 기준 → symlink 시 main 격리붕괴) ---
# tracked 면 worktree add 가 실파일로 제공 → 아래 존재 검사가 skip(exclude 불요).
# .tack/local 은 main 런타임 상태(dev-context.json·전 토픽 산출물·세션)라 wholesale
# copy 로 worktree 에 새면 안 된다 — copy 직후 제거하고 step 5 가 요청 토픽만 격리
# re-seed 한다. (구 레이아웃은 .harness 정적/docs/_local 런타임이 별개 트리라 이 leak
# 이 없었다. .tack/local 중첩으로 생긴 격리 회귀를 여기서 닫는다.)
HARNESS_COPIED=""
if [ -e "$WT/.tack" ]; then
  echo "[3] .tack exists — skip"
else
  cp -R "$MAIN/.tack" "$WT/.tack"
  rm -rf "$WT/.tack/local"
  HARNESS_COPIED="1"
  echo "[3] .tack copied (main .tack/local stripped — step 5 re-seeds per-worktree)"
fi

# --- 4. env copy (격리, 값 변경 안전). .secrets 는 never-tracked → 있으면 copy ---
SECRETS_COPIED=""
if [ -e "$WT/.secrets" ]; then
  echo "[4] .secrets exists — skip"
elif [ -e "$MAIN/.secrets" ]; then
  cp -R "$MAIN/.secrets" "$WT/.secrets"
  SECRETS_COPIED="1"
  echo "[4] .secrets copied"
else
  echo "[4] no .secrets — skip"
fi

# --- 5. .tack/local per-worktree 실디렉토리 (blocker-1: codex workspace-write 가
#         worktree 밖 symlink 쓰기 차단) + 토픽 산출물 핸드오프 copy ---
mkdir -p "$WT/.tack/local/backlog" "$WT/.tack/local/active" "$WT/.tack/local/done"
# 토픽이 있는 stage 를 탐지해 그 디렉토리를 통째로 copy (spec:confirmed=backlog, plan+=active)
SRC_STAGE=""
for stage in active backlog done; do
  if [ -d "$MAIN/.tack/local/$stage/$TOPIC" ]; then SRC_STAGE="$stage"; break; fi
done
if [ -n "$SRC_STAGE" ]; then
  if [ ! -d "$WT/.tack/local/$SRC_STAGE/$TOPIC" ]; then
    cp -R "$MAIN/.tack/local/$SRC_STAGE/$TOPIC" "$WT/.tack/local/$SRC_STAGE/$TOPIC"
  fi
  echo "[5] handoff copied: .tack/local/$SRC_STAGE/$TOPIC"
else
  echo "[5] WARN: topic dir not found in main .tack/local/{active,backlog,done}/$TOPIC" >&2
fi
# dev-context.json per-worktree (current_topic 격리). main 에 없으면(/flow-spec 전) 방어적 skip.
if [ ! -f "$WT/.tack/local/dev-context.json" ] && [ -f "$MAIN/.tack/local/dev-context.json" ]; then
  cp "$MAIN/.tack/local/dev-context.json" "$WT/.tack/local/dev-context.json"
  echo "[5] dev-context.json provisioned (per-worktree)"
elif [ ! -f "$MAIN/.tack/local/dev-context.json" ]; then
  echo "[5] WARN: main .tack/local/dev-context.json 없음 — /flow-spec 후 재프로비저닝 필요" >&2
fi

# --- 6. git status 누출 처리: 공용 $MAIN/.git/info/exclude 에 실제 주입분만 등록.
#         공용 exclude 는 브랜치 독립·전 worktree 적용이라 커밋된 .gitignore 상태와
#         무관하게 worktree status 를 clean 하게 유지한다. symlink 는 slash-less 패턴만
#         매칭되므로 slash 없이 등록한다. tracked 항목은 INJECTED 에 없어 자동 제외. ---
EXCLUDE="$MAIN/.git/info/exclude"
if [ -f "$EXCLUDE" ]; then
  EXC="$INJECTED"
  [ -n "$HARNESS_COPIED" ] && EXC="$EXC .tack"
  [ -n "$SECRETS_COPIED" ] && EXC="$EXC .secrets"
  for e in $EXC; do
    grep -qxF "$e" "$EXCLUDE" || printf '%s\n' "$e" >> "$EXCLUDE"
  done
  if [ -n "$EXC" ]; then echo "[6] shared exclude ensured:$EXC"; else echo "[6] no injected items to exclude"; fi
fi

# --- 7. 생성물 복원: node_modules 재생성 (package.json 있을 때만) ---
if [ -f "$WT/package.json" ]; then
  ( cd "$WT" && pnpm install >/dev/null 2>&1 && echo "[7] pnpm install done" ) || echo "[7] WARN pnpm install failed" >&2
else
  echo "[7] no package.json — pnpm install skip"
fi

# --- 8. 알려진 stale lockfile drift 되돌림 (커밋된 lockfile 이 CI 기준. 없으면 no-op) ---
if [ -f "$WT/pnpm-lock.yaml" ] && [ -n "$(git -C "$WT" status --porcelain pnpm-lock.yaml)" ]; then
  git -C "$WT" checkout -- pnpm-lock.yaml
  echo "[8] reverted unrelated pnpm-lock.yaml drift"
fi

# --- 9. 격리 프로브 + git status 검증 ---
echo "=== isolation probe (worktree .tack → worktree dev-context) ==="
node "$WT/.tack/scripts/dev-context.js" read --field=current_topic || true
echo "=== worktree git status (expect clean) ==="
git -C "$WT" status --short || true

echo ""
echo "[wf-worktree-context] provisioned: $WT"
echo "다음: 그 디렉토리에서 연 worktree-rooted Claude 세션에서 /flow-* 를 실행한다."
