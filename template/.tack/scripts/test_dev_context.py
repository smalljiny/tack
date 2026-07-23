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
