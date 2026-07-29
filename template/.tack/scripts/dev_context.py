#!/usr/bin/env python3
"""dev-context.json 전담 CLI 스크립트 (레퍼런스 dev-context.js Python 포트).

사용법: python3 .tack/scripts/dev_context.py <subcommand> [options]

진입점 결정(OQ2): shebang + `python3 dev_context.py <sub> [--flag=value]` 직접 호출.
uv 래핑·.venv 부트스트랩은 스크립트 밖 환경 관심사로 분리한다. 레퍼런스
`node dev-context.js` 직접 호출과 대칭이다.

인자 파싱(OQ3): 레퍼런스 parseArgs를 수동 파싱으로 이식한다(argparse 미채택).
`--key=value`와 값 없는 boolean flag(`--allow-unsafe-force` → True) 동작을 보존한다.

전환 유효성 모델은 state_machine.py(E2-S1 확정 순수 모듈)를 import로 소비한다 —
전환표·STATE_ORDER를 이 파일에 재정의하지 않는다.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

# 전환 모델의 정본은 state_machine이 소유한다 — dev_context.py는 재정의하지 않고 소비만 한다.
# 런타임 검증은 is_valid_transition/allowed_transitions(update-state)와
# STATE_ORDER/is_known_state/is_forward_jump(force-state)로 라우팅한다.
# VALID_TRANSITIONS는 seam 배선(plan T1.3의 6-심볼 요구)으로 import하되 직접 참조는 없다.
import config_schema
from state_machine import (
    VALID_TRANSITIONS,  # noqa: F401 — seam 배선용, 직접 참조 없음(위 주석 참조)
    STATE_ORDER,
    is_valid_transition,
    allowed_transitions,
    is_known_state,
    is_forward_jump,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 레퍼런스 JS: join(__dirname, '../../.tack/local/dev-context.json') (normalize 포함)
DEFAULT_CONTEXT_PATH = os.path.normpath(
    os.path.join(SCRIPT_DIR, "..", "..", ".tack", "local", "dev-context.json")
)
# config 키 계약(.tack/contracts/config-schema.json). local 경로와 달리 SCRIPT_DIR 기준으로
# 유도한다 — 스키마는 배포 산출물의 일부라 DEV_CONTEXT_PATH 격리와 함께 움직이지 않는다.
DEFAULT_CONFIG_SCHEMA_PATH = os.path.normpath(
    os.path.join(SCRIPT_DIR, "..", "contracts", "config-schema.json")
)

# phase/status 설정 금지 필드
PROTECTED_FIELDS = frozenset(["phase", "status"])

# 프로토타입 오염 방지: config 경로 세그먼트·토픽 이름에 예약 키 금지
FORBIDDEN_CONFIG_SEGMENTS = frozenset(["__proto__", "constructor", "prototype"])


def resolve_context_path():
    """DEV_CONTEXT_PATH env override, 미설정 시 스크립트 상대 기본 경로."""
    return os.environ.get("DEV_CONTEXT_PATH") or DEFAULT_CONTEXT_PATH


def resolve_shared_config_path():
    """DEV_CONFIG_PATH env override, 미설정 시 **해석된 local 경로**의 2-hop 상위.

    `.tack/local/dev-context.json` → dirname 2회 → `.tack/` → `.tack/config.json`.

    SCRIPT_DIR 기준으로 유도하지 않는다 — 그러면 DEV_CONTEXT_PATH로 격리된 호출자(테스트·
    worktree)가 실제 저장소의 공유 파일을 읽고 쓰게 된다. 렌더 스모크 테스트는 env를
    설정하지 않고 이 2-hop 유도에 의존하므로 hop 수를 바꾸지 않는다.
    """
    return os.environ.get("DEV_CONFIG_PATH") or os.path.normpath(
        os.path.join(os.path.dirname(os.path.dirname(resolve_context_path())), "config.json")
    )


def resolve_config_schema_path():
    """DEV_CONFIG_SCHEMA_PATH env override, 미설정 시 스크립트 상대 계약 경로.

    DEV_CONTEXT_PATH 선례를 따르는 테스트·격리 seam이다.
    """
    return os.environ.get("DEV_CONFIG_SCHEMA_PATH") or DEFAULT_CONFIG_SCHEMA_PATH


def _empty_shared_config():
    return {"file_format": "1.0", "config": {}}


def load_shared_config(path):
    """공유 config 파일을 엄격하게 읽는다. `(ok, data_or_reason)`.

    degrade 정책을 담지 않는다 — 부재는 `(True, 빈 층)`, 손상은 `(False, 사유)`로
    구분해 돌려준다. 읽기 경로는 read_shared_config가 이 결과에 관대 정책을 씌우고,
    쓰기 경로(Story 4의 read-modify-write)는 `ok=False`에서 멈춰 파싱하지 못한 tracked
    파일을 단일 키로 덮어쓰지 않아야 한다.
    """
    if not os.path.exists(path):
        return True, _empty_shared_config()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError, RecursionError) as e:
        return False, f"읽을 수 없습니다 ({path}): {e}"
    if not isinstance(data, dict) or not isinstance(data.get("config"), dict):
        return False, f"형식이 올바르지 않습니다 ({path})."
    return True, data


def read_shared_config():
    """tracked 공유 config(.tack/config.json)를 읽는다. 부재·손상 시 빈 층으로 degrade.

    읽기는 관대하다 — 공유 파일이 없거나 깨져 있어도 die하지 않고 경고 1줄만 남긴 뒤
    빈 층을 돌려준다. 공유 파일 하나가 워크플로 진입 전체를 막지 않게 하기 위함이다(G5).
    """
    ok, data = load_shared_config(resolve_shared_config_path())
    if not ok:
        sys.stderr.write(f"경고: 공유 config 파일을 {data} 빈 층으로 처리합니다.\n")
        return _empty_shared_config()
    return data


# 미설정(양층 miss) 센티널. JSON null·빈 배열·false는 모두 유효한 local 값이므로
# None을 miss 신호로 쓸 수 없다 — local hit(None)과 miss를 구분하려면 별도 센티널이 필요하다.
_MISSING = object()


def resolve_config_leaf(layers, ns, key):
    """leaf 단위 병합: 우선순위 순 layer들을 훑어 첫 own property를 반환. 없으면 _MISSING.

    `layers`는 우선순위 내림차순 iterable이다 (현재: local → shared). 값이 JSON
    null·빈 배열·false여도 앞선 layer에 own property가 있으면 그 layer가 이긴다.
    배열은 통째 교체이며 층을 concat하지 않는다.

    iterable을 받는 이유는 스펙 §3.6의 E4 seam이다 — 런타임 공유 층(Mongo)은 tracked와
    local 사이에 원소 하나로 삽입되며, 호출자는 generator를 넘겨 뒤쪽 layer의 획득을
    지연시킨다(파일 열기·네트워크 호출을 앞선 layer가 답하면 수행하지 않는다).

    Python dict는 상속 데이터 키가 없어 `in`이 곧 hasOwn 가드다. 예약 키는 호출 전
    parse_config_path가 이미 거부하지만, layer는 모두 파일에서 온 신뢰 밖 데이터이므로
    여기서도 동일하게 차단한다.
    """
    if ns in FORBIDDEN_CONFIG_SEGMENTS or key in FORBIDDEN_CONFIG_SEGMENTS:
        return _MISSING
    for layer in layers:
        if not isinstance(layer, dict):
            continue
        ns_obj = layer.get(ns)
        if isinstance(ns_obj, dict) and key in ns_obj:
            return ns_obj[key]
    return _MISSING


def _iso_now():
    """레퍼런스 new Date().toISOString()과 동일한 밀리초+Z ISO 문자열."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def read_context():
    path = resolve_context_path()
    if not os.path.exists(path):
        return {"current_topic": None, "topics": {}, "config": {}, "updatedAt": _iso_now()}
    with open(path, encoding="utf-8") as f:
        ctx = json.load(f)
    if not isinstance(ctx.get("topics"), dict):
        ctx["topics"] = {}
    if "current_topic" not in ctx:
        ctx["current_topic"] = None
    if not isinstance(ctx.get("config"), dict):
        ctx["config"] = {}
    # 자동 마이그레이션: 기존 currentTask 필드 → currentStory.
    # 두 필드 동시 존재 시 no-op으로 currentTask를 보존(수동 정리 대상으로 남긴다).
    for topic_name in list(ctx["topics"].keys()):
        t = ctx["topics"][topic_name]
        if not isinstance(t, dict):
            continue
        if "currentTask" in t and "currentStory" not in t:
            t["currentStory"] = t.pop("currentTask")
    return ctx


