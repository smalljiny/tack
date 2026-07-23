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

# phase/status 설정 금지 필드
PROTECTED_FIELDS = frozenset(["phase", "status"])

# 프로토타입 오염 방지: config 경로 세그먼트·토픽 이름에 예약 키 금지
FORBIDDEN_CONFIG_SEGMENTS = frozenset(["__proto__", "constructor", "prototype"])


def resolve_context_path():
    """DEV_CONTEXT_PATH env override, 미설정 시 스크립트 상대 기본 경로."""
    return os.environ.get("DEV_CONTEXT_PATH") or DEFAULT_CONTEXT_PATH


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


def write_context(ctx):
    path = resolve_context_path()
    ctx["updatedAt"] = _iso_now()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    # 원자적 쓰기: 임시 파일에 쓴 뒤 rename
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(ctx, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


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
        parsed = parse_config_path(field)
        if not parsed["ok"]:
            die(f"set-field: {parsed['reason']}")
        ctx = read_context()
        ns = parsed["ns"]
        if not isinstance(ctx["config"].get(ns), dict):
            ctx["config"][ns] = {}
        ctx["config"][ns][parsed["key"]] = coerce_config_value(value)
        write_context(ctx)
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
        parsed = parse_config_path(field)
        if not parsed["ok"]:
            die(f"read: {parsed['reason']}")
        # Python dict는 상속 데이터 키가 없어 `in`이 곧 hasOwn 가드다.
        config = ctx.get("config")
        ns_obj = config.get(parsed["ns"]) if isinstance(config, dict) else None
        val = ns_obj.get(parsed["key"]) if isinstance(ns_obj, dict) else None
        if isinstance(val, list):
            # 빈 배열과 미설정은 모두 빈 출력(빈 줄)을 낸다.
            sys.stdout.write(("\n".join(val) + "\n") if len(val) > 0 else "\n")
        else:
            _emit_scalar(val)
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
