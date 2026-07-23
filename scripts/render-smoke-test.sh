#!/usr/bin/env bash
#
# render-smoke-test.sh — copier 렌더 스모크 테스트 (E1-S6 · Open Q2)
#
# 배치 위치 근거 (Open Q2): 이 스크립트는 repo 루트 `scripts/`에 둔다 — `template/`
# 안이 아니다. 이유:
#   1. template/ 안에 두면 모든 consuming 프로젝트로 배포되고, 그 자체가 stale-path
#      grep(Check b)의 스캔 대상이 되어 자기 자신을 오탐한다.
#   2. 레퍼런스 부트스트랩 하네스의 `.harness/scripts/`와도 분리한다.
#   3. repo 루트 `scripts/`는 tack 자체 tooling이며 이미 graphify target이다.
#
# 검증 항목 (uvx 존재 시):
#   (a) copier가 seed한 dev-context.json 존재 + 첫 dev-context 명령 exit 0
#   (b) 렌더 dest에 stale 경로 토큰(.harness · docs/_local/) 0건
#   (c) git repo 안에서 .tack/local/ 이 gitignore로 무시됨
#
# uvx 부재 시: clean skip + exit 0 (가용성 게이트).
# 종료 코드: 전부 통과 0 / 하나라도 실패 nonzero / uvx 부재 clean skip 0.

set -u

# repo 루트 = 이 스크립트(scripts/)의 부모 디렉토리
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$(dirname "$SCRIPT_DIR")"

# uvx 가용성 게이트 (adapter 패턴: 외부 도구 부재 시 clean skip)
if ! command -v uvx >/dev/null 2>&1; then
  echo "[skip] uvx 없음 — copier 렌더 스모크 테스트를 건너뜁니다 (exit 0)."
  exit 0
fi

DEST="$(mktemp -d)"
# mktemp 실패 시 DEST가 빈 문자열이 되면 copier가 dest=""(=cwd)로 렌더해
# repo 루트를 materialize한다 (E1-S3 Non-goal 위반). trap 설정 전 방어한다.
if [ -z "${DEST:-}" ] || [ ! -d "$DEST" ]; then
  echo "[FAIL] 임시 dest 생성 실패 (mktemp -d)"
  exit 1
fi
cleanup() { rm -rf "$DEST"; }
trap cleanup EXIT

fail() { echo "[FAIL] $1"; exit 1; }

# --- 렌더 (T5.2) ---
# --trust 필수: 없으면 copier가 _tasks(.tack/local/ mkdir + dev-context.json seed)를
# 건너뛰어 (a)·(c)가 미스캐폴드 dest에서 무의미해진다.
# --defaults: 비대화형 실행 (스크립트 컨텍스트에 tty 없음).
# 보안 가정: --trust는 template의 _tasks(임의 셸 명령)를 실행한다. SRC는 이 스크립트
# 자신의 repo(신뢰됨)로 고정돼 안전하다. fork/PR 체크아웃을 SRC로 렌더하는 CI에는
# 배선하지 않는다 — 그 경우 신뢰되지 않은 _tasks가 실행된다.
echo "[render] uvx copier copy --trust --defaults $SRC $DEST"
if ! uvx copier copy --trust --defaults "$SRC" "$DEST" >/dev/null 2>&1; then
  fail "copier 렌더가 nonzero exit로 종료됨"
fi

# --- Check (a): seed 파일 존재 + 첫 read exit 0 (T5.3) ---
# test -f는 _tasks+--trust가 실행됐음을 증명한다 — seed 없이도 exit 0을 반환하는
# default-object read의 vacuous 통과를 방지한다.
if [ ! -f "$DEST/.tack/local/dev-context.json" ]; then
  fail "(a) seed 파일 부재: .tack/local/dev-context.json (--trust _tasks 미실행)"
fi
if ! node "$DEST/.tack/scripts/dev-context.js" read --field=current_topic >/dev/null 2>&1; then
  fail "(a) 첫 dev-context read가 nonzero exit로 종료됨"
fi
echo "[PASS] (a) seed 존재 + 첫 read exit 0"

# --- Check (b): 렌더 dest에 stale 토큰 0건 (T5.4) ---
# git init(c) 이전에 실행해 .git 메타데이터를 스캔에서 배제한다.
# `docs/_local`은 후행 슬래시를 요구하지 않는다 — 슬래시 없는 bare 산문 참조
# (예: "the docs/_local dir")까지 잡아 가드를 마이그레이션 검증 스윕과 정렬한다.
STALE="$(grep -rnE '\.harness|docs/_local' "$DEST" 2>/dev/null || true)"
if [ -n "$STALE" ]; then
  echo "$STALE"
  fail "(b) 렌더 dest에 stale 경로 토큰 잔존"
fi
echo "[PASS] (b) stale-token grep 0건"

# --- Check (c): git repo 안에서 .tack/local/ ignore (T5.5) ---
# git check-ignore는 repo 밖에서 에러다. dest에서 git init 후 확인한다.
if ! git -C "$DEST" init -q >/dev/null 2>&1; then
  fail "(c) dest git init 실패"
fi
if ! git -C "$DEST" check-ignore .tack/local/dev-context.json >/dev/null 2>&1; then
  fail "(c) .tack/local/dev-context.json 이 gitignore로 무시되지 않음"
fi
echo "[PASS] (c) .tack/local/ gitignore 무시 확인"

# --- 전부 통과 (T5.6) ---
echo "[OK] 렌더 스모크 테스트 3검증 모두 통과."
exit 0
