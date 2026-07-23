"""remove-topic 서브커맨드 (레퍼런스 dev-context.test.js L658-688)."""

import json
from pathlib import Path

from _dc_helpers import read_ctx, run, run_raw


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
