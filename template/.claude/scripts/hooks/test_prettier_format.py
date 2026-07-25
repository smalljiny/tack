"""Parity tests for the ``prettier-format`` hook.

Node source calls ``spawnSync('npx', ['prettier','--write',filePath], ...)`` — a
LIST-form spawn that NEVER throws even if ``npx`` is missing. Python
``subprocess.run(["npx", ...])`` RAISES ``FileNotFoundError`` on a missing
binary, so the port wraps the call in ``except (FileNotFoundError, OSError,
subprocess.TimeoutExpired): pass`` to reproduce spawnSync's silent tolerance.

The call uses LIST form (no shell), so the file path is passed as an argv
element — no shell-injection surface.
"""

import subprocess

import pytest

from conftest import load_hook

SUPPORTED = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]


@pytest.fixture
def hook():
    return load_hook("prettier-format")


def _make_config(project_dir, name=".prettierrc"):
    (project_dir / name).write_text("{}", encoding="utf-8")


@pytest.mark.parametrize("ext", SUPPORTED)
def test_supported_extensions_invoke_prettier(
    hook, run_hook, project_dir, fake_run, monkeypatch, ext
):
    _make_config(project_dir)
    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    result = run_hook(hook, [f"src/file{ext}"])
    assert result.exit_code == 0
    assert len(fake_run.calls) == 1


@pytest.mark.parametrize("arg", ["notes.md", ""])
def test_unsupported_or_empty_arg_skips(
    hook, run_hook, project_dir, fake_run, monkeypatch, arg
):
    _make_config(project_dir)
    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    result = run_hook(hook, [arg] if arg else [])
    assert result.exit_code == 0
    assert fake_run.calls == []


def test_config_gate(hook, run_hook, project_dir, fake_run, monkeypatch):
    # No config file present -> not called.
    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    result = run_hook(hook, ["src/app.ts"])
    assert result.exit_code == 0
    assert fake_run.calls == []
    # With any of the accepted config filenames -> called.
    _make_config(project_dir, "prettier.config.cjs")
    result = run_hook(hook, ["src/app.ts"])
    assert result.exit_code == 0
    assert len(fake_run.calls) == 1


def test_argv_shape_and_kwargs(hook, run_hook, project_dir, fake_run, monkeypatch):
    _make_config(project_dir)
    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    path = "src/deep/app.tsx"
    result = run_hook(hook, [path])
    assert result.exit_code == 0
    call = fake_run.calls[0]
    assert call["cmd"] == ["npx", "prettier", "--write", path]
    assert call["kwargs"]["cwd"] == str(project_dir)
    assert call["kwargs"]["timeout"] == 10


def test_missing_binary_and_timeout_are_silent(
    hook, run_hook, project_dir, monkeypatch
):
    _make_config(project_dir)

    def _raise_fnf(*_a, **_k):
        raise FileNotFoundError("npx not found")

    monkeypatch.setattr(hook.subprocess, "run", _raise_fnf)
    result = run_hook(hook, ["src/app.ts"])
    assert result.exit_code == 0
    assert result.stderr == ""

    def _raise_timeout(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd=["npx", "prettier"], timeout=10)

    monkeypatch.setattr(hook.subprocess, "run", _raise_timeout)
    result = run_hook(hook, ["src/app.ts"])
    assert result.exit_code == 0
    assert result.stderr == ""
