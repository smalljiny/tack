"""read non-config + T5.3 non-stripped stdout (레퍼런스 dev-context.test.js L323-365)."""

import pytest

from _dc_helpers import run, run_raw


class TestReadNonConfig:
    @pytest.fixture
    def rt(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=read-test",
            "--spec=.tack/local/backlog/read-test/spec.md")
        return ctx_path

    def test_read_phase(self, rt):
        assert run(rt, "read", "--topic=read-test", "--field=phase").stdout.strip() == "spec"

    def test_read_status(self, rt):
        assert run(rt, "read", "--topic=read-test", "--field=status").stdout.strip() == "drafting"

    def test_read_current_topic(self, rt):
        assert run(rt, "read", "--field=current_topic").stdout.strip() == "read-test"

    def test_read_spec_path(self, rt):
        out = run(rt, "read", "--topic=read-test", "--field=spec").stdout.strip()
        assert out == ".tack/local/backlog/read-test/spec.md"

    def test_read_nonexistent_topic_non_zero(self, rt):
        err = run_raw(rt, "read", "--topic=nonexistent", "--field=phase")
        assert err.returncode != 0

    def test_read_current_topic_with_topic_flag_errors(self, rt):
        err = run_raw(rt, "read", "--topic=read-test", "--field=current_topic")
        assert err.returncode != 0
        assert "--topic과 함께 사용할 수 없습니다" in err.stderr

    def test_read_missing_field_shows_usage(self, rt):
        err = run_raw(rt, "read")
        assert err.returncode != 0
        assert "--field" in err.stderr
        assert "사용 가능한 호출 형태" in err.stderr

    # T5.3 — non-stripped stdout byte-parity (trailing-newline 계약 G5a)
    def test_null_field_raw_stdout_is_newline_only(self, rt):
        # specReview는 register-topic 시 null → raw stdout이 정확히 "\n"
        result = run(rt, "read", "--topic=read-test", "--field=specReview")
        assert result.stdout == "\n"

    def test_scalar_field_raw_stdout_has_trailing_newline(self, rt):
        result = run(rt, "read", "--topic=read-test", "--field=phase")
        assert result.stdout == "spec\n"
