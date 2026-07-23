"""force-state 서브커맨드 (레퍼런스 dev-context.test.js L690-798)."""

import time

from _dc_helpers import read_ctx, run, run_raw


class TestForceState:
    def test_backward_recovery_succeeds_without_flag(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=ft", "--spec=spec.md")
        run(ctx_path, "update-state", "--topic=ft", "--phase=spec", "--status=reviewing")
        run(ctx_path, "force-state", "--topic=ft", "--phase=spec", "--status=drafting")
        ctx = read_ctx(ctx_path)
        assert ctx["topics"]["ft"]["phase"] == "spec"
        assert ctx["topics"]["ft"]["status"] == "drafting"

    def test_backward_recovery_stderr_warning(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=ft2", "--spec=spec.md")
        run(ctx_path, "update-state", "--topic=ft2", "--phase=spec", "--status=reviewing")
        result = run(ctx_path, "force-state", "--topic=ft2", "--phase=spec", "--status=drafting")
        assert "VALID_TRANSITIONS를 우회해" in result.stderr
        assert "관리자 용도" in result.stderr
        assert "[--allow-unsafe-force]" not in result.stderr  # 역방향은 note 미포함

    def test_forward_jump_without_flag_non_zero(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=ft2b", "--spec=spec.md")
        err = run_raw(ctx_path, "force-state", "--topic=ft2b", "--phase=plan", "--status=ready")
        assert err.returncode != 0
        assert "순방향 점프" in err.stderr
        assert "allow-unsafe-force" in err.stderr

    def test_forward_jump_with_flag_succeeds(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=ft2c", "--spec=spec.md")
        result = run(ctx_path, "force-state", "--topic=ft2c", "--phase=plan",
                     "--status=ready", "--allow-unsafe-force")
        ctx = read_ctx(ctx_path)
        assert ctx["topics"]["ft2c"]["phase"] == "plan"
        assert ctx["topics"]["ft2c"]["status"] == "ready"
        assert "[--allow-unsafe-force]" in result.stderr  # 순방향은 note 포함

    def test_same_state_is_noop_updatedat_unchanged(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=ft3", "--spec=spec.md")
        run(ctx_path, "force-state", "--topic=ft3", "--phase=spec", "--status=drafting")
        before = read_ctx(ctx_path)["topics"]["ft3"]["updatedAt"]
        run(ctx_path, "force-state", "--topic=ft3", "--phase=spec", "--status=drafting")
        after = read_ctx(ctx_path)["topics"]["ft3"]["updatedAt"]
        assert before == after

    def test_updatedat_refreshed(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=ft4", "--spec=spec.md")
        run(ctx_path, "update-state", "--topic=ft4", "--phase=spec", "--status=reviewing")
        before = read_ctx(ctx_path)["topics"]["ft4"]["updatedAt"]
        time.sleep(0.01)
        run(ctx_path, "force-state", "--topic=ft4", "--phase=spec", "--status=drafting")
        after = read_ctx(ctx_path)["topics"]["ft4"]["updatedAt"]
        assert before != after

    def test_missing_topic_flag_non_zero(self, ctx_path):
        err = run_raw(ctx_path, "force-state", "--phase=spec", "--status=drafting")
        assert err.returncode != 0

    def test_missing_phase_non_zero(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=ft5", "--spec=spec.md")
        err = run_raw(ctx_path, "force-state", "--topic=ft5", "--status=drafting")
        assert err.returncode != 0

    def test_nonexistent_topic_non_zero(self, ctx_path):
        err = run_raw(ctx_path, "force-state", "--topic=ghost", "--phase=spec", "--status=drafting")
        assert err.returncode != 0

    def test_unknown_state_non_zero(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=ft6", "--spec=spec.md")
        err = run_raw(ctx_path, "force-state", "--topic=ft6", "--phase=garbage", "--status=junk")
        assert err.returncode != 0
        assert "알 수 없는 상태" in err.stderr

    def test_missing_status_non_zero(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=ft8", "--spec=spec.md")
        err = run_raw(ctx_path, "force-state", "--topic=ft8", "--phase=spec")
        assert err.returncode != 0

    def test_proto_topic_name_non_zero(self, ctx_path):
        err = run_raw(ctx_path, "force-state", "--topic=__proto__", "--phase=spec", "--status=drafting")
        assert err.returncode != 0

    def test_constructor_topic_name_non_zero(self, ctx_path):
        err = run_raw(ctx_path, "force-state", "--topic=constructor", "--phase=spec", "--status=drafting")
        assert err.returncode != 0

    def test_prototype_topic_name_non_zero(self, ctx_path):
        err = run_raw(ctx_path, "force-state", "--topic=prototype", "--phase=spec", "--status=drafting")
        assert err.returncode != 0

    def test_update_state_still_enforces_valid_transitions(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=ft7", "--spec=spec.md")
        err = run_raw(ctx_path, "update-state", "--topic=ft7", "--phase=plan", "--status=ready")
        assert err.returncode != 0
        assert "유효하지 않은 전환" in err.stderr
