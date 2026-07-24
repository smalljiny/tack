"""Parity tests for the ``suggest-compact`` hook.

Asserted against byte-captured Node ground truth: the hook increments a
per-session tool-call counter file in the system temp dir and writes a
``[StrategicCompact]`` reminder to stderr at the threshold and every 25 calls
after it. It always exits 0 and never blocks.

Env is read INSIDE ``main()``/helpers, so tests set ``CLAUDE_SESSION_ID`` and
``COMPACT_THRESHOLD`` via ``monkeypatch.setenv`` and redirect the counter dir
by patching ``tempfile.gettempdir``.
"""

import tempfile

import pytest

from conftest import load_hook

MSG1 = "[StrategicCompact] 도구 호출 {n}회 — 다음 Task 시작 전 /compact 고려\n"
MSG2 = "[StrategicCompact] 도구 호출 {n}회 — 컨텍스트가 오래됐다면 /compact 좋은 시점\n"


@pytest.fixture
def hook():
    return load_hook("suggest-compact")


def _counter_path(tmp_path, session_id):
    return tmp_path / f"harness-tool-count-{session_id}"


def _prepare(monkeypatch, tmp_path, session_id, threshold=None):
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setenv("CLAUDE_SESSION_ID", session_id)
    monkeypatch.delenv("PPID", raising=False)
    if threshold is None:
        monkeypatch.delenv("COMPACT_THRESHOLD", raising=False)
    else:
        monkeypatch.setenv("COMPACT_THRESHOLD", threshold)


def test_first_call_creates_counter_at_one(hook, run_hook, monkeypatch, tmp_path):
    _prepare(monkeypatch, tmp_path, "sess-first")
    result = run_hook(hook, [])
    assert result.stderr == ""
    assert result.exit_code == 0
    assert _counter_path(tmp_path, "sess-first").read_text(encoding="utf-8") == "1"


def test_reaching_threshold_emits_msg1(hook, run_hook, monkeypatch, tmp_path):
    _prepare(monkeypatch, tmp_path, "sess-thr", threshold="50")
    _counter_path(tmp_path, "sess-thr").write_text("49", encoding="utf-8")
    result = run_hook(hook, [])
    assert result.stderr == MSG1.format(n=50)
    assert result.exit_code == 0


def test_reminder_interval_emits_msg2(hook, run_hook, monkeypatch, tmp_path):
    _prepare(monkeypatch, tmp_path, "sess-rem", threshold="50")
    # seed THRESHOLD+24 = 74 so count becomes 75, (75-50) % 25 == 0.
    _counter_path(tmp_path, "sess-rem").write_text("74", encoding="utf-8")
    result = run_hook(hook, [])
    assert result.stderr == MSG2.format(n=75)
    assert result.exit_code == 0


def test_in_between_count_is_silent(hook, run_hook, monkeypatch, tmp_path):
    _prepare(monkeypatch, tmp_path, "sess-btw", threshold="50")
    # seed 50 so count becomes 51: not == 50, and (51-50) % 25 != 0.
    _counter_path(tmp_path, "sess-btw").write_text("50", encoding="utf-8")
    result = run_hook(hook, [])
    assert result.stderr == ""
    assert result.exit_code == 0


def test_corrupt_counter_restarts_at_one(hook, run_hook, monkeypatch, tmp_path):
    _prepare(monkeypatch, tmp_path, "sess-corrupt", threshold="50")
    _counter_path(tmp_path, "sess-corrupt").write_text("garbage", encoding="utf-8")
    result = run_hook(hook, [])
    assert result.stderr == ""
    assert result.exit_code == 0
    assert _counter_path(tmp_path, "sess-corrupt").read_text(encoding="utf-8") == "1"


def test_non_utf8_counter_restarts_at_one(hook, run_hook, monkeypatch, tmp_path):
    # JS readFileSync(..,'utf8') lossily decodes invalid bytes and parseInt||0
    # yields 0. The port must mirror the catch-all: a non-UTF-8 counter -> 0,
    # count becomes 1, no crash, exit 0.
    _prepare(monkeypatch, tmp_path, "sess-badbytes", threshold="50")
    _counter_path(tmp_path, "sess-badbytes").write_bytes(b"\xff\xfe\x00bad")
    result = run_hook(hook, [])
    assert result.stderr == ""
    assert result.exit_code == 0
    assert _counter_path(tmp_path, "sess-badbytes").read_text(encoding="utf-8") == "1"


def test_counter_write_failure_is_silent(hook, run_hook, monkeypatch, tmp_path):
    # Point the temp dir at a non-existent path so the counter write raises.
    missing = tmp_path / "does-not-exist"
    _prepare(monkeypatch, missing, "sess-nowrite")
    result = run_hook(hook, [])
    assert result.stderr == ""
    assert result.exit_code == 0


def test_parseint_prefix_threshold_triggers(hook, run_hook, monkeypatch, tmp_path):
    # JS parseInt("1x", 10) == 1; with count == 1 that fires msg1.
    _prepare(monkeypatch, tmp_path, "sess-1x", threshold="1x")
    result = run_hook(hook, [])
    assert result.stderr == MSG1.format(n=1)
    assert result.exit_code == 0


def test_non_numeric_threshold_never_fires(hook, run_hook, monkeypatch, tmp_path):
    # JS parseInt("abc", 10) == NaN; all comparisons false -> no message ever.
    _prepare(monkeypatch, tmp_path, "sess-abc", threshold="abc")
    _counter_path(tmp_path, "sess-abc").write_text("49", encoding="utf-8")
    result = run_hook(hook, [])
    assert result.stderr == ""
    assert result.exit_code == 0
