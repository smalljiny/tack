#!/usr/bin/env python3
"""Stop 훅: 세션 중 수정된 파일에서 console.log를 감사한다.

Node 원본: getModifiedFiles는 execSync로 git diff를 실행하고 throw 시 []를
반환한다 -> Python은 returncode로 분기한다 (check=True 미사용). checkConsoleLog는
spawnSync를 LIST 형태로 grep 호출하며 throw하지 않는다 -> Python은 list-form
호출을 예외로 감싸 무음 skip한다. git diff 명령은 고정 리터럴이라 셸 인젝션
표면이 없다.
"""

import os
import subprocess
import sys


def get_cwd():
    return os.environ.get("PWD") or os.getcwd()


def get_modified_files(cwd):
    try:
        result = subprocess.run(
            "git diff --name-only HEAD 2>/dev/null",
            shell=True,
            cwd=cwd,
            capture_output=True,
            # Node encoding:'utf-8' 미러. text=True의 로케일 strict 디코딩이 non-ASCII
            # 파일명에 UnicodeDecodeError를 던지는 것을 피한다.
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except Exception:
        # TimeoutExpired 등 -> execSync throw -> [] 미러
        return []

    # execSync throw -> [] 를 더 충실히 미러: non-zero면 [].
    if result.returncode != 0:
        return []

    output = result.stdout or ""
    return [
        f
        for f in output.strip().split("\n")
        if f
        and (
            f.endswith(".ts")
            or f.endswith(".tsx")
            or f.endswith(".js")
            or f.endswith(".jsx")
        )
    ]


def check_console_log(files, cwd):
    if len(files) == 0:
        return []

    violations = []
    for file in files:
        try:
            result = subprocess.run(
                ["grep", "-n", "console\\.log", file],
                cwd=cwd,
                capture_output=True,
                # Node encoding:'utf-8' 미러. grep 출력에 non-ASCII(예: 한글 문자열
                # 리터럴)가 담겨도 로케일 strict 디코딩으로 크래시하지 않게 한다.
                encoding="utf-8",
                errors="replace",
                timeout=3,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            # spawnSync는 조용히 반환한다. 해당 파일 skip.
            continue
        if result.returncode == 0 and result.stdout.strip():
            violations.append({"file": file, "lines": result.stdout.strip()})

    return violations


def main():
    cwd = get_cwd()
    violations = check_console_log(get_modified_files(cwd), cwd)

    if len(violations) > 0:
        print(
            "[console.log 감사] 다음 파일에 console.log가 남아있습니다:",
            file=sys.stderr,
        )
        for v in violations:
            print("\n  📁 " + v["file"], file=sys.stderr)
            for line in v["lines"].split("\n"):
                print("    " + line, file=sys.stderr)
        print(
            "\n  커밋 전에 제거하거나 적절한 logger로 교체하세요.",
            file=sys.stderr,
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
