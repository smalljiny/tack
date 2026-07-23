"""update-state 서브커맨드 (레퍼런스 dev-context.test.js L133-207)."""

from pathlib import Path

import pytest

from _dc_helpers import read_ctx, run, run_raw


class TestUpdateState:
    @pytest.fixture
    def t1(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=t1", "--spec=some/spec.md")
        return ctx_path

    def test_valid_transition_drafting_to_reviewing(self, t1):
        run(t1, "update-state", "--topic=t1", "--phase=spec", "--status=reviewing")
        ctx = read_ctx(t1)
        assert ctx["topics"]["t1"]["phase"] == "spec"
        assert ctx["topics"]["t1"]["status"] == "reviewing"

    def test_full_lifecycle_chain(self, t1):
        run(t1, "update-state", "--topic=t1", "--phase=spec", "--status=reviewing")
        run(t1, "update-state", "--topic=t1", "--phase=spec", "--status=confirmed")
        run(t1, "update-state", "--topic=t1", "--phase=plan", "--status=ready")
        run(t1, "update-state", "--topic=t1", "--phase=plan", "--status=reviewing")
        run(t1, "update-state", "--topic=t1", "--phase=plan", "--status=confirmed")
        run(t1, "update-state", "--topic=t1", "--phase=impl", "--status=in-progress")
        run(t1, "update-state", "--topic=t1", "--phase=review", "--status=in-progress")
        ctx = read_ctx(t1)
        assert ctx["topics"]["t1"]["phase"] == "review"
        assert ctx["topics"]["t1"]["status"] == "in-progress"

    def test_invalid_transition_drafting_to_plan_ready(self, t1):
        err = run_raw(t1, "update-state", "--topic=t1", "--phase=plan", "--status=ready")
        assert err.returncode != 0
        assert "유효하지 않은 전환" in err.stderr

    def test_invalid_transition_drafting_to_review(self, t1):
        err = run_raw(t1, "update-state", "--topic=t1", "--phase=review", "--status=in-progress")
        assert err.returncode != 0

    def test_invalid_backward_confirmed_to_drafting(self, t1):
        run(t1, "update-state", "--topic=t1", "--phase=spec", "--status=reviewing")
        run(t1, "update-state", "--topic=t1", "--phase=spec", "--status=confirmed")
        err = run_raw(t1, "update-state", "--topic=t1", "--phase=spec", "--status=drafting")
        assert err.returncode != 0

    def test_plan_reviewing_to_ready_rollback(self, t1):
        run(t1, "update-state", "--topic=t1", "--phase=spec", "--status=reviewing")
        run(t1, "update-state", "--topic=t1", "--phase=spec", "--status=confirmed")
        run(t1, "update-state", "--topic=t1", "--phase=plan", "--status=ready")
        run(t1, "update-state", "--topic=t1", "--phase=plan", "--status=reviewing")
        run(t1, "update-state", "--topic=t1", "--phase=plan", "--status=ready")
        ctx = read_ctx(t1)
        assert ctx["topics"]["t1"]["phase"] == "plan"
        assert ctx["topics"]["t1"]["status"] == "ready"

    def test_review_to_impl_rollback(self, t1):
        run(t1, "update-state", "--topic=t1", "--phase=spec", "--status=reviewing")
        run(t1, "update-state", "--topic=t1", "--phase=spec", "--status=confirmed")
        run(t1, "update-state", "--topic=t1", "--phase=plan", "--status=ready")
        run(t1, "update-state", "--topic=t1", "--phase=plan", "--status=reviewing")
        run(t1, "update-state", "--topic=t1", "--phase=plan", "--status=confirmed")
        run(t1, "update-state", "--topic=t1", "--phase=impl", "--status=in-progress")
        run(t1, "update-state", "--topic=t1", "--phase=review", "--status=in-progress")
        run(t1, "update-state", "--topic=t1", "--phase=impl", "--status=in-progress")
        ctx = read_ctx(t1)
        assert ctx["topics"]["t1"]["phase"] == "impl"
        assert ctx["topics"]["t1"]["status"] == "in-progress"

    def test_same_state_transition_is_noop(self, t1):
        run(t1, "update-state", "--topic=t1", "--phase=spec", "--status=drafting")
        ctx = read_ctx(t1)
        assert ctx["topics"]["t1"]["phase"] == "spec"
        assert ctx["topics"]["t1"]["status"] == "drafting"

    def test_same_state_does_not_write_file(self, t1):
        before = Path(t1).read_text(encoding="utf-8")
        run(t1, "update-state", "--topic=t1", "--phase=spec", "--status=drafting")
        after = Path(t1).read_text(encoding="utf-8")
        assert before == after

    def test_missing_topic_non_zero(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=exists", "--spec=s.md")
        err = run_raw(ctx_path, "update-state", "--topic=ghost", "--phase=spec", "--status=reviewing")
        assert err.returncode != 0

    def test_invalid_transition_lists_allowed(self, t1):
        # 무효 전환 시 stderr에 allowed_transitions(from) 안내 포함
        err = run_raw(t1, "update-state", "--topic=t1", "--phase=plan", "--status=ready")
        assert err.returncode != 0
        assert "spec:reviewing" in err.stderr  # spec:drafting의 허용 다음 상태
