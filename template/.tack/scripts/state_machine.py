"""phase 상태 머신 순수 모듈.

레퍼런스 dev-context.js가 검증한 phase:status 상태 모델의 정본 순수 구현.
VALID_TRANSITIONS(14 directed edges)·STATE_ORDER(10 states)·순방향 점프 판정을
I/O·CLI·argparse·부작용 없이 module-level 상수·순수 함수로만 노출한다.
E2-S2 엔진(CLI·dev-context.json I/O·config·force-state 플래그 배선)이 이 모듈을
import로 소비한다 — 깨끗한 seam.
"""

# 상태 전환 유효성 테이블 (phase:status → 허용 다음 상태 목록).
# 레퍼런스 dev-context.js L14-25에서 변경 없이 승계한 14 directed edge
# (9 순방향 + 5 롤백).
VALID_TRANSITIONS = {
    "spec:drafting": ["spec:reviewing"],
    "spec:reviewing": ["spec:confirmed", "spec:drafting"],
    "spec:confirmed": ["plan:ready"],
    "plan:ready": ["plan:reviewing"],
    "plan:reviewing": ["plan:confirmed", "plan:ready"],
    "plan:confirmed": ["impl:in-progress"],
    "impl:in-progress": ["review:in-progress"],
    "review:in-progress": ["impl:in-progress", "docs:generated"],
    "docs:generated": ["pr:created", "review:in-progress"],
    "pr:created": ["docs:generated"],
}

# 워크플로우 선형 순서 (순방향 점프 판정 기준).
# 레퍼런스 dev-context.js L336-340에서 변경 없이 승계한 10 states.
# 전환 그래프는 back-edge/cycle을 포함해 선형 순서를 VALID_TRANSITIONS에서
# 파생 불가하므로 독립 상수로 유지한다 (OQ1).
STATE_ORDER = [
    "spec:drafting", "spec:reviewing", "spec:confirmed",
    "plan:ready", "plan:reviewing", "plan:confirmed",
    "impl:in-progress", "review:in-progress", "docs:generated", "pr:created",
]


def is_valid_transition(frm, to):
    """frm에서 to로의 전환이 VALID_TRANSITIONS에 정의된 유효 edge인지 반환한다."""
    return to in VALID_TRANSITIONS.get(frm, [])


def allowed_transitions(frm):
    """frm에서 허용된 다음 상태 목록의 복사본을 반환한다 (unknown frm은 빈 목록).

    복사본을 반환해 호출자의 mutate가 VALID_TRANSITIONS 상수를 오염시키지 않게 한다.
    """
    return list(VALID_TRANSITIONS.get(frm, []))


def is_known_state(state):
    """state가 STATE_ORDER에 정의된 10개 known 상태 중 하나인지 반환한다."""
    return state in STATE_ORDER


def is_forward_jump(frm, to):
    """frm→to가 STATE_ORDER 상 순방향(후기 상태로 진입)인지 반환한다.

    전환 유효성과 독립인 판정이다 — 무효 전환도 순방향일 수 있고, 유효 전환도
    역방향(롤백)일 수 있다. 레퍼런스 dev-context.js L341-343 판정을 승계하되,
    차단·플래그·경고는 배선하지 않는다.

    JS indexOf()는 미발견 시 -1을 반환하지만 Python list.index()는 ValueError를
    raise하므로, .index() 호출 앞에 known 가드를 둔다.
    """
    if not (is_known_state(frm) and is_known_state(to)):
        return False
    return STATE_ORDER.index(to) > STATE_ORDER.index(frm)