def atomic_write_json(path, data):
    """JSON을 원자적으로 기록한다 — 임시 파일에 쓴 뒤 rename.

    쓰기 목적지가 둘(local dev-context.json · tracked config.json)이므로 관용구를 여기
    한 곳에 둔다. `updatedAt` 스탬핑은 이 함수가 하지 않는다 — tracked 파일은 매 쓰기가
    diff 노이즈가 되므로 타임스탬프를 갖지 않으며, 스탬핑은 write_context의 책임이다.
    """
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def write_context(ctx):
    ctx["updatedAt"] = _iso_now()
    atomic_write_json(resolve_context_path(), ctx)


def parse_args(argv):
    args = {}
    for arg in argv:
        # JS /^--([^=]+)=(.*)$/ (no s flag): '.'는 개행 미포함, '$'는 입력 끝에서만
        # 매치. Python은 \Z + DOTALL 미사용으로 동일 동작 재현(개행 값은 nomatch → 부울 분기).
        m = re.match(r"^--([^=]+)=(.*)\Z", arg)
        if m:
            args[m.group(1)] = m.group(2)
        elif re.match(r"^--[a-zA-Z]", arg):
            # boolean flag (값 없음): --flag → args['flag'] = True
            args[arg[2:]] = True
    return args


def die(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)


