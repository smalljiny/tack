"""Parity tests for the ``session-logger`` hook.

Asserted against byte-captured Node ground truth: the hook appends one compact
JSON line per invocation to ``<cwd>/.claude/sessions/<UTC-date>.jsonl``. Keys
appear in order ts, tool, file, topic; ``file`` is omitted when the arg is
empty and ``topic`` is omitted when no current topic is resolved. Non-ASCII is
kept raw (ensure_ascii=False) and there are no spaces in the serialization.

``ts`` is time-dependent, so its format is asserted via regex, not an exact
value. The hook always exits 0.
"""

import json
import re
from datetime import datetime, timezone

import pytest

from conftest import load_hook

TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


@pytest.fixture
def hook():
    return load_hook("session-logger")


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _log_path(project_dir):
    return project_dir / ".claude" / "sessions" / f"{_today()}.jsonl"


def _read_lines(project_dir):
    return _log_path(project_dir).read_text(encoding="utf-8").splitlines()


def test_full_entry_appended(hook, run_hook, project_dir, ctx_file):
    ctx_file(project_dir, {"current_topic": "한글토픽"})
    result = run_hook(hook, ["Edit", "src/foo.ts"])
    assert result.exit_code == 0
    lines = _read_lines(project_dir)
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["tool"] == "Edit"
    assert entry["file"] == "src/foo.ts"
    assert entry["topic"] == "한글토픽"
    assert TS_RE.match(entry["ts"])


def test_key_order_and_no_space_serialization(hook, run_hook, project_dir, ctx_file):
    ctx_file(project_dir, {"current_topic": "t1"})
    result = run_hook(hook, ["Edit", "src/foo.ts"])
    assert result.exit_code == 0
    raw = _read_lines(project_dir)[0]
    # Compact separators: no ", " and no ": " anywhere.
    assert ", " not in raw
    assert ": " not in raw
    assert raw.startswith('{"ts":"')
    # Key order ts < tool < file < topic.
    assert (
        raw.index('"ts"')
        < raw.index('"tool"')
        < raw.index('"file"')
        < raw.index('"topic"')
    )


def test_empty_file_arg_omits_file_key(hook, run_hook, project_dir):
    result = run_hook(hook, ["Read"])
    assert result.exit_code == 0
    entry = json.loads(_read_lines(project_dir)[0])
    assert "file" not in entry
    assert entry["tool"] == "Read"


def test_corrupt_dev_context_omits_topic(hook, run_hook, project_dir):
    ctx_path = project_dir / ".tack" / "local" / "dev-context.json"
    ctx_path.parent.mkdir(parents=True, exist_ok=True)
    ctx_path.write_text("{not valid json", encoding="utf-8")
    result = run_hook(hook, ["Read", "a.ts"])
    assert result.exit_code == 0
    entry = json.loads(_read_lines(project_dir)[0])
    assert "topic" not in entry


def test_non_dict_dev_context_omits_topic(hook, run_hook, project_dir, ctx_file):
    # Valid JSON but not an object (list/null/number): JS `context.current_topic`
    # yields undefined -> null; the port must mirror the catch-all and omit topic
    # + exit 0 rather than crashing on `.get`. json.dumps([]) == "[]".
    ctx_file(project_dir, [])
    result = run_hook(hook, ["Read", "a.ts"])
    assert result.exit_code == 0
    entry = json.loads(_read_lines(project_dir)[0])
    assert "topic" not in entry


def test_current_topic_included_raw_non_ascii(hook, run_hook, project_dir, ctx_file):
    ctx_file(project_dir, {"current_topic": "한글토픽"})
    result = run_hook(hook, ["Read"])
    assert result.exit_code == 0
    raw = _read_lines(project_dir)[0]
    # ensure_ascii=False keeps the topic raw, not \uXXXX-escaped.
    assert "한글토픽" in raw
    assert json.loads(raw)["topic"] == "한글토픽"


def test_no_tool_arg_defaults_to_unknown(hook, run_hook, project_dir):
    result = run_hook(hook, [])
    assert result.exit_code == 0
    entry = json.loads(_read_lines(project_dir)[0])
    assert entry["tool"] == "unknown"


def test_empty_tool_arg_defaults_to_unknown(hook, run_hook, project_dir):
    # JS `process.argv[2] || 'unknown'`: an explicit empty string also maps to
    # "unknown" (byte-verified against the Node hook).
    result = run_hook(hook, ["", "src/x.ts"])
    assert result.exit_code == 0
    entry = json.loads(_read_lines(project_dir)[0])
    assert entry["tool"] == "unknown"
    assert entry["file"] == "src/x.ts"


def test_sessions_dir_auto_created(hook, run_hook, project_dir):
    sessions_dir = project_dir / ".claude" / "sessions"
    assert not sessions_dir.exists()
    result = run_hook(hook, ["Read"])
    assert result.exit_code == 0
    assert sessions_dir.is_dir()
    assert _log_path(project_dir).exists()


def test_append_failure_is_silent(hook, run_hook, project_dir, monkeypatch):
    def _raise(*_args, **_kwargs):
        raise OSError("append boom")

    monkeypatch.setattr(hook, "_append_line", _raise)
    result = run_hook(hook, ["Read", "a.ts"])
    assert result.exit_code == 0
    assert result.stdout == ""
