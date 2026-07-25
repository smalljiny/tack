"""Parity tests for the ``console-log-audit`` hook.

Node source: ``getModifiedFiles`` runs ``git diff --name-only HEAD 2>/dev/null``
via ``execSync`` (THROWS on non-zero -> ``[]``); the port branches on
``result.returncode != 0`` -> ``[]``. ``checkConsoleLog`` runs
``spawnSync('grep', ['-n','console\\.log', file], ...)`` per file (LIST form,
never throws in Node); the port wraps the list-form call in
``except (FileNotFoundError, OSError, subprocess.TimeoutExpired): continue``.

Both shell strings are fixed literals (no interpolation), satisfying the
shell-injection security criterion. The exact stderr report below is byte
ground-truth captured from the real Node hook.
"""

import subprocess

import pytest

from conftest import load_hook

GIT_DIFF_CMD = "git diff --name-only HEAD 2>/dev/null"

# Byte-for-byte Node ground truth for two violating files a.ts (lines 2,3) and
# c.js (line 2). Every console.warn adds a trailing \n; the leading \n in the
# 📁 and footer templates produce the blank lines.
EXPECTED_REPORT = (
    "[console.log 감사] 다음 파일에 console.log가 남아있습니다:\n"
    "\n  📁 a.ts\n"
    "    2:console.log(x)\n"
    '    3:console.log("two")\n'
    "\n  📁 c.js\n"
    '    2:console.log("c")\n'
    "\n  커밋 전에 제거하거나 적절한 logger로 교체하세요.\n"
)


@pytest.fixture
def hook():
    return load_hook("console-log-audit")


def test_git_diff_nonzero_no_violations(hook, run_hook, project_dir, fake_run, monkeypatch):
    fake_run.add_result(returncode=1, stdout="")
    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert result.stderr == ""
    # Only the git diff call; grep NOT called.
    assert len(fake_run.calls) == 1
    assert fake_run.calls[0]["cmd"] == GIT_DIFF_CMD
    assert fake_run.calls[0]["kwargs"]["shell"] is True
    # Node pins encoding:'utf-8'; guard against a regression to text=True.
    assert fake_run.calls[0]["kwargs"]["encoding"] == "utf-8"
    assert fake_run.calls[0]["kwargs"]["errors"] == "replace"


def test_git_diff_empty_no_grep(hook, run_hook, project_dir, fake_run, monkeypatch):
    fake_run.add_result(returncode=0, stdout="")
    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert result.stderr == ""
    assert len(fake_run.calls) == 1


def test_file_filtering(hook, run_hook, project_dir, fake_run, monkeypatch):
    # Only .ts/.tsx/.js/.jsx pass; .md and .py excluded.
    fake_run.add_result(returncode=0, stdout="a.ts\nb.md\nc.py\nd.js")
    fake_run.add_result(returncode=1, stdout="")  # grep a.ts (no match)
    fake_run.add_result(returncode=1, stdout="")  # grep d.js (no match)
    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    result = run_hook(hook, [])
    assert result.exit_code == 0
    grep_calls = fake_run.calls[1:]
    assert len(grep_calls) == 2
    assert grep_calls[0]["cmd"] == ["grep", "-n", "console\\.log", "a.ts"]
    assert grep_calls[1]["cmd"] == ["grep", "-n", "console\\.log", "d.js"]
    # Node pins encoding:'utf-8' on grep; guard against a regression to text=True.
    assert grep_calls[0]["kwargs"]["encoding"] == "utf-8"
    assert grep_calls[0]["kwargs"]["errors"] == "replace"


def test_exact_report_two_files(hook, run_hook, project_dir, fake_run, monkeypatch):
    fake_run.add_result(returncode=0, stdout="a.ts\nc.js")
    fake_run.add_result(returncode=0, stdout='2:console.log(x)\n3:console.log("two")')
    fake_run.add_result(returncode=0, stdout='2:console.log("c")')
    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert result.stderr == EXPECTED_REPORT
    assert result.stdout == ""


def test_grep_no_match_no_violation(hook, run_hook, project_dir, fake_run, monkeypatch):
    fake_run.add_result(returncode=0, stdout="a.ts")
    fake_run.add_result(returncode=1, stdout="")
    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert result.stderr == ""


def test_grep_missing_binary_skipped_silently(hook, run_hook, project_dir, monkeypatch):
    recorded = []

    def _run(cmd, *_a, **_k):
        recorded.append(cmd)
        if isinstance(cmd, str):  # git diff
            return subprocess.CompletedProcess(cmd, 0, stdout="a.ts\n", stderr="")
        raise FileNotFoundError("grep not found")

    monkeypatch.setattr(hook.subprocess, "run", _run)
    result = run_hook(hook, [])
    assert result.exit_code == 0
    assert result.stderr == ""
    # git diff + one grep attempt (which raised and was swallowed).
    assert len(recorded) == 2


def test_real_subprocess_non_ascii_console_log(hook, run_hook, project_dir, monkeypatch):
    # Integration guard for the encoding fix: with a REAL git+grep against a file
    # whose console.log holds non-ASCII (한글), the pinned encoding='utf-8' must
    # decode grep's stdout without crashing, even under an ASCII locale where
    # text=True would raise UnicodeDecodeError. Reproduces the reported defect.
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("LANG", "C")

    def _git(*args, **kwargs):
        subprocess.run(["git", *args], cwd=str(project_dir), check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    _git("init")
    _git("config", "user.email", "t@t")
    _git("config", "user.name", "t")
    (project_dir / "a.ts").write_text("const x = 1\n", encoding="utf-8")
    _git("add", "-A")
    _git("commit", "-m", "init")
    (project_dir / "a.ts").write_text(
        'const x = 1\nconsole.log("한글 메시지")\n', encoding="utf-8"
    )

    result = run_hook(hook, [])
    assert result.exit_code == 0
    # The Korean line is surfaced in the report, not a crash.
    assert "한글 메시지" in result.stderr
    assert "  📁 a.ts" in result.stderr