def parse_config_path(field):
    """config 점 경로 파싱: 'config.<ns>.<key>'(깊이 2 고정). {ok, ns, key} 또는 {ok:False, reason}."""
    segments = field.split(".")
    if len(segments) != 3 or segments[0] != "config" or not segments[1] or not segments[2]:
        return {
            "ok": False,
            "reason": f"config 경로는 정확히 'config.<namespace>.<key>' 형태여야 합니다 (입력: {field})",
        }
    if segments[1] in FORBIDDEN_CONFIG_SEGMENTS or segments[2] in FORBIDDEN_CONFIG_SEGMENTS:
        return {
            "ok": False,
            "reason": f"config 경로에 예약된 키를 사용할 수 없습니다 (입력: {field})",
        }
    return {"ok": True, "ns": segments[1], "key": segments[2]}


def coerce_config_value(value):
    """config 전용 타입 추론: 'true'/'false'→bool, 정수 리터럴→int, JSON 배열→list, 그 외→str.

    배열은 '[' 시작 + ']' 끝 패턴만. '[A-Z].*' 같은 정규식 스칼라는 ']' 뒤에 문자가 있어 미매치.
    JS \\d는 ASCII이므로 [0-9]를 사용하고, JS /…/s(dotAll)는 re.DOTALL로 재현한다.
    """
    # 값 없는 boolean flag(--value)는 parse_args가 True로 만든다. JS는 이 값을 그대로 저장하므로
    # (String(true)이 정수·배열 정규식에 매치되지 않음), 비-str 입력은 타입 추론 없이 그대로 반환한다.
    if not isinstance(value, str):
        return value
    if value == "true":
        return True
    if value == "false":
        return False
    if re.fullmatch(r"-?[0-9]+", value):
        # 2^53 초과 정수는 JS Number()가 float로 반올림하지만 Python int는 정확값을 유지한다
        # (의도된 비-parity, config 값은 소형 정수라 실사용에서 도달 불가).
        return int(value)
    if re.fullmatch(r"\s*\[.*\]\s*", value, re.DOTALL):
        try:
            parsed = json.loads(value)
        except (ValueError, RecursionError) as e:
            # 깊게 중첩된 대괄호는 json.loads가 RecursionError를 낸다 — clean die로 처리(traceback 회피).
            die(f"config 값 파싱 오류: JSON 배열 파싱 실패 — {e} (입력: {value})")
        if not isinstance(parsed, list) or not all(
            isinstance(el, str) and not re.search(r"[\r\n]", el) for el in parsed
        ):
            die(
                "config 배열 값은 문자열 원소만 허용합니다 — 줄바꿈 포함 및 "
                '비문자열 불가 (예: [".claude/", ".tack/"])'
            )
        return parsed
    return value


