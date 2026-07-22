#!/usr/bin/env bash
# wf-worktree-context — worktree teardown (sync-back 우선)
#
# docs/_local 은 per-worktree 실디렉토리라 /flow-done 이 아카이브한
# docs/_local/done/<topic>/ 가 worktree 에만 존재한다. worktree 제거 시 유실되므로
# 제거 전 메인으로 sync-back 한다.
#
# sync-back 이 성공하면 main 의 원본 핸드오프본(docs/_local/{backlog,active}/<topic>)을
# 폐기한다 — done 아카이브가 정본이므로 stale 원본 스펙을 남기지 않는다(--keep-original 로 보존).
#
# Usage:
#   teardown.sh <topic> [--main <path>] [--force] [--keep-worktree] [--keep-original]
#
#   --force          worktree 에 미커밋 변경이 있어도 제거 (git worktree remove --force)
#   --keep-worktree  sync-back 만 하고 worktree 는 남긴다
#   --keep-original  sync-back 후에도 main 의 원본 backlog/active 핸드오프본을 폐기하지 않는다
set -euo pipefail

TOPIC=""
MAIN=""
FORCE=""
KEEP=""
KEEP_ORIGINAL=""

while [ $# -gt 0 ]; do
  case "$1" in
    --main) MAIN="$2"; shift 2 ;;
    --force) FORCE="1"; shift ;;
    --keep-worktree) KEEP="1"; shift ;;
    --keep-original) KEEP_ORIGINAL="1"; shift ;;
    --*) echo "unknown flag: $1" >&2; exit 2 ;;
    *) if [ -z "$TOPIC" ]; then TOPIC="$1"; shift; else echo "unexpected arg: $1" >&2; exit 2; fi ;;
  esac
done

if [ -z "$TOPIC" ]; then
  echo "usage: teardown.sh <topic> [--main <path>] [--force] [--keep-worktree]" >&2
  exit 2
fi

if [ -z "$MAIN" ]; then MAIN="$(git rev-parse --show-toplevel)"; fi
MAIN="$(cd "$MAIN" && pwd)"
WT="$(dirname "$MAIN")/$(basename "$MAIN").worktrees/$TOPIC"

if [ ! -d "$WT" ]; then
  echo "worktree not found: $WT" >&2
  exit 1
fi

# --- 1. sync-back: worktree 의 done 아카이브를 메인으로 복사 ---
SRC="$WT/docs/_local/done/$TOPIC"
SYNCED=""
if [ -d "$SRC" ]; then
  mkdir -p "$MAIN/docs/_local/done"
  cp -R "$SRC" "$MAIN/docs/_local/done/$TOPIC"
  SYNCED="1"
  echo "[1] synced back: docs/_local/done/$TOPIC → main"
else
  echo "[1] no done archive at $SRC — skip sync-back (토픽이 아직 /flow-done 전이면 정상)"
fi

# --- 1b. 원본 폐기: sync-back 이 정본 done 아카이브를 main 에 심었으니 stale 원본
#          핸드오프본(backlog/active)을 폐기한다. done 을 정본으로 남긴다. ---
if [ -n "$SYNCED" ] && [ -z "$KEEP_ORIGINAL" ]; then
  for stage in backlog active; do
    if [ -d "$MAIN/docs/_local/$stage/$TOPIC" ]; then
      rm -rf "$MAIN/docs/_local/$stage/$TOPIC"
      echo "[1b] purged stale original: docs/_local/$stage/$TOPIC"
    fi
  done
elif [ -n "$KEEP_ORIGINAL" ]; then
  echo "[1b] --keep-original: main 원본 핸드오프본 보존"
fi

if [ -n "$KEEP" ]; then
  echo "[keep] worktree 유지: $WT"
  exit 0
fi

# --- 2. worktree 제거 ---
if [ -n "$FORCE" ]; then
  git -C "$MAIN" worktree remove --force "$WT"
else
  git -C "$MAIN" worktree remove "$WT"
fi
echo "[2] worktree removed: $WT"
echo "브랜치 feature/$TOPIC 는 남는다 — 필요 시 git branch -D 로 별도 삭제."
