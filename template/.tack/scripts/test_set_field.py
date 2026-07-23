"""set-field non-config + currentTask→currentStory 마이그레이션
(레퍼런스 dev-context.test.js L209-321)."""

import json
from pathlib import Path

import pytest

from _dc_helpers import read_ctx, run, run_raw


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
