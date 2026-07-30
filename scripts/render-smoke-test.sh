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
#   (a)  copier가 seed한 dev-context.json 존재 + 첫 dev-context read(Python 엔진) exit 0
#   (a2) Python 엔진 쓰기 서브커맨드(set-field) exit 0
#   (a3) 렌더 dest에 dev-context.js 엔진 파리티 잔존 (G5)
#   (a4) 스킬층(.claude/skills · .claude/scripts)에 stale inline node dev-context.js 실행 호출 0건
#        (훅층 split-line 콜러 detect-and-cache.js는 의도적 스코프 밖 — E7-S1까지 Node 유지)
#   (a5) 렌더 dest에 config 스키마(.tack/contracts/config-schema.json) 존재 + JSON 파싱 가능
#   (a6) shared 층 end-to-end: 사전 부재 → shared 키 set-field → .tack/config.json 생성
#        → 파일 내용 확인 → read-back 일치
#   (a7) cache 키의 --layer=shared 승격 거부 (거부 문구 + 파일 미변경까지 단언)
#   (b)  렌더 dest에 stale 경로 토큰(.harness · docs/_local/) 0건
#   (c)  git repo 안에서 .tack/local/ 이 gitignore로 무시되고, .tack/config.json 은 무시되지 않음
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

# 상속된 경로 override를 걷어낸다. (a6)은 공유 config 경로의 2-hop 유도가 렌더
# 레이아웃에서 성립하는지를 검증하므로 override가 살아 있으면 그 전제가 무너지고,
# 더 나쁘게는 tracked 파일 쓰기가 override가 가리키는 실제 저장소로 떨어진다.
unset DEV_CONTEXT_PATH DEV_CONFIG_PATH DEV_CONFIG_SCHEMA_PATH

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
if ! python3 "$DEST/.tack/scripts/dev_context.py" read --field=current_topic >/dev/null 2>&1; then
  fail "(a) 첫 dev-context read(Python 엔진)가 nonzero exit로 종료됨"
fi
echo "[PASS] (a) seed 존재 + 첫 read(Python) exit 0"

# --- Python engine write-path check (set-field exit 0) ---
# temp dest이므로 실제 쓰기가 무해하다. update-state는 seeded 상태에서 거부될 수
# 있어 피하고, config 필드 set-field로 Python 엔진의 쓰기 경로가 동작함을 확인한다.
if ! python3 "$DEST/.tack/scripts/dev_context.py" set-field --field=config.dev_impl.auto_commit --value=true >/dev/null 2>&1; then
  fail "(a2) Python 엔진 쓰기 서브커맨드(set-field)가 nonzero exit로 종료됨"
fi
echo "[PASS] (a2) Python 쓰기 서브커맨드 exit 0"

# --- engine parity: dev-context.js 잔존 (G5) ---
# Python 전환 후에도 레퍼런스 Node 엔진을 파리티로 유지한다 (Codex-on-Node 등).
if [ ! -f "$DEST/.tack/scripts/dev-context.js" ]; then
  fail "(a3) dev-context.js 엔진 파리티 파일 부재 (G5 위반)"
fi
echo "[PASS] (a3) dev-context.js 엔진 파리티 잔존"

# --- stale inline node dev-context caller guard (스킬층 한정) ---
# 스코프를 .claude/skills · .claude/scripts 두 디렉토리로 한정한다:
#   - .codex/ 는 out-of-scope(Codex 스킬은 Node 엔진 유지)이므로 배제.
#   - .tack/scripts/ 는 엔진 self-ref(dev-context.js 주석)이므로 배제.
# 이 guard는 단일 라인 `node ... dev-context.js` 실행 호출만 탐지한다. 훅층의
# split-line 콜러(detect-and-cache.js의 `spawnSync('node', [devContextScript])`,
# devContextScript=join(cwd,'.tack/scripts/dev-context.js'))는 의도적으로 스코프
# 밖이다 — 훅층은 E7-S1까지 Node 유지(plan Out-of-scope), G5로 dev-context.js가
# 잔존하므로 그 콜러는 정상 동작한다. PASS 메시지는 "inline" 한정으로 명시해 이
# guard가 모든 node 콜러 부재가 아니라 인라인 콜러 부재만 증명함을 정직하게 표기한다.
# 기존 Check (b) 관용구(2>/dev/null || true + [ -n ])를 미러해 디렉토리 부재에도 안전.
STALE_NODE="$(grep -rnE 'node .*dev-context\.js' "$DEST/.claude/skills" "$DEST/.claude/scripts" 2>/dev/null || true)"
if [ -n "$STALE_NODE" ]; then
  echo "$STALE_NODE"
  fail "(a4) 스킬층에 stale inline node dev-context.js 실행 호출 잔존"
