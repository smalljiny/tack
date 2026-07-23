"""dev_context.py 엔진 통합 테스트 (pytest).

레퍼런스 dev-context.js·dev-context.test.js(89 케이스)를 동작·외부 계약 패리티로
이식한다. 실제 repo dev-context.json을 건드리지 않도록 테스트별 독립 tmp 파일 경로에
DEV_CONTEXT_PATH env를 주입하고, subprocess로 `[sys.executable, SCRIPT, ...]`를 호출한다
(레퍼런스 테스트의 `['node', SCRIPT, ...]`와 대칭).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(SCRIPT_DIR, "dev_context.py")
NODE_SCRIPT = os.path.join(SCRIPT_DIR, "dev-context.js")
# ISO 타임스탬프(밀리초+Z) 정규화 — createdAt/updatedAt만 런타임마다 달라진다.
_ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z")


def run_raw(ctx_path, *args):
    """성공/실패 무관하게 CompletedProcess 반환 (실패 케이스용)."""
    env = {**os.environ, "DEV_CONTEXT_PATH": ctx_path}
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )


def run(ctx_path, *args):
    """서브커맨드를 실행하고 성공(exit 0)을 단언한 뒤 CompletedProcess 반환."""
    result = run_raw(ctx_path, *args)
    assert result.returncode == 0, (
        f"expected success, got exit {result.returncode}: {result.stderr}"
    )
    return result


def read_ctx(ctx_path):
    with open(ctx_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def ctx_path(tmp_path):
    """테스트별 독립 tmp 파일 경로 (파일은 생성하지 않음)."""
    return str(tmp_path / "dev-context.json")


# --- register-topic (레퍼런스 dev-context.test.js L60-131) ---


class TestRegisterTopic:
    def test_normal_registration_creates_spec_drafting(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=test-topic",
            "--spec=.tack/local/backlog/test-topic/spec.md")
        ctx = read_ctx(ctx_path)
        assert ctx["current_topic"] == "test-topic"
        assert ctx["topics"]["test-topic"]["phase"] == "spec"
        assert ctx["topics"]["test-topic"]["status"] == "drafting"
        assert ctx["topics"]["test-topic"]["spec"] == ".tack/local/backlog/test-topic/spec.md"

    def test_legacy_fields_removed(self, ctx_path):
        Path(ctx_path).write_text(json.dumps({
            "current_topic": None,
            "current_spec": "old/path",
            "specConfirmed": True,
            "planConfirmed": False,
            "topics": {},
            "updatedAt": "2026-01-01T00:00:00.000Z",
        }), encoding="utf-8")
        run(ctx_path, "register-topic", "--topic=legacy-test", "--spec=some/spec.md")
        ctx = read_ctx(ctx_path)
        assert "current_spec" not in ctx
        assert "specConfirmed" not in ctx
        assert "planConfirmed" not in ctx

    def test_registration_on_legacy_file_without_topics(self, ctx_path):
        Path(ctx_path).write_text(json.dumps({
            "current_spec": ".tack/local/backlog/legacy/spec.md",
            "updatedAt": "2026-01-01T00:00:00.000Z",
        }), encoding="utf-8")
        run(ctx_path, "register-topic", "--topic=legacy-only",
            "--spec=.tack/local/backlog/legacy-only/spec.md")
        ctx = read_ctx(ctx_path)
        assert "current_spec" not in ctx
        assert ctx["current_topic"] == "legacy-only"
        assert ctx["topics"]["legacy-only"]["phase"] == "spec"
        assert ctx["topics"]["legacy-only"]["status"] == "drafting"

    def test_file_auto_created_when_absent(self, ctx_path):
        assert not os.path.exists(ctx_path)
        run(ctx_path, "register-topic", "--topic=new-topic", "--spec=some/spec.md")
        assert os.path.exists(ctx_path)
        ctx = read_ctx(ctx_path)
        assert ctx["topics"]["new-topic"]["phase"] == "spec"

    def test_duplicate_registration_non_zero_exit(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=dup-topic", "--spec=some/spec.md")
        err = run_raw(ctx_path, "register-topic", "--topic=dup-topic", "--spec=other/spec.md")
        assert err.returncode != 0
        assert "이미 존재합니다" in err.stderr

    def test_nested_parent_path_file_creation(self, tmp_path):
        nested = str(tmp_path / "deep" / "path" / "dev-context.json")
        run(nested, "register-topic", "--topic=nested-test", "--spec=spec.md")
        assert os.path.exists(nested)
        ctx = read_ctx(nested)
        assert ctx["topics"]["nested-test"]["phase"] == "spec"


# --- T1.4: JSON round-trip byte-parity + default-path 격리 ---


class TestByteParityAndDefaultPath:
    def test_json_output_is_round_trip_idempotent(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=bp", "--spec=some/spec.md")
        raw = Path(ctx_path).read_text(encoding="utf-8")
        assert raw == json.dumps(json.loads(raw), indent=2, ensure_ascii=False) + "\n"

    def test_default_context_path_resolves_relative_to_script(self, monkeypatch):
        # env 미주입 상태에서 default 경로가 __file__ 기준으로 계산되는지만 검증.
        # 서브커맨드를 호출하지 않으므로 실제 repo dev-context.json에 접근하지 않는다.
        monkeypatch.delenv("DEV_CONTEXT_PATH", raising=False)
        import importlib

        import dev_context
        importlib.reload(dev_context)
        script_dir = os.path.dirname(os.path.abspath(dev_context.__file__))
        expected = os.path.normpath(
            os.path.join(script_dir, "..", "..", ".tack", "local", "dev-context.json")
        )
        assert dev_context.DEFAULT_CONTEXT_PATH == expected

    def test_env_override_takes_precedence(self, monkeypatch, tmp_path):
        override = str(tmp_path / "override.json")
        monkeypatch.setenv("DEV_CONTEXT_PATH", override)
        import importlib

        import dev_context
        importlib.reload(dev_context)
        assert dev_context.resolve_context_path() == override

    @pytest.mark.skipif(shutil.which("node") is None, reason="node 미설치")
    def test_byte_parity_against_node_reference(self, tmp_path):
        # 동일 입력으로 node·python 엔진을 각각 실행해 파일 raw bytes를 비교한다.
        # 런타임마다 달라지는 ISO 타임스탬프만 placeholder로 정규화 → 구조는 byte-for-byte 동일.
        node_path = str(tmp_path / "node.json")
        py_path = str(tmp_path / "py.json")
        args = ["register-topic", "--topic=parity", "--spec=.tack/local/backlog/parity/spec.md"]
        subprocess.run(
            ["node", NODE_SCRIPT, *args],
            check=True, capture_output=True, text=True,
            env={**os.environ, "DEV_CONTEXT_PATH": node_path},
        )
        run(py_path, *args)
        node_raw = _ISO_RE.sub("TS", Path(node_path).read_text(encoding="utf-8"))
        py_raw = _ISO_RE.sub("TS", Path(py_path).read_text(encoding="utf-8"))
        assert py_raw == node_raw


# --- update-state (레퍼런스 dev-context.test.js L133-207) ---


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


# --- set-field non-config (레퍼런스 dev-context.test.js L209-257) ---


class TestSetFieldNonConfig:
    @pytest.fixture
    def sf(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=sf-test", "--spec=some/spec.md")
        return ctx_path

    def test_general_field_update(self, sf):
        run(sf, "set-field", "--topic=sf-test", "--field=specReview",
            "--value=.tack/local/backlog/sf-test/spec-review-001.md")
        ctx = read_ctx(sf)
        assert ctx["topics"]["sf-test"]["specReview"] == ".tack/local/backlog/sf-test/spec-review-001.md"

    def test_current_story_null_setting(self, sf):
        run(sf, "set-field", "--topic=sf-test", "--field=currentStory", "--value=Story3")
        run(sf, "set-field", "--topic=sf-test", "--field=currentStory", "--value=null")
        ctx = read_ctx(sf)
        assert ctx["topics"]["sf-test"]["currentStory"] is None

    def test_phase_protected(self, sf):
        err = run_raw(sf, "set-field", "--topic=sf-test", "--field=phase", "--value=plan")
        assert err.returncode != 0
        assert "update-state 전용" in err.stderr

    def test_status_protected(self, sf):
        err = run_raw(sf, "set-field", "--topic=sf-test", "--field=status", "--value=confirmed")
        assert err.returncode != 0
        assert "update-state 전용" in err.stderr

    def test_current_topic_global_update(self, sf):
        run(sf, "register-topic", "--topic=other-topic", "--spec=other/spec.md")
        run(sf, "set-field", "--field=current_topic", "--value=sf-test")
        ctx = read_ctx(sf)
        assert ctx["current_topic"] == "sf-test"

    def test_current_topic_null_setting(self, sf):
        run(sf, "set-field", "--field=current_topic", "--value=null")
        ctx = read_ctx(sf)
        assert ctx["current_topic"] is None

    def test_current_topic_with_topic_flag_errors(self, sf):
        err = run_raw(sf, "set-field", "--topic=sf-test", "--field=current_topic", "--value=sf-test")
        assert err.returncode != 0
        assert "--topic과 함께 사용할 수 없습니다" in err.stderr

    def test_reserved_key_topic_field_rejected(self, sf):
        err = run_raw(sf, "set-field", "--topic=sf-test", "--field=__proto__", "--value=x")
        assert err.returncode != 0
        assert "사용할 수 없습니다" in err.stderr

    def test_missing_topic_die(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=exists", "--spec=s.md")
        err = run_raw(ctx_path, "set-field", "--topic=ghost", "--field=plan", "--value=x")
        assert err.returncode != 0

    def test_topic_field_stores_literal_string_no_coercion(self, sf):
        run(sf, "set-field", "--topic=sf-test", "--field=plan", "--value=true")
        ctx = read_ctx(sf)
        assert ctx["topics"]["sf-test"]["plan"] == "true"
        assert isinstance(ctx["topics"]["sf-test"]["plan"], str)

    def test_empty_string_value_accepted(self, sf):
        # 레퍼런스 value === undefined는 키 부재만 die — 빈 문자열은 유효 값(exit 0, "" 저장).
        # "falsy" 검사로 회귀하면 이 케이스가 깨진다.
        run(sf, "set-field", "--topic=sf-test", "--field=specReview", "--value=")
        ctx = read_ctx(sf)
        assert ctx["topics"]["sf-test"]["specReview"] == ""

    def test_missing_value_flag_dies(self, sf):
        err = run_raw(sf, "set-field", "--topic=sf-test", "--field=specReview")
        assert err.returncode != 0
        assert "--value 필요" in err.stderr


# --- currentTask → currentStory 마이그레이션 (레퍼런스 dev-context.test.js L259-321) ---


class TestCurrentTaskMigration:
    def test_currenttask_only_promoted_and_removed(self, ctx_path):
        Path(ctx_path).write_text(json.dumps({
            "current_topic": "legacy",
            "topics": {
                "legacy": {
                    "phase": "impl", "status": "in-progress",
                    "spec": ".tack/local/active/legacy/spec.md",
                    "specReview": None,
                    "plan": ".tack/local/active/legacy/implementation-plan.md",
                    "planReview": None,
                    "currentTask": "Task5",
                    "createdAt": "2026-01-01T00:00:00.000Z",
                    "updatedAt": "2026-01-01T00:00:00.000Z",
                },
            },
            "updatedAt": "2026-01-01T00:00:00.000Z",
        }), encoding="utf-8")
        # read→write 경로를 통과하는 어떤 쓰기든 마이그레이션을 영속화한다
        run(ctx_path, "set-field", "--topic=legacy", "--field=planReview",
            "--value=.tack/local/active/legacy/plan-review-001.md")
        ctx = read_ctx(ctx_path)
        assert ctx["topics"]["legacy"]["currentStory"] == "Task5"
        assert "currentTask" not in ctx["topics"]["legacy"]

    def test_both_fields_present_is_noop(self, ctx_path):
        Path(ctx_path).write_text(json.dumps({
            "current_topic": "both",
            "topics": {
                "both": {
                    "phase": "impl", "status": "in-progress",
                    "spec": ".tack/local/active/both/spec.md",
                    "specReview": None,
                    "plan": ".tack/local/active/both/implementation-plan.md",
                    "planReview": None,
                    "currentTask": "OldT",
                    "currentStory": "NewS",
                    "createdAt": "2026-01-01T00:00:00.000Z",
                    "updatedAt": "2026-01-01T00:00:00.000Z",
                },
            },
            "updatedAt": "2026-01-01T00:00:00.000Z",
        }), encoding="utf-8")
        run(ctx_path, "set-field", "--topic=both", "--field=planReview",
            "--value=.tack/local/active/both/plan-review-001.md")
        ctx = read_ctx(ctx_path)
        assert ctx["topics"]["both"]["currentStory"] == "NewS"
        assert ctx["topics"]["both"]["currentTask"] == "OldT"

    def test_register_topic_creates_currentstory_null_no_currenttask(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=fresh",
            "--spec=.tack/local/backlog/fresh/spec.md")
        ctx = read_ctx(ctx_path)
        assert ctx["topics"]["fresh"]["currentStory"] is None
        assert "currentTask" not in ctx["topics"]["fresh"]


# --- read non-config (레퍼런스 dev-context.test.js L323-365) + T5.3 non-stripped ---


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


# --- config 점 경로 plumbing (레퍼런스 dev-context.test.js L367-656) + T6.4 ---


class TestConfigPath:
    def _write_min(self, ctx_path, obj):
        Path(ctx_path).write_text(json.dumps(obj), encoding="utf-8")

    # 1. 설정값 한 줄 출력 / 미설정 빈 출력
    def test_read_config_set_value_one_line(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.dev_impl.auto_start", "--value=true")
        assert run(ctx_path, "read", "--field=config.dev_impl.auto_start").stdout.strip() == "true"

    def test_read_config_unset_empty(self, ctx_path):
        assert run(ctx_path, "read", "--field=config.dev_impl.auto_start").stdout.strip() == ""

    # 2. config.* + --topic → non-zero
    def test_read_config_with_topic_non_zero(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=cp-test", "--spec=some/spec.md")
        err = run_raw(ctx_path, "read", "--topic=cp-test", "--field=config.dev_impl.auto_start")
        assert err.returncode != 0

    # 3. 누락 세그먼트 → 빈 출력
    def test_read_config_missing_config_key(self, ctx_path):
        self._write_min(ctx_path, {"current_topic": None, "topics": {}, "updatedAt": "2026-01-01T00:00:00.000Z"})
        assert run(ctx_path, "read", "--field=config.dev_impl.auto_start").stdout.strip() == ""

    def test_read_config_missing_namespace(self, ctx_path):
        self._write_min(ctx_path, {"current_topic": None, "topics": {}, "config": {}, "updatedAt": "2026-01-01T00:00:00.000Z"})
        assert run(ctx_path, "read", "--field=config.dev_impl.auto_start").stdout.strip() == ""

    def test_read_config_missing_leaf(self, ctx_path):
        self._write_min(ctx_path, {"current_topic": None, "topics": {}, "config": {"dev_impl": {}}, "updatedAt": "2026-01-01T00:00:00.000Z"})
        assert run(ctx_path, "read", "--field=config.dev_impl.auto_start").stdout.strip() == ""

    # 4-7. 타입 추론
    def test_set_config_true_boolean(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.dev_impl.auto_start", "--value=true")
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["dev_impl"]["auto_start"] is True

    def test_set_config_false_boolean(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.dev_impl.auto_start", "--value=false")
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["dev_impl"]["auto_start"] is False

    def test_set_config_integer(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.some.count", "--value=42")
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["some"]["count"] == 42
        assert isinstance(ctx["config"]["some"]["count"], int)

    def test_set_config_negative_integer(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.some.count", "--value=-7")
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["some"]["count"] == -7
        assert isinstance(ctx["config"]["some"]["count"], int)

    def test_set_config_string(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.some.label", "--value=foo")
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["some"]["label"] == "foo"
        assert isinstance(ctx["config"]["some"]["label"], str)

    # 8-9. auto-create + config 키 영속화
    def test_set_config_auto_create_intermediate(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.dev_impl.auto_start", "--value=true")
        ctx = read_ctx(ctx_path)
        assert isinstance(ctx["config"], dict)
        assert isinstance(ctx["config"]["dev_impl"], dict)
        assert ctx["config"]["dev_impl"]["auto_start"] is True

    def test_config_key_persists_after_topic_set_field(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=sch-test", "--spec=some/spec.md")
        run(ctx_path, "set-field", "--topic=sch-test", "--field=plan", "--value=.tack/local/active/sch-test/plan.md")
        ctx = read_ctx(ctx_path)
        assert "config" in ctx
        assert isinstance(ctx["config"], dict)

    def test_read_config_on_configless_file_empty(self, ctx_path):
        self._write_min(ctx_path, {"current_topic": None, "topics": {}, "updatedAt": "2026-01-01T00:00:00.000Z"})
        assert run(ctx_path, "read", "--field=config.dev_impl.auto_start").stdout.strip() == ""

    # 10-11. 깊이 거부
    def test_read_config_depth_3_non_zero(self, ctx_path):
        err = run_raw(ctx_path, "read", "--field=config.dev_impl.auto_start.extra")
        assert err.returncode != 0

    def test_set_config_depth_1_non_zero(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.dev_impl", "--value=true")
        assert err.returncode != 0

    def test_set_config_depth_3_non_zero(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.a.b.c", "--value=true")
        assert err.returncode != 0

    def test_set_config_bare_non_zero(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config", "--value=true")
        assert err.returncode != 0

    # 12. config.* + --topic (set-field)
    def test_set_config_with_topic_non_zero(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=cp-topic-test", "--spec=some/spec.md")
        err = run_raw(ctx_path, "set-field", "--topic=cp-topic-test", "--field=config.dev_impl.auto_start", "--value=true")
        assert err.returncode != 0

    # 13. 회귀: 토픽 필드 문자열 보존
    def test_topic_field_string_preserved_regression(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=reg-test", "--spec=some/spec.md")
        run(ctx_path, "set-field", "--topic=reg-test", "--field=plan", "--value=true")
        ctx = read_ctx(ctx_path)
        assert ctx["topics"]["reg-test"]["plan"] == "true"
        assert isinstance(ctx["topics"]["reg-test"]["plan"], str)

    # 예약 키 방어
    def test_set_config_proto_reserved(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.__proto__.polluted", "--value=yes")
        assert err.returncode != 0
        assert "예약된 키" in err.stderr

    def test_set_config_constructor_reserved(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.constructor.x", "--value=y")
        assert err.returncode != 0

    def test_set_config_prototype_key_reserved(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.dev_impl.prototype", "--value=y")
        assert err.returncode != 0

    def test_read_config_proto_reserved(self, ctx_path):
        err = run_raw(ctx_path, "read", "--field=config.__proto__.toString")
        assert err.returncode != 0

    # hasOwn 가드: 상속 속성이 own으로 읽히지 않음
    def test_read_config_tostring_empty(self, ctx_path):
        self._write_min(ctx_path, {"current_topic": None, "topics": {}, "updatedAt": "2026-01-01T00:00:00.000Z"})
        assert run(ctx_path, "read", "--field=config.toString.name").stdout.strip() == ""

    def test_read_config_hasownproperty_empty(self, ctx_path):
        self._write_min(ctx_path, {"current_topic": None, "topics": {}, "updatedAt": "2026-01-01T00:00:00.000Z"})
        assert run(ctx_path, "read", "--field=config.hasOwnProperty.name").stdout.strip() == ""

    def test_read_config_valueof_empty(self, ctx_path):
        self._write_min(ctx_path, {"current_topic": None, "topics": {}, "updatedAt": "2026-01-01T00:00:00.000Z"})
        assert run(ctx_path, "read", "--field=config.valueOf.name").stdout.strip() == ""

    def test_set_config_own_property_reads_back(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.dev_impl.auto_start", "--value=true")
        assert run(ctx_path, "read", "--field=config.dev_impl.auto_start").stdout.strip() == "true"

    # 14. JSON 배열
    def test_set_config_json_array(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", '--value=[".claude/",".tack/"]')
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["docs"]["sourceFilter"] == [".claude/", ".tack/"]
        assert isinstance(ctx["config"]["docs"]["sourceFilter"], list)

    def test_read_config_array_newline_joined(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", '--value=[".claude/",".tack/","CLAUDE.md"]')
        assert run(ctx_path, "read", "--field=config.docs.sourceFilter").stdout.strip() == ".claude/\n.tack/\nCLAUDE.md"

    def test_set_config_empty_array(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", "--value=[]")
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["docs"]["sourceFilter"] == []
        assert isinstance(ctx["config"]["docs"]["sourceFilter"], list)

    def test_read_config_empty_array_empty_output(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", "--value=[]")
        assert run(ctx_path, "read", "--field=config.docs.sourceFilter").stdout.strip() == ""

    def test_set_config_non_string_element_int(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.docs.sourceFilter", "--value=[1,2]")
        assert err.returncode != 0
        assert "문자열 원소만 허용" in err.stderr

    def test_set_config_non_string_element_null(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.docs.sourceFilter", "--value=[null]")
        assert err.returncode != 0
        assert "문자열 원소만 허용" in err.stderr

    def test_set_config_unclosed_bracket_scalar(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", "--value=[invalid")
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["docs"]["sourceFilter"] == "[invalid"
        assert isinstance(ctx["config"]["docs"]["sourceFilter"], str)

    def test_set_config_regex_scalar_not_array(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.git.branchPattern", "--value=[A-Z].*")
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["git"]["branchPattern"] == "[A-Z].*"
        assert isinstance(ctx["config"]["git"]["branchPattern"], str)

    def test_set_config_newline_array_element(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.docs.sourceFilter", '--value=["src/\\nlib/"]')
        assert err.returncode != 0
        assert "줄바꿈" in err.stderr

    def test_empty_array_round_trip_zero_prefixes(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", "--value=[]")
        out = run(ctx_path, "read", "--field=config.docs.sourceFilter").stdout.strip()
        prefixes = [p for p in out.split("\n") if p]
        assert len(prefixes) == 0

    def test_topic_field_no_array_inference_regression(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=arr-reg", "--spec=some/spec.md")
        run(ctx_path, "set-field", "--topic=arr-reg", "--field=plan", '--value=["x"]')
        ctx = read_ctx(ctx_path)
        assert ctx["topics"]["arr-reg"]["plan"] == '["x"]'
        assert isinstance(ctx["topics"]["arr-reg"]["plan"], str)

    # T6.4 — non-stripped stdout + non-ASCII byte-parity
    def test_array_raw_stdout_non_stripped(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", '--value=["a","b","c"]')
        assert run(ctx_path, "read", "--field=config.docs.sourceFilter").stdout == "a\nb\nc\n"

    def test_empty_array_raw_stdout_is_newline_only(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", "--value=[]")
        assert run(ctx_path, "read", "--field=config.docs.sourceFilter").stdout == "\n"

    def test_non_ascii_config_value_byte_parity(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.some.label", "--value=한글")
        raw = Path(ctx_path).read_text(encoding="utf-8")
        assert "한글" in raw
        assert "\\u" not in raw  # ensure_ascii=False → escape 미포함

    def test_config_boolean_read_lowercase(self, ctx_path):
        # JS String(true)="true" — Python str(True)="True" 트랩 방어
        run(ctx_path, "set-field", "--field=config.dev_impl.auto_start", "--value=true")
        assert run(ctx_path, "read", "--field=config.dev_impl.auto_start").stdout == "true\n"


# --- remove-topic (레퍼런스 dev-context.test.js L658-688) ---


class TestRemoveTopic:
    def test_topic_deleted(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=rm-test", "--spec=some/spec.md")
        run(ctx_path, "remove-topic", "--topic=rm-test")
        ctx = read_ctx(ctx_path)
        assert "rm-test" not in ctx["topics"]

    def test_current_topic_reassigned_to_remaining(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=a", "--spec=spec-a.md")
        run(ctx_path, "register-topic", "--topic=b", "--spec=spec-b.md")
        assert run(ctx_path, "read", "--field=current_topic").stdout.strip() == "b"
        run(ctx_path, "remove-topic", "--topic=b")
        ctx = read_ctx(ctx_path)
        assert ctx["current_topic"] == "a"

    def test_last_topic_removal_sets_current_null(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=only", "--spec=spec.md")
        run(ctx_path, "remove-topic", "--topic=only")
        ctx = read_ctx(ctx_path)
        assert ctx["current_topic"] is None

    def test_remove_nonexistent_non_zero(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=exists", "--spec=s.md")
        err = run_raw(ctx_path, "remove-topic", "--topic=ghost")
        assert err.returncode != 0

    def test_missing_topic_flag_dies(self, ctx_path):
        err = run_raw(ctx_path, "remove-topic")
        assert err.returncode != 0

    def test_current_topic_unchanged_when_removing_other(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=a", "--spec=spec-a.md")
        run(ctx_path, "register-topic", "--topic=b", "--spec=spec-b.md")
        run(ctx_path, "set-field", "--field=current_topic", "--value=a")
        run(ctx_path, "remove-topic", "--topic=b")
        ctx = read_ctx(ctx_path)
        assert ctx["current_topic"] == "a"
        assert "a" in ctx["topics"]

    def test_empty_dict_topic_value_removed(self, ctx_path):
        # JS `if (!ctx.topics[topic])`는 {}를 truthy로 취급해 삭제를 진행한다.
        # naive `if not ...get(topic)`로 회귀하면 {} 토픽 삭제가 잘못 die한다.
        Path(ctx_path).write_text(json.dumps({
            "current_topic": "keep",
            "topics": {"weird": {}, "keep": {"phase": "spec", "status": "drafting"}},
            "updatedAt": "2026-01-01T00:00:00.000Z",
        }), encoding="utf-8")
        run(ctx_path, "remove-topic", "--topic=weird")
        ctx = read_ctx(ctx_path)
        assert "weird" not in ctx["topics"]
        assert ctx["current_topic"] == "keep"


# --- force-state (레퍼런스 dev-context.test.js L690-798) ---


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