def _candidate_hint(name, candidates):
    """오타 후보 문구. 근접 후보가 없으면 전체 후보를 나열한다.

    difflib cutoff에 걸리지 않는 입력('bogus' 등)에서 빈 문구를 내보내면 사용자가 다음
    행동을 알 수 없다 — 후보 집합이 유한하고 작으므로 전체를 보여주는 편이 낫다.
    """
    close = config_schema.suggest(name, candidates)
    if close:
        return "가까운 후보: " + ", ".join(close)
    return "사용 가능: " + ", ".join(candidates)


def load_config_schema():
    """config 키 계약을 fail-closed로 읽는다 — 부재·손상이면 해석된 경로를 담아 die.

    env override 경로에도 같은 정책을 적용한다(프로덕션/테스트 동작 분기를 만들지 않는다).
    이 경로는 config **쓰기**에서만 호출된다 — read는 스키마를 조회하지 않으므로 스키마
    한 파일이 워크플로 진입 전체를 막지 않는다(스펙 §3.4).
    """
    try:
        return config_schema.load_schema(resolve_config_schema_path())
    except config_schema.SchemaError as e:
        die(f"set-field: {e}")


def validate_config_write(schema, ns, key, value):
    """스키마 대조 후 저장할 값을 반환한다. 위반은 die.

    순서: (1) 네임스페이스 조회 → (2) 키 조회 → (3) 타입 추론 → (4) 타입 검사.
    경로 깊이·예약 키 검사(parse_config_path)는 호출 전에 끝나 있어야 한다 — 그 메시지가
    스키마 조회 메시지보다 먼저 나와야 기존 계약이 유지된다.

    `schema`를 인자로 받는다 — 로드는 호출자(I/O 층)가 하고 이 함수는 판정만 한다.
    layer 라우팅도 같은 schema 객체를 소비하므로, 한 번의 로드로 검증과 목적지 결정이
    같은 지점에서 이어진다 (스펙 §3.3·§3.4가 한 시퀀스로 규정한 검사 순서).
    """
    if ns not in config_schema.namespaces(schema):
        die(
            f"set-field: 알 수 없는 config 네임스페이스 '{ns}' — "
            f"{_candidate_hint(ns, config_schema.namespaces(schema))}"
        )
    entry = config_schema.lookup(schema, ns, key)
    if entry is None:
        die(
            f"set-field: 알 수 없는 config 키 '{ns}.{key}' — "
            f"{_candidate_hint(key, config_schema.keys_of(schema, ns))}"
        )

    coerced = coerce_config_value(value)
    declared = entry.get("type")
    if not config_schema.check_type(declared, coerced):
        if not isinstance(value, str):
            # 등호 없는 bare `--value`는 parse_args가 True로 만든다. 사용자가 입력한
            # 문자열이 아니므로 '입력: true' 표기만으로는 원인이 드러나지 않는다.
            shown = "등호 없는 '--value' 플래그"
            hint = " 값을 주려면 '--value=<값>' 형태를 사용합니다."
        else:
            shown = f"입력값: '{value}'"
            # 'false'·'2026' 같은 문자열은 타입 추론이 bool·int로 바꾼다. 빈 문자열
            # 저장은 등호를 붙인 `--value=` 형태여야 한다.
            hint = " 빈 문자열을 저장하려면 '--value=' 형태를 사용합니다." if declared == "string" else ""
        die(
            f"set-field: config.{ns}.{key} 키는 {declared} 타입이지만 입력이 "
            f"{config_schema.type_name(coerced)} 타입으로 해석됐습니다 ({shown}).{hint}"
        )
    return coerced


