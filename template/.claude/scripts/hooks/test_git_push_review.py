"""Parity tests for the ``git-push-review`` hook.

Asserted against byte-captured Node ground truth: on a ``git push`` command the
hook prints a 6-line checklist block (5 content lines + one empty line) to
stdout and exits 0; otherwise it prints nothing and exits 0.

``load_hook`` is imported directly (not only via fixture) to prove the reuse
path Stories 2-4 depend on.
"""

import subprocess

import pytest

from conftest import load_hook

# Byte-exact expected stdout. Each checklist line is indented with exactly two
# spaces + "□" + one space. The final print("") yields the trailing empty line,
# so the block ends with "?\n\n".
EXPECTED = (
    "[git push 전 확인 사항]\n"
    "  □ /dev:review 를 완료했는가?\n"
    "  □ /dev:verify 의 모든 게이트를 통과했는가?\n"
    "  □ console.log가 남아있지 않은가?\n"
    "  □ 시크릿이 커밋에 포함되지 않았는가?\n"
    "\n"
)


@pytest.fixture
def hook():
    return load_hook("git-push-review")


def test_git_push_prints_full_checklist(hook, run_hook):
    result = run_hook(hook, ["git push"])
    assert result.stdout == EXPECTED
    assert result.exit_code == 0


def test_dev_command_lines_preserved_verbatim(hook, run_hook):
    result = run_hook(hook, ["git push"])
    # Character-level preservation of the slash-command reference lines.
    assert "  □ /dev:review 를 완료했는가?\n" in result.stdout
    assert "  □ /dev:verify 의 모든 게이트를 통과했는가?\n" in result.stdout


def test_leading_whitespace_still_matches(hook, run_hook):
    result = run_hook(hook, ["  git push --force"])
    assert result.stdout == EXPECTED
    assert result.exit_code == 0


def test_git_status_produces_no_output(hook, run_hook):
    result = run_hook(hook, ["git status"])
    assert result.stdout == ""
    assert result.exit_code == 0


def test_no_argument_produces_no_output(hook, run_hook):
    result = run_hook(hook, [])
    assert result.stdout == ""
    assert result.exit_code == 0


def test_mid_string_match_does_not_trigger(hook, run_hook):
    result = run_hook(hook, ["echo git push"])
    assert result.stdout == ""
    assert result.exit_code == 0


def test_fake_run_records_argv_cwd_timeout_and_stdout(fake_run):
    # De-risks the shared subprocess recorder that Stories 2-4 depend on but
    # git-push-review itself does not exercise.
    fake_run.returncode = 0
    fake_run.stdout = "topic-x\n"
    result = fake_run(
        ["dev-context.js", "read", "--field=current_topic"],
        cwd="/tmp/proj",
        timeout=5,
        stdout=subprocess.PIPE,
    )
    assert isinstance(result, subprocess.CompletedProcess)
    assert result.returncode == 0
    assert result.stdout == "topic-x\n"
    assert len(fake_run.calls) == 1
    call = fake_run.calls[0]
    assert call["cmd"] == ["dev-context.js", "read", "--field=current_topic"]
    assert call["kwargs"]["cwd"] == "/tmp/proj"
    assert call["kwargs"]["timeout"] == 5
    assert call["kwargs"]["stdout"] is subprocess.PIPE


def test_fake_run_per_call_result_queue(fake_run):
    # De-risks the multi-call branching path Story 4 (console-log-audit) needs:
    # one git-diff-style call, then per-file grep calls with distinct results.
    fake_run.add_result(returncode=0, stdout="a.js\nb.js\n")
    fake_run.add_result(returncode=0, stdout="3:console.log(x)\n")
    fake_run.add_result(returncode=1, stdout="")
    first = fake_run(["git", "diff", "--name-only"])
    second = fake_run(["grep", "-n", "console.log", "a.js"])
    third = fake_run(["grep", "-n", "console.log", "b.js"])
    assert first.stdout == "a.js\nb.js\n"
    assert (second.returncode, second.stdout) == (0, "3:console.log(x)\n")
    assert third.returncode == 1
    # Queue exhausted -> falls back to scalar defaults.
    fake_run.stdout = "fallback"
    assert fake_run(["x"]).stdout == "fallback"
    assert len(fake_run.calls) == 4