fi
echo "[PASS] (a4) 스킬층 stale inline node dev-context.js 실행 호출 0건"

# --- Check (a5): config 스키마 존재 + 파싱 가능 (T7.1) ---
# 스키마는 set-field의 fail-closed 입력이다 — 배포 산출물에서 빠지거나 깨지면 config
# 쓰기 전체가 막히므로, 렌더 형태 그대로 존재·파싱을 확인한다.
SCHEMA_DEST="$DEST/.tack/contracts/config-schema.json"
if [ ! -f "$SCHEMA_DEST" ]; then
  fail "(a5) config 스키마 파일 부재: .tack/contracts/config-schema.json"
fi
if ! python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$SCHEMA_DEST" >/dev/null 2>&1; then
  fail "(a5) config 스키마가 유효한 JSON이 아님: .tack/contracts/config-schema.json"
fi
echo "[PASS] (a5) config 스키마 존재 + JSON 파싱 가능"

# --- Check (a6): shared 층 end-to-end 쓰기 + read-back (T7.2) ---
# DEV_CONFIG_PATH를 설정하지 않는다 — 공유 config 경로의 2-hop 유도(해석된 local 경로의
# dirname 2회 → .tack/config.json)가 렌더 레이아웃에서 성립하는지가 이 체크의 대상이다.
# env override를 주면 검증 대상인 그 유도를 잃는다.
# git.pushRemote는 shared layer라 기본 라우팅(플래그 없음)이 tracked 파일로 보낸다.

# 쓰기 이전 부재를 먼저 고정한다. 렌더 산출물에 .tack/config.json이 미리 들어오면
# 아래 세 단언이 전부 vacuous해진다 — 파일이 이미 있고 값이 스키마 default(`origin`)와
# 같으면 쓰기가 아무 일도 하지 않아도 통과한다. "생성 확인"은 사전 부재를 전제한다.
if [ -f "$DEST/.tack/config.json" ]; then
  fail "(a6) 렌더 산출물에 .tack/config.json 이 이미 존재함 — shared 쓰기 검증이 무의미해진다"
fi
# stderr를 버리지 않는다 — 스키마가 JSON으로는 파싱되지만 구조가 무효인 경우((a5)가
# 잡지 못하는 유일한 경로) load_config_schema의 fail-closed 메시지가 원인을 담고 있다.
SET_ERR="$(python3 "$DEST/.tack/scripts/dev_context.py" set-field --field=config.git.pushRemote --value=origin 2>&1)" \
  || fail "(a6) shared 키 set-field가 nonzero exit로 종료됨: $SET_ERR"
if [ ! -f "$DEST/.tack/config.json" ]; then
  fail "(a6) shared 쓰기가 .tack/config.json 을 생성하지 않음 (2-hop 경로 유도 실패)"
fi
# 병합된 read보다 공유 파일 자체를 먼저 본다 — local 층이 답해도 read-back은 통과하므로,
# 파일 내용 확인 없이는 shared 경로가 검증되지 않는다.
if ! python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d["config"]["git"]["pushRemote"]=="origin" else 1)' "$DEST/.tack/config.json" >/dev/null 2>&1; then
  fail "(a6) .tack/config.json 에 config.git.pushRemote=origin 이 기록되지 않음"
fi
SHARED_READ="$(python3 "$DEST/.tack/scripts/dev_context.py" read --field=config.git.pushRemote 2>/dev/null)"
if [ "$SHARED_READ" != "origin" ]; then
  fail "(a6) shared 층 read-back 불일치: 기대 'origin', 실제 '$SHARED_READ'"
