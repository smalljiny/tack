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

from state_machine import (  # noqa: F401 — Story 2·6·8에서 소비, Story 1은 배선만
    VALID_TRANSITIONS,
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
    # 자동 마이그레이션(currentTask → currentStory)은 Story 4(T4.2)에서 이식한다.
    # 여기서는 배선만 두고 지연한다 (import noqa 마커와 동일 규약).
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


def main(argv):
    subcommand = argv[1] if len(argv) > 1 else None
    args = parse_args(argv[2:])

    if subcommand == "register-topic":
        cmd_register_topic(args)
    else:
        die(
            f"알 수 없는 서브커맨드: {subcommand}\n"
            "사용 가능: register-topic, update-state, set-field, "
            "remove-topic, read, force-state"
        )


if __name__ == "__main__":
    main(sys.argv)
