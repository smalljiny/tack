"""phase 상태 머신 순수 모듈 단위 테스트.

레퍼런스 dev-context.js의 VALID_TRANSITIONS(14 directed edges)·STATE_ORDER(10 states)·
순방향 점프 판정을 승계한 state_machine.py를 실행 가능한 spec으로 고정한다.
pytest가 test_*.py를 자동 발견하고 파일 디렉토리를 sys.path에 prepend하므로
conftest.py·pyproject.toml 없이 `from state_machine import ...`가 동작한다.
"""

from state_machine import (
    VALID_TRANSITIONS,
    STATE_ORDER,
    is_valid_transition,
    allowed_transitions,
    is_known_state,
    is_forward_jump,
)

# 레퍼런스 dev-context.js L14-25 VALID_TRANSITIONS의 9 순방향 edge
FORWARD_EDGES = [
    ("spec:drafting", "spec:reviewing"),
    ("spec:reviewing", "spec:confirmed"),
    ("spec:confirmed", "plan:ready"),
    ("plan:ready", "plan:reviewing"),
    ("plan:reviewing", "plan:confirmed"),
    ("plan:confirmed", "impl:in-progress"),
    ("impl:in-progress", "review:in-progress"),
    ("review:in-progress", "docs:generated"),
    ("docs:generated", "pr:created"),
]

# 레퍼런스 L14-25 VALID_TRANSITIONS의 5 롤백 edge
ROLLBACK_EDGES = [
    ("spec:reviewing", "spec:drafting"),
    ("plan:reviewing", "plan:ready"),
    ("review:in-progress", "impl:in-progress"),
    ("docs:generated", "review:in-progress"),
    ("pr:created", "docs:generated"),
]


class TestValidTransition:
    """T1.1 — 전 유효 edge·대표 무효 전환 (spec §3.2 표 전량)."""

    def test_all_forward_edges_valid(self):
        assert len(FORWARD_EDGES) == 9
        for frm, to in FORWARD_EDGES:
            assert is_valid_transition(frm, to) is True, f"forward {frm}->{to}"

    def test_all_rollback_edges_valid(self):
        assert len(ROLLBACK_EDGES) == 5
        for frm, to in ROLLBACK_EDGES:
            assert is_valid_transition(frm, to) is True, f"rollback {frm}->{to}"

    def test_total_edge_count_is_14(self):
        total = sum(len(v) for v in VALID_TRANSITIONS.values())
        assert total == 14

    def test_representative_invalid_transitions(self):
        # 순방향 스킵·무효 역방향은 전환 불가
        assert is_valid_transition("spec:drafting", "plan:ready") is False
        assert is_valid_transition("spec:drafting", "review:in-progress") is False
        assert is_valid_transition("spec:confirmed", "spec:drafting") is False

    def test_unknown_from_is_invalid(self):
        assert is_valid_transition("bogus", "spec:reviewing") is False


class TestAllowedTransitions:
    """T1.1 — allowed_transitions가 VALID_TRANSITIONS 목록과 일치."""

    def test_matches_valid_transitions_map(self):
        for frm, tos in VALID_TRANSITIONS.items():
            assert allowed_transitions(frm) == tos

    def test_unknown_from_returns_empty(self):
        assert allowed_transitions("bogus") == []
        assert allowed_transitions("done:archived") == []

    def test_returns_copy_not_internal_reference(self):
        # 반환 리스트 mutate가 상수를 오염시키지 않음 (immutability)
        result = allowed_transitions("spec:reviewing")
        result.append("mutated")
        assert "mutated" not in VALID_TRANSITIONS["spec:reviewing"]


class TestKnownState:
    """T1.1 — is_known_state: 10개 known True, unknown False."""

    def test_all_10_states_known(self):
        assert len(STATE_ORDER) == 10
        for state in STATE_ORDER:
            assert is_known_state(state) is True

    def test_unknown_states_false(self):
        assert is_known_state("done:archived") is False
        assert is_known_state("bogus") is False
        assert is_known_state("") is False


class TestStateSetConsistency:
    """T1.1 — 두 상수 state 집합 일치 (state-name typo 방어, OQ1)."""

    def test_transition_keys_equal_state_order(self):
        assert set(VALID_TRANSITIONS.keys()) == set(STATE_ORDER)

    def test_transition_targets_are_all_known(self):
        for tos in VALID_TRANSITIONS.values():
            for to in tos:
                assert to in STATE_ORDER


class TestForwardJump:
    """T1.2 — is_forward_jump가 is_valid_transition과 직교."""

    def test_invalid_but_forward_is_true(self):
        # 전환 무효여도 순방향
        assert is_forward_jump("spec:drafting", "pr:created") is True

    def test_valid_but_backward_is_false(self):
        # 전환 유효여도 역방향
        assert is_forward_jump("review:in-progress", "impl:in-progress") is False
        assert is_forward_jump("pr:created", "docs:generated") is False

    def test_adjacent_forward_is_true(self):
        assert is_forward_jump("impl:in-progress", "review:in-progress") is True

    def test_unknown_state_is_false(self):
        # JS indexOf(-1) vs Python .index(ValueError) 포팅 트랩: known 가드 필수
        assert is_forward_jump("spec:drafting", "done:archived") is False
        assert is_forward_jump("bogus", "pr:created") is False

    def test_same_state_is_false(self):
        assert is_forward_jump("impl:in-progress", "impl:in-progress") is False


class TestPurity:
    """모듈이 순수 함수·상수만 노출 (I/O·CLI·argparse·부작용 없음)."""

    def test_module_has_no_side_effect_symbols(self):
        import state_machine

        # argparse·sys.argv 파싱·main 진입점이 없어야 함
        assert not hasattr(state_machine, "main")
        for banned in ("argparse", "sys"):
            assert banned not in vars(state_machine), f"{banned} imported"
