#!/usr/bin/env python3
"""PostToolUse 훅: TypeScript 파일 편집 후 타입 체크를 실행한다.
.ts, .tsx 파일에만 동작한다.

Node 원본은 execSync가 non-zero exit 시 throw하고 catch에서 경고를 출력한다.
Python subprocess.run은 non-zero에 예외를 던지지 않으므로 returncode로 분기한다
(check=True 미사용). 명령 문자열은 고정 리터럴이라 셸 인젝션 표면이 없다.
"""

import os
import subprocess
import sys


def get_cwd():
    return os.environ.get("PWD") or os.getcwd()


def is_typescript_file(path):
    return path.endswith(".ts") or path.endswith(".tsx")


def has_tsconfig(cwd):
    return os.path.exists(os.path.join(cwd, "tsconfig.json"))


def emit_warning(output):
    # Node console.warn 2회 -> stderr 2줄 (각 \n 추가).
    if output and output.strip():
        print("[타입 체크] 오류 발견:", file=sys.stderr)
        print(output[:500], file=sys.stderr)


def main():
    file_path = sys.argv[1] if len(sys.argv) > 1 else ""
    cwd = get_cwd()

    # TypeScript 파일이 아니면 스킵
    if not is_typescript_file(file_path):
        sys.exit(0)

    # tsconfig.json이 없으면 스킵
    if not has_tsconfig(cwd):
        sys.exit(0)

    try:
        result = subprocess.run(
            "npx tsc --noEmit 2>&1",
            shell=True,
            cwd=cwd,
            capture_output=True,
            # Node는 encoding:'utf-8'를 고정한다. text=True는 로케일 인코딩(C 로케일
            # 등에서 ASCII)으로 strict 디코딩해 non-ASCII 출력에 UnicodeDecodeError를
            # 던지므로, Node의 lenient utf-8 디코딩을 encoding+errors로 미러한다.
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        # 타임아웃 시 부분 출력이 exc.stdout에 담길 수 있다 (None/bytes 가능).
        partial = exc.stdout
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", errors="replace")
        emit_warning(partial or "")
        sys.exit(0)

    # 오류 감지는 returncode로 분기한다 (execSync throw 미러). 2>&1로 병합된
    # 출력이 stdout에 담긴다.
    output = result.stdout or ""
    if result.returncode != 0:
        # Node는 error.stdout이 비면 error.message로 폴백하지만, 2>&1 하에서
        # 실제 tsc/npx 오류는 stdout에 실려 도달 경로에서 output이 비지 않는다.
        # returncode!=0 + 완전 빈 stdout은 도달 불가한 발산으로 수용한다.
        emit_warning(output)

    sys.exit(0)


if __name__ == "__main__":
    main()
