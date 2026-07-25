#!/usr/bin/env python3
"""PreToolUse 훅: git push 명령어 전 변경 사항 검토를 안내한다.
push를 막지 않고 정보만 제공.
"""

import sys


def is_git_push(cmd):
    return cmd.strip().startswith("git push")


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if not is_git_push(command):
        sys.exit(0)

    # push 전 체크리스트 출력
    print("[git push 전 확인 사항]")
    print("  □ /dev:review 를 완료했는가?")
    print("  □ /dev:verify 의 모든 게이트를 통과했는가?")
    print("  □ console.log가 남아있지 않은가?")
    print("  □ 시크릿이 커밋에 포함되지 않았는가?")
    print("")

    # exit 0: push를 막지 않음 (정보 제공만)
    sys.exit(0)


if __name__ == "__main__":
    main()