fi
echo "[PASS] (a6) shared 층 쓰기 + .tack/config.json 생성 + read-back(origin)"

# --- Check (a7): cache 키의 shared 승격 거부 (T7.3) ---
# 이 스크립트에서 성공한 명령이 실패 신호인 유일한 체크다 — `!` 없이 성공을 fail로
# 판정한다. codex.available은 cache layer이므로 감지 캐시가 커밋 대상 파일로 승격되면
# 다른 머신에서 잘못된 값으로 읽힌다.
A7_ERR="$(python3 "$DEST/.tack/scripts/dev_context.py" set-field --field=config.codex.available --layer=shared --value=true 2>&1)" \
  && fail "(a7) cache 키의 --layer=shared 승격이 거부되지 않음"
# nonzero exit만으로는 부족하다 — 키 이름 변경·타입 변경·`--layer` 어휘 변경도 모두
# nonzero를 내므로, 검증 대상 guard가 실패 원인인지 문구로 고정한다
# (testing.md 다층 Guard 테스트 원칙: "테스트가 실패하는 이유가 검증 대상 guard인가?").
case "$A7_ERR" in
  *"승격할 수 없습니다"*) : ;;
  *) fail "(a7) 승격 거부가 아닌 다른 사유로 실패했습니다: $A7_ERR" ;;
esac
# 거부는 exit code만이 아니라 "파일 미변경"까지 포함한다 — dev_context.py의 검증-선행
# 불변식(거부된 쓰기는 파일을 만들지도 건드리지도 않는다)의 관측 가능한 절반이다.
# (a6)이 이미 파일을 만들어 뒀으므로 존재 여부로는 이 절반을 볼 수 없다.
if python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if "codex" in d["config"] else 1)' "$DEST/.tack/config.json" >/dev/null 2>&1; then
  fail "(a7) 거부된 승격이 .tack/config.json 에 codex 네임스페이스를 남겼음"
fi
echo "[PASS] (a7) cache 키 --layer=shared 승격 거부 (파일 미변경 포함)"

# --- Check (b): 렌더 dest에 stale 토큰 0건 (T5.4) ---
# (a6)이 기록한 값은 'origin'이라 아래 grep에 걸리는 토큰을 포함하지 않는다.
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
# core.excludesFile=/dev/null: 두 단언의 유일한 입력을 렌더 dest의 .tack/.gitignore로
# 고정한다. 없으면 config.json을 전역 ignore한 메인테이너 환경에서 아래 단언이 false FAIL
# 한다 (secrets 습관으로 흔하다).
if ! git -C "$DEST" -c core.excludesFile=/dev/null check-ignore .tack/local/dev-context.json >/dev/null 2>&1; then
  fail "(c) .tack/local/dev-context.json 이 gitignore로 무시되지 않음"
fi
# tracked 공유 config는 반대 방향을 단언한다 (T7.4). exit code를 정확히 1로 요구한다 —
# "nonzero" 판정은 git 오류(128)까지 통과시켜 체크가 실패할 수 없게 만든다.
# 이 한 줄은 파일에서 유일하게 exit status가 load-bearing인 bare 호출이다 — `set -e`가
# 꺼져 있어야 다음 줄의 `$?` 캡처에 도달한다.
git -C "$DEST" -c core.excludesFile=/dev/null check-ignore .tack/config.json >/dev/null 2>&1
CHECK_IGNORE_RC=$?
if [ "$CHECK_IGNORE_RC" -ne 1 ]; then
  fail "(c) .tack/config.json 은 ignore 대상이 아니어야 한다 (check-ignore exit=$CHECK_IGNORE_RC — 0=ignore됨, 128=git 오류)"
fi
echo "[PASS] (c) .tack/local/ ignore + .tack/config.json non-ignore 확인"

# --- 전부 통과 ---
echo "[OK] 렌더 스모크 테스트 모든 검증 통과 (a·a2·a3·a4·a5·a6·a7·b·c)."
exit 0
