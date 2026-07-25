"""Parity tests for the ``type-check`` hook.

Node source runs ``npx tsc --noEmit 2>&1`` via ``execSync``, which THROWS on a
non-zero exit; the catch block reads ``error.stdout`` (tsc's merged output) and
warns. Python ``subprocess.run`` does NOT raise on non-zero, so the port must
branch on ``result.returncode != 0`` — a naive ``try/except`` would never warn.
These tests pin that returncode-branch, the two ``console.warn`` -> stderr
lines, the 500-char truncation, and the fixed literal command string.

The command ``"npx tsc --noEmit 2>&1"`` is a fixed literal (no file path or env
interpolated), satisfying the shell-injection security criterion.
"""

import subprocess

import pytest

from conftest import load_hook


@pytest.fixture
def hook():
    return load_hook("type-check")


def _make_tsconfig(project_dir):
    (project_dir / "tsconfig.json").write_text("{}", encoding="utf-8")


def test_non_ts_arg_skips_subprocess(hook, run_hook, project_dir, fake_run, monkeypatch):
    _make_tsconfig(project_dir)
    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    result = run_hook(hook, ["notes.py"])
    assert result.exit_code == 0
    assert fake_run.calls == []


def test_no_tsconfig_skips_subprocess(hook, run_hook, project_dir, fake_run, monkeypatch):
    # .ts file but no tsconfig.json under cwd -> skip, no subprocess.
    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    result = run_hook(hook, ["src/app.ts"])
    assert result.exit_code == 0
    assert fake_run.calls == []


def test_returncode_zero_no_output(hook, run_hook, project_dir, fake_run, monkeypatch):
    _make_tsconfig(project_dir)
    fake_run.returncode = 0
    fake_run.stdout = ""
    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    result = run_hook(hook, ["src/app.ts"])
    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout == ""
    # Command is the fixed literal, shell=True.
    call = fake_run.calls[0]
    assert call["cmd"] == "npx tsc --noEmit 2>&1"
    assert call["kwargs"]["shell"] is True
    assert call["kwargs"]["cwd"] == str(project_dir)
    # Node pins encoding:'utf-8'; guard against a regression to text=True (which
    # decodes with the locale encoding and crashes on non-ASCII under LC_ALL=C).
    assert call["kwargs"]["encoding"] == "utf-8"
    assert call["kwargs"]["errors"] == "replace"


def test_returncode_nonzero_warns_on_stderr_truncated(
    hook, run_hook, project_dir, fake_run, monkeypatch
):
    _make_tsconfig(project_dir)
    payload = "x" * 600
    fake_run.returncode = 1
    fake_run.stdout = payload
    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    result = run_hook(hook, ["src/app.tsx"])
    assert result.exit_code == 0
    # Output goes to STDERR (Node console.warn), not stdout.
    assert result.stdout == ""
    assert "[타입 체크] 오류 발견:" in result.stderr
    # Truncated at 500 chars of the payload.
    assert result.stderr.count("x") == 500
    # Two console.warn calls -> two trailing newlines; exact shape.
    assert result.stderr == "[타입 체크] 오류 발견:\n" + "x" * 500 + "\n"


def test_returncode_nonzero_empty_output_no_warn(
    hook, run_hook, project_dir, fake_run, monkeypatch
):
    _make_tsconfig(project_dir)
    fake_run.returncode = 2
    fake_run.stdout = "   \n  "  # whitespace-only -> .strip() empty
    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    result = run_hook(hook, ["src/app.ts"])
    assert result.exit_code == 0
    assert result.stderr == ""


def test_timeout_survives(hook, run_hook, project_dir, monkeypatch):
    _make_tsconfig(project_dir)

    def _raise(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="npx tsc --noEmit 2>&1", timeout=30)

    monkeypatch.setattr(hook.subprocess, "run", _raise)
    result = run_hook(hook, ["src/app.ts"])
    assert result.exit_code == 0
    assert result.stderr == ""