def cmd_register_topic(args):
    topic = args.get("topic")
    spec = args.get("spec")
    if not topic:
        die("register-topic: --topic 필요")
    if not spec:
        die("register-topic: --spec 필요")

    ctx = read_context()

    # JS `if (ctx.topics[topic])`는 빈 객체 {}도 truthy로 die한다. Python `if existing:`는
    # {}를 falsy로 처리해 divergence하므로 `is not None`으로 존재 여부를 판정한다.
    existing = ctx["topics"].get(topic)
    if existing is not None:
        die(
            f"register-topic: 토픽 '{topic}'이 이미 존재합니다 "
            f"(현재 {existing.get('phase')}:{existing.get('status')})"
        )

    # 기존 레거시 필드 정리
    ctx.pop("current_spec", None)
    ctx.pop("specConfirmed", None)
    ctx.pop("planConfirmed", None)

    ctx["topics"][topic] = {
        "phase": "spec",
        "status": "drafting",
        "spec": spec,
        "specReview": None,
        "plan": None,
        "planReview": None,
        "currentStory": None,
        "createdAt": _iso_now(),
        "updatedAt": _iso_now(),
    }
    ctx["current_topic"] = topic
    write_context(ctx)


def cmd_update_state(args):
    topic = args.get("topic")
    phase = args.get("phase")
    status = args.get("status")
    if not topic:
        die("update-state: --topic 필요")
    if not phase:
        die("update-state: --phase 필요")
    if not status:
        die("update-state: --status 필요")

    ctx = read_context()
    t = ctx["topics"].get(topic)
    if t is None:
        die(f"update-state: 토픽 '{topic}' 미존재")

    frm = f"{t.get('phase')}:{t.get('status')}"
    to = f"{phase}:{status}"

    if frm == to:
        # 동일 상태는 무시 (idempotent) — 파일 미변경
        return

    if not is_valid_transition(frm, to):
        allowed = allowed_transitions(frm)
        allowed_str = ", ".join(allowed) if allowed else "없음"
        die(f"update-state: 유효하지 않은 전환 '{frm}' → '{to}'\n허용: {allowed_str}")

    t["phase"] = phase
    t["status"] = status
    t["updatedAt"] = _iso_now()
    write_context(ctx)


def _set_config_field(field, value):
    """config 점 경로 쓰기: 경로 검증 → 스키마 검증 → 목적지 파일 갱신.

    스키마는 여기서 한 번 로드해 검증에 넘긴다. layer 라우팅(Story 4)도 같은 객체를
    소비하므로 목적지 결정이 검증과 같은 지점에서 이어진다.
    """
    parsed = parse_config_path(field)
    if not parsed["ok"]:
        die(f"set-field: {parsed['reason']}")
    ns = parsed["ns"]
    key = parsed["key"]
    schema = load_config_schema()
    # 검증이 read-modify-write보다 앞선다 — 거부된 쓰기는 파일을 만들지도 건드리지도 않는다.
    coerced = validate_config_write(schema, ns, key, value)
    ctx = read_context()
    if not isinstance(ctx["config"].get(ns), dict):
        ctx["config"][ns] = {}
    ctx["config"][ns][key] = coerced
    write_context(ctx)


