"""Shared pytest infrastructure for hook parity tests (Stories 1-4).

The hooks under this directory are stdlib-only Python ports of the reference
Node hooks. Each hook exposes a ``main()`` guarded by
``if __name__ == "__main__": main()`` so importing the module never runs it.
These tests import the module, then call ``main()`` directly.

Helpers provided here:

- ``load_hook(name)``   import a hyphenated-filename hook module without running
                        ``main()``; returns the module object.
- ``project_dir``       fixture: a temp project root with ``PWD`` pointed at it.
- ``ctx_file``          fixture: writes a ``.tack/local/dev-context.json`` file
                        under a project root (used by Stories 2-4).
- ``fake_run``          fixture: a ``subprocess.run`` recorder + fake result.
- ``run_hook``          fixture: runs a hook's ``main()`` and returns
                        ``(stdout, stderr, exit_code)``, capturing ``SystemExit``.

File-side-effect assertion pattern (Stories 2-4)
------------------------------------------------
When a hook writes into the temp project tree, read the file back and assert
its contents. Example using the ``project_dir`` fixture root::

    out_path = project_dir / ".tack" / "local" / "dev-context.json"
    assert out_path.exists()
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["current_topic"] == "example"

The ``ctx_file`` fixture seeds that same JSON file before a hook runs, so a
test can assert the hook read it and rewrote the expected fields.
"""

import importlib.util
import json
import subprocess
import sys
from collections import namedtuple
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parent


def load_hook(name):
    """Import the hook module ``<name>.py`` without running ``main()``.

    ``name`` is the hyphenated filename stem (e.g. ``"git-push-review"``). The
    module is registered in ``sys.modules`` under the normalized name
    (hyphens -> underscores) before execution so coverage can measure it.
    """
    module_name = name.replace("-", "_")
    file_path = HOOKS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


HookResult = namedtuple("HookResult", ["stdout", "stderr", "exit_code"])


@pytest.fixture
def project_dir(tmp_path, monkeypatch):
    """A temp project root with ``PWD`` pointed at it."""
    monkeypatch.setenv("PWD", str(tmp_path))
    return tmp_path


@pytest.fixture
def ctx_file():
    """Return a writer that seeds ``.tack/local/dev-context.json``.

    Usage::

        ctx_file(project_dir, {"current_topic": "example"})
    """

    def _write(project_root, data):
        ctx_path = Path(project_root) / ".tack" / "local" / "dev-context.json"
        ctx_path.parent.mkdir(parents=True, exist_ok=True)
        ctx_path.write_text(json.dumps(data), encoding="utf-8")
        return ctx_path

    return _write


class FakeRun:
    """A ``subprocess.run`` stand-in that records calls and returns a fake result.

    Install via ``monkeypatch.setattr``. Two result modes:

    - **Scalar (default)**: every call returns the same result, configured by
      setting ``returncode`` / ``stdout`` / ``stderr`` before the hook runs.
      Sufficient for hooks that make a single subprocess call.
    - **Per-call queue**: for hooks that make several calls and branch on
      *distinct* results (e.g. one ``git diff`` listing files, then a ``grep``
      per file), enqueue results with ``add_result(returncode=, stdout=,
      stderr=)``. Each call pops the next queued result in FIFO order; once the
      queue is exhausted it falls back to the scalar attributes.

    Each call appends a dict to ``.calls`` recording the positional command
    (``cmd``), any extra positional ``args``, and the full ``kwargs`` dict — so
    a test can assert ANY passed argument (``cwd``, ``timeout``, ``check``,
    ``capture_output``, ``text``, ``encoding``, ``stdout`` redirection, ...)
    without editing this shared recorder. Read e.g. ``call["kwargs"]["cwd"]``.
    """

    def __init__(self):
        self.calls = []
        self.returncode = 0
        self.stdout = ""
        self.stderr = ""
        self.results = []

    def add_result(self, returncode=0, stdout="", stderr=""):
        """Enqueue a per-call result consumed FIFO by later ``__call__`` calls."""
        self.results.append(
            {"returncode": returncode, "stdout": stdout, "stderr": stderr}
        )

    def __call__(self, cmd, *args, **kwargs):
        self.calls.append({"cmd": cmd, "args": args, "kwargs": kwargs})
        if self.results:
            result = self.results.pop(0)
        else:
            result = {
                "returncode": self.returncode,
                "stdout": self.stdout,
                "stderr": self.stderr,
            }
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=result["returncode"],
            stdout=result["stdout"],
            stderr=result["stderr"],
        )


@pytest.fixture
def fake_run():
    """Return a fresh ``FakeRun`` recorder for a test."""
    return FakeRun()


@pytest.fixture
def run_hook(capsys, monkeypatch):
    """Run a hook's ``main()`` and return ``(stdout, stderr, exit_code)``.

    ``_run(module, argv_list)`` sets ``sys.argv`` to ``["hook", *argv_list]``,
    calls ``module.main()``, and captures ``SystemExit`` (a missing/None code
    maps to 0, matching a plain ``sys.exit()``). Streams come from ``capsys``.
    """

    def _run(module, argv_list):
        monkeypatch.setattr(sys, "argv", ["hook", *argv_list])
        exit_code = 0
        try:
            module.main()
        except SystemExit as exc:
            exit_code = 0 if exc.code is None else exc.code
        captured = capsys.readouterr()
        return HookResult(captured.out, captured.err, exit_code)

    return _run
