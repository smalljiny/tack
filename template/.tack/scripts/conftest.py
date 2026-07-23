"""pytest 설정 — 서브프로세스 커버리지 측정 배선.

test_dev_context.py는 CLI 계약(exit code·stdout·stderr)을 검증하려고 dev_context.py를
`subprocess.run([sys.executable, SCRIPT, ...])`로 실행한다(OQ2). pytest-cov는 기본적으로
서브프로세스 실행을 측정하지 못하므로, `--cov` 활성 시에만 coverage.process_startup()을
서브프로세스 시작 시 호출하도록 COVERAGE_PROCESS_START + PYTHONPATH(sitecustomize)를 주입한다.
`--cov` 미사용(일반 배포 프로젝트의 pytest 실행)에서는 아무것도 하지 않는다.
"""

import os
import pathlib
import tempfile


def pytest_configure(config):
    # coverage(--cov)가 활성일 때만 서브프로세스 측정을 배선한다.
    if not config.pluginmanager.hasplugin("pytest_cov"):
        return
    if not config.getoption("--cov", default=None):
        return

    rootdir = pathlib.Path(str(config.rootpath))
    # boot 파일(sitecustomize·coveragerc)은 시스템 tempdir에 둔다 — repo 트리를 오염시키지 않는다.
    boot_dir = pathlib.Path(tempfile.mkdtemp(prefix="cov_subprocess_boot_"))

    data_file = rootdir / ".coverage"
    rc = boot_dir / "coveragerc"
    rc.write_text(
        "[run]\n"
        "parallel = true\n"
        "include = */dev_context.py\n"
        f"data_file = {data_file}\n",
        encoding="utf-8",
    )
    # 서브프로세스 Python이 시작 시 자동 import하는 sitecustomize (sys.path[0]=스크립트 dir,
    # 여기에 boot_dir을 PYTHONPATH로 추가). COVERAGE_PROCESS_START가 있을 때만 측정 시작.
    (boot_dir / "sitecustomize.py").write_text(
        "import coverage\ncoverage.process_startup()\n", encoding="utf-8"
    )

    os.environ["COVERAGE_PROCESS_START"] = str(rc)
    existing = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = (
        str(boot_dir) + (os.pathsep + existing if existing else "")
    )