def cmd_set_field(args):
    field = args.get("field")
    topic = args.get("topic")
    if not field:
        die("set-field: --field 필요")
    if "value" not in args:  # 레퍼런스 value === undefined (키 부재만)
        die("set-field: --value 필요")
    value = args["value"]

    # 글로벌 필드: current_topic (--topic 없이 사용, read와 대칭)
    if field == "current_topic":
        if topic:
            die("set-field: current_topic은 글로벌 필드이므로 --topic과 함께 사용할 수 없습니다")
        ctx = read_context()
        ctx["current_topic"] = None if value == "null" else value
        write_context(ctx)
        return

    # 글로벌 config 점 경로 (config.<ns>.<key>)
    if field == "config" or field.startswith("config."):
        if topic:
            die("set-field: config.* 는 글로벌 필드이므로 --topic과 함께 사용할 수 없습니다")
        _set_config_field(field, value)
        return

    if not topic:
        die("set-field: --topic 필요 (current_topic 제외)")

    if field in PROTECTED_FIELDS:
        die(f"set-field: '{field}' 필드는 update-state 전용입니다")

    # 프로토타입 오염 방지: topic 필드 예약 키 금지
    if field in ("__proto__", "constructor", "prototype"):
        die(f"set-field: '{field}' 필드는 사용할 수 없습니다")

    ctx = read_context()
    t = ctx["topics"].get(topic)
    if t is None:
        die(f"set-field: 토픽 '{topic}' 미존재")

    # 토픽 필드 값은 타입 추론 없이 문자열 그대로 저장 (타입 추론은 config 전용)
    t[field] = None if value == "null" else value
    t["updatedAt"] = _iso_now()
    write_context(ctx)


def _js_string(val):
    """레퍼런스 String(val) 재현: None→'', bool→'true'/'false', 그 외→str(val).

    Python str(True)='True'이지만 JS String(true)='true'이므로 bool을 명시 변환한다
    (config boolean read의 byte-parity에 필요).
    """
    if val is None:
        return ""
    if val is True:
        return "true"
    if val is False:
        return "false"
    return str(val)


def _emit_scalar(val):
    """레퍼런스 process.stdout.write((val==null? '' : String(val)) + '\\n')와 동일."""
    sys.stdout.write(_js_string(val) + "\n")


def _read_config_field(ctx, field):
    """config 점 경로 읽기: 경로 검증 → 우선순위 층 병합 → 출력."""
    parsed = parse_config_path(field)
    if not parsed["ok"]:
        # 경로 검증이 공유 파일 읽기보다 먼저다 — 깊이·예약 키 위반이 손상된 공유
        # 파일 경고를 앞세우지 않게 한다.
        die(f"read: {parsed['reason']}")
    # generator로 넘겨 뒤쪽 층의 획득을 지연시킨다 — local이 답하는 읽기에서는 공유
    # 파일을 열지 않아, 손상된 공유 파일의 경고가 무관한 읽기마다 스킬층 stdout 캡처
    # 옆으로 반복 출력되지 않는다.
    layers = (layer() for layer in (lambda: ctx.get("config"), lambda: read_shared_config()["config"]))
    val = resolve_config_leaf(layers, parsed["ns"], parsed["key"])
    if val is _MISSING:
        # 미설정은 빈 출력이다 — 스키마 default를 합성하지 않는다 (G6).
        val = None
    if isinstance(val, list):
        # 빈 배열은 join 시맨틱상 그대로 빈 줄이 되므로 미설정과 같은 출력이다.
        # 원소를 _js_string으로 통과시켜 레퍼런스 val.join('\n')과 파리티를 맞춘다 —
        # JS join은 비-문자열을 강제 변환하고 null을 빈 문자열로 만든다. 손으로 편집되는
        # tracked 공유 파일에 비-문자열 원소가 들어와도 read가 exit 1로 죽지 않아야 한다.
        sys.stdout.write("\n".join(_js_string(v) for v in val) + "\n")
    else:
        _emit_scalar(val)


