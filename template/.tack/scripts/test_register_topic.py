"""register-topic + JSON byte-parity·default-path (레퍼런스 dev-context.test.js L60-131)."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from _dc_helpers import NODE_SCRIPT, _ISO_RE, read_ctx, run, run_raw


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
