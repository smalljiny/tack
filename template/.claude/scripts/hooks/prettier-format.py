#!/usr/bin/env python3
"""PostToolUse 훅: JS/TS 파일 편집 후 Prettier로 자동 포맷한다.

Node 원본은 spawnSync를 LIST 형태로 호출해 npx 부재에도 예외를 던지지 않는다.
Python subprocess.run(list)은 바이너리 부재 시 FileNotFoundError를 던지므로,
spawnSync의 무음 관용을 재현하려 예외를 삼킨다. 파일 경로는 argv 요소로
전달되어 (LIST form, no shell) 셸 인젝션 표면이 없다.
"""

import os
import subprocess
import sys

SUPPORTED_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")

CONFIG_CANDIDATES = (
    ".prettierrc",
    ".prettierrc.json",
    ".prettierrc.js",
    ".prettierrc.cjs",
    "prettier.config.js",
    "prettier.config.cjs",
)


def get_cwd():
    return os.environ.get("PWD") or os.getcwd()


def is_supported_file(path):
    return any(path.endswith(ext) for ext in SUPPORTED_EXTENSIONS)


def has_prettier_config(cwd):
    return any(os.path.exists(os.path.join(cwd, c)) for c in CONFIG_CANDIDATES)


def main():
    file_path = sys.argv[1] if len(sys.argv) > 1 else ""
    cwd = get_cwd()

    if not file_path or not is_supported_file(file_path):
        sys.exit(0)

    if not has_prettier_config(cwd):
        sys.exit(0)

    try:
        subprocess.run(
            ["npx", "prettier", "--write", file_path],
            cwd=cwd,
            timeout=10,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        # spawnSync는 바이너리 부재·타임아웃에도 조용히 반환한다. 미러.
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