def cmd_read(args):
    field = args.get("field")
    topic = args.get("topic")
    if not field:
        die(
            "read: --field 필요\n"
            "\n"
            "사용 가능한 호출 형태:\n"
            "  read --field=current_topic\n"
            "  read --field=config.<namespace>.<key>\n"
            "  read --topic=<topic> "
            "--field=<phase|status|spec|specReview|plan|planReview|currentStory>"
        )

    ctx = read_context()

    if field == "current_topic":
        if topic:
            die("read: current_topic은 글로벌 필드이므로 --topic과 함께 사용할 수 없습니다")
        _emit_scalar(ctx.get("current_topic"))
        return

    # 글로벌 config 점 경로 (config.<ns>.<key>)
    if field == "config" or field.startswith("config."):
        if topic:
            die("read: config.* 는 글로벌 필드이므로 --topic과 함께 사용할 수 없습니다")
        _read_config_field(ctx, field)
        return

    if not topic:
        die("read: --topic 필요 (current_topic 제외)")

    t = ctx["topics"].get(topic)
    if t is None:
        die(f"read: 토픽 '{topic}' 미존재")

    _emit_scalar(t.get(field))


def cmd_remove_topic(args):
    topic = args.get("topic")
    if not topic:
        die("remove-topic: --topic 필요")

    ctx = read_context()
    if ctx["topics"].get(topic) is None:
        die(f"remove-topic: 토픽 '{topic}' 미존재")

    del ctx["topics"][topic]

    # current_topic 전환 (남은 토픽 중 하나 또는 null)
    if ctx.get("current_topic") == topic:
        remaining = list(ctx["topics"].keys())
        ctx["current_topic"] = remaining[0] if remaining else None

    write_context(ctx)


def cmd_force_state(args):
    topic = args.get("topic")
    phase = args.get("phase")
    status = args.get("status")
    if not topic:
        die("force-state: --topic 필요")
    if not phase:
        die("force-state: --phase 필요")
    if not status:
        die("force-state: --status 필요")

    # 예약어 토픽 이름 거부 (prototype pollution 방지)
    if topic in ("__proto__", "constructor", "prototype"):
        die(f"force-state: '{topic}' 토픽 이름은 사용할 수 없습니다")

    to = f"{phase}:{status}"
    if not is_known_state(to):
        die(f"force-state: 알 수 없는 상태 '{to}'\n허용: {', '.join(STATE_ORDER)}")

    ctx = read_context()
    t = ctx["topics"].get(topic)
    if t is None:
        die(f"force-state: 토픽 '{topic}' 미존재")

    frm = f"{t.get('phase')}:{t.get('status')}"
    if frm == to:
        # idempotent: 동일 상태는 무시 (updatedAt 불변)
        return

    # 순방향(forward) 점프는 아티팩트 검증 없이 후기 상태로 진입해 워크플로우 게이트를 우회한다.
    # 역방향 복구가 force-state의 의도된 용도이므로, 순방향에는 명시적 플래그를 요구한다.
    is_forward = is_forward_jump(frm, to)
    if is_forward and not args.get("allow-unsafe-force"):
        die(
            f"force-state: '{frm}' → '{to}'는 순방향 점프입니다.\n"
            "아티팩트 검증 없이 후기 상태로 이동하면 워크플로우 게이트를 우회합니다.\n"
            "의도한 경우 --allow-unsafe-force 플래그를 추가하세요 (역방향 복구에는 불필요)."
        )

    forward_note = " [--allow-unsafe-force]" if is_forward else ""
    sys.stderr.write(
        f"force-state: VALID_TRANSITIONS를 우회해 {frm} → {to}로 강제 전환했습니다 "
        f"(관리자 용도){forward_note}.\n"
    )

    t["phase"] = phase
    t["status"] = status
    t["updatedAt"] = _iso_now()
    write_context(ctx)


def main(argv):
    subcommand = argv[1] if len(argv) > 1 else None
    args = parse_args(argv[2:])

    if subcommand == "register-topic":
        cmd_register_topic(args)
    elif subcommand == "update-state":
        cmd_update_state(args)
    elif subcommand == "set-field":
        cmd_set_field(args)
    elif subcommand == "read":
        cmd_read(args)
    elif subcommand == "remove-topic":
        cmd_remove_topic(args)
    elif subcommand == "force-state":
        cmd_force_state(args)
    else:
        die(
            f"알 수 없는 서브커맨드: {subcommand}\n"
            "사용 가능: register-topic, update-state, set-field, "
            "remove-topic, read, force-state"
        )


if __name__ == "__main__":
    main(sys.argv)
