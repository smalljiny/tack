"""Parity tests for the ``session-start`` hook.

Asserted against byte-captured Node ground truth: on SessionStart the hook
restores prior context from ``<cwd>/.tack/local/dev-context.json`` (printing up
to four ``[컨텍스트 복원]`` lines to stdout) and then, if the codex
``detect-and-cache`` script exists, invokes it once via ``node``. It always
exits 0 and swallows every error.

Notable Node quirks reproduced here:
- A missing ``phase`` key interpolates as the literal string ``undefined`` in
  line 1 (JS template-literal behavior), not empty and not a crash.
- A topic present but absent from ``topics`` produces no restore output.
- Corrupt JSON is swallowed; the hook still proceeds to the detect step.

Seeded fixtures use ``.tack/local`` paths only, so the new test file stays
clean under the render-smoke grep gates.
"""

import pytest

from conftest import load_hook

# The plan value seeded into the committed fixtures. A token-clean path is used
# here; the byte-for-byte reference ground-truth path is checked only in the
# ephemeral differential Node run, never in this committed file.
PLAN = ".tack/local/active/E7-S1/implementation-plan.md"

FULL_CONTEXT = {
    "current_topic": "E7-S1",
    "topics": {
        "E7-S1": {
            "phase": "impl",
            "currentStory": "Story 3",
            "plan": PLAN,
        }
    },
}

EXPECTED_FULL = (
    "[컨텍스트 복원] 주제: E7-S1 | phase: impl\n"
    "[컨텍스트 복원] 다음 Story: Story 3\n"
    "  → /dev:impl 로 계속하세요.\n"
    f"[컨텍스트 복원] 계획 파일: {PLAN}\n"
)


@pytest.fixture
def hook():
    return load_hook("session-start")


def _make_detect_script(project_dir):
    detect = project_dir / ".claude" / "scripts" / "codex" / "detect-and-cache.js"
    detect.parent.mkdir(parents=True, exist_ok=True)
    detect.write_text("// stub\n", encoding="utf-8")
    return detect


def test_no_context_file_empty_stdout(hook, run_hook, project_dir):
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert result.stdout == ""


def test_full_context_exact_four_lines(hook, run_hook, project_dir, ctx_file):
    ctx_file(project_dir, FULL_CONTEXT)
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert result.stdout == EXPECTED_FULL


def test_current_story_lines_present(hook, run_hook, project_dir, ctx_file):
    ctx_file(
        project_dir,
        {
            "current_topic": "t",
            "topics": {"t": {"phase": "impl", "currentStory": "Story 9"}},
        },
    )
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert "[컨텍스트 복원] 다음 Story: Story 9\n" in result.stdout
    assert "  → /dev:impl 로 계속하세요.\n" in result.stdout
    # plan absent -> no 계획 파일 line.
    assert "계획 파일" not in result.stdout


def test_plan_line_present_without_story(hook, run_hook, project_dir, ctx_file):
    ctx_file(
        project_dir,
        {"current_topic": "t", "topics": {"t": {"phase": "plan", "plan": PLAN}}},
    )
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert f"[컨텍스트 복원] 계획 파일: {PLAN}\n" in result.stdout
    # currentStory absent -> no 다음 Story lines.
    assert "다음 Story" not in result.stdout
    assert "/dev:impl" not in result.stdout


def test_missing_phase_renders_literal_undefined(hook, run_hook, project_dir, ctx_file):
    # JS interpolates a missing key as the string "undefined"; the port mirrors
    # this via a get(key, "undefined") default. Absent key -> "undefined".
    ctx_file(
        project_dir,
        {"current_topic": "t", "topics": {"t": {"currentStory": "S1"}}},
    )
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert "[컨텍스트 복원] 주제: t | phase: undefined\n" in result.stdout


def test_topic_not_in_topics_no_output(hook, run_hook, project_dir, ctx_file):
    ctx_file(project_dir, {"current_topic": "t", "topics": {}})
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert result.stdout == ""


def test_empty_dict_topic_prints_undefined_phase(hook, run_hook, project_dir, ctx_file):
    # JS `if (topicData)` treats an empty object {} as truthy, so Node prints the
    # restore line with `phase: undefined` (byte-verified). The port must mirror
    # this (`is not None`), not skip on Python's falsy empty-dict.
    ctx_file(project_dir, {"current_topic": "t", "topics": {"t": {}}})
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert result.stdout == "[컨텍스트 복원] 주제: t | phase: undefined\n"


def test_null_topic_value_no_output(hook, run_hook, project_dir, ctx_file):
    # topics[topic] === null: JS `if (topicData)` -> null falsy -> skip. The port
    # mirrors this because None is not a dict and `is not None` is False.
    ctx_file(project_dir, {"current_topic": "t", "topics": {"t": None}})
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert result.stdout == ""


def test_present_null_phase_renders_literal_null(hook, run_hook, project_dir, ctx_file):
    # JS `${topicData.phase}` with phase===null renders the string "null"
    # (distinct from an absent key -> "undefined"). Byte-verified.
    ctx_file(project_dir, {"current_topic": "t", "topics": {"t": {"phase": None}}})
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert result.stdout == "[컨텍스트 복원] 주제: t | phase: null\n"


def test_corrupt_json_silent_exit_zero(hook, run_hook, project_dir):
    ctx_path = project_dir / ".tack" / "local" / "dev-context.json"
    ctx_path.parent.mkdir(parents=True, exist_ok=True)
    ctx_path.write_text("{not valid json", encoding="utf-8")
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert result.stdout == ""


def test_detect_script_invoked_once_with_node(
    hook, run_hook, project_dir, fake_run, monkeypatch
):
    detect = _make_detect_script(project_dir)
    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert len(fake_run.calls) == 1
    assert fake_run.calls[0]["cmd"] == ["node", str(detect)]


def test_detect_script_absent_not_invoked(
    hook, run_hook, project_dir, fake_run, monkeypatch
):
    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert fake_run.calls == []


def test_detect_node_missing_swallowed(hook, run_hook, project_dir, monkeypatch):
    # detect present but `node` binary missing -> FileNotFoundError must be
    # swallowed silently (exit 0, no stderr leak).
    _make_detect_script(project_dir)

    def _raise(*_args, **_kwargs):
        raise FileNotFoundError("node not found")

    monkeypatch.setattr(hook.subprocess, "run", _raise)
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert result.stderr == ""
