"""Parity tests for the ``memory-persist`` hook.

Asserted against byte-captured Node ground truth: on Stop the hook refreshes
``topics[current_topic].updatedAt`` to a fresh millisecond-ISO timestamp and
rewrites ``<cwd>/.tack/local/dev-context.json`` as 2-space-indented JSON with a
trailing newline, preserving every other key/value in order and keeping
non-ASCII raw (ensure_ascii=False). When there is no context file, no current
topic, the topic is absent from ``topics``, or the JSON is corrupt, the file is
left byte-unchanged. The hook always exits 0.

``updatedAt`` is time-dependent, so its format is asserted via regex.
"""

import json
import re

import pytest

from conftest import load_hook

TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


@pytest.fixture
def hook():
    return load_hook("memory-persist")


def _ctx_path(project_dir):
    return project_dir / ".tack" / "local" / "dev-context.json"


def test_no_context_file_creates_nothing(hook, run_hook, project_dir):
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert not _ctx_path(project_dir).exists()


def test_current_topic_null_leaves_file_unchanged(hook, run_hook, project_dir, ctx_file):
    data = {"current_topic": None, "topics": {"t": {"phase": "impl"}}}
    ctx = ctx_file(project_dir, data)
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert ctx.read_text(encoding="utf-8") == json.dumps(data)


def test_topic_absent_from_topics_leaves_file_unchanged(
    hook, run_hook, project_dir, ctx_file
):
    data = {"current_topic": "t", "topics": {}}
    ctx = ctx_file(project_dir, data)
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert ctx.read_text(encoding="utf-8") == json.dumps(data)


def test_normal_updates_only_updatedat_preserving_rest(
    hook, run_hook, project_dir, ctx_file
):
    original = {
        "current_topic": "E7-S1",
        "topics": {
            "E7-S1": {
                "phase": "impl",
                "currentStory": "Story 3",
                "한글키": "한글값",
            }
        },
        "meta": {"count": 3, "flag": True},
    }
    ctx_file(project_dir, original)
    result = run_hook(hook, [])
    assert result.exit_code == 0
    written = json.loads(_ctx_path(project_dir).read_text(encoding="utf-8"))
    # updatedAt added with the ms-ISO format.
    assert TS_RE.match(written["topics"]["E7-S1"]["updatedAt"])
    # Every other key/value preserved, including the non-ASCII key/value.
    assert written["current_topic"] == "E7-S1"
    assert written["topics"]["E7-S1"]["phase"] == "impl"
    assert written["topics"]["E7-S1"]["currentStory"] == "Story 3"
    assert written["topics"]["E7-S1"]["한글키"] == "한글값"
    assert written["meta"] == {"count": 3, "flag": True}
    # Dropping the added updatedAt yields the exact original structure.
    del written["topics"]["E7-S1"]["updatedAt"]
    assert written == original


def test_output_format_indent_trailing_newline_raw_unicode(
    hook, run_hook, project_dir, ctx_file
):
    ctx_file(
        project_dir,
        {"current_topic": "t", "topics": {"t": {"note": "한글값"}}},
    )
    result = run_hook(hook, [])
    assert result.exit_code == 0
    raw = _ctx_path(project_dir).read_text(encoding="utf-8")
    # 2-space indent block opening and trailing newline after the final brace.
    assert raw.startswith("{\n  ")
    assert raw.endswith("}\n")
    # ensure_ascii=False keeps the value raw, not \uXXXX-escaped.
    assert "한글값" in raw
    assert "\\u" not in raw


def test_null_topic_value_leaves_file_unchanged(hook, run_hook, project_dir, ctx_file):
    # topics[topic] === null: JS `!context.topics?.[topic]` -> true -> exit w/o
    # write. Python proceeds past the membership check, then None["updatedAt"]
    # raises TypeError (caught) before the write reopens the file -> byte-
    # unchanged. Same observable outcome, exit 0. (File-side-effect parity.)
    data = {"current_topic": "t", "topics": {"t": None}}
    ctx = ctx_file(project_dir, data)
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert ctx.read_text(encoding="utf-8") == json.dumps(data)


def test_corrupt_json_silent_file_unchanged(hook, run_hook, project_dir):
    ctx = _ctx_path(project_dir)
    ctx.parent.mkdir(parents=True, exist_ok=True)
    seeded = "{not valid json"
    ctx.write_text(seeded, encoding="utf-8")
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert ctx.read_text(encoding="utf-8") == seeded
