#!/usr/bin/env python3
"""PreToolUse 훅: 도구 호출 횟수를 추적하고 전략적 compaction 시점을 제안한다.
Exit 0으로 종료 — 제안만 할 뿐 작업을 막지 않는다.
"""

import os
import sys
import tempfile

REMIND_EVERY = 25


def parse_int_prefix(s):
    """JS ``parseInt(s, 10)``의 base-10 의미를 재현한다.

    앞쪽 공백을 건너뛰고, 선택적 부호(+/-) 뒤의 연속된 ASCII 숫자를 파싱하며,
    첫 비숫자 문자에서 멈춘다. 유효한 숫자가 없으면 NaN에 해당하는 ``None``을
    반환한다.
    """
    if s is None:
        return None
    i = 0
    n = len(s)
    while i < n and s[i] in " \t\n\r\f\v":
        i += 1
    sign = 1
    if i < n and s[i] in "+-":
        if s[i] == "-":
            sign = -1
        i += 1
    start = i
    while i < n and s[i] in "0123456789":
        i += 1
    if i == start:
        return None
    return sign * int(s[start:i])


def get_threshold():
    # JS: parseInt(process.env.COMPACT_THRESHOLD || '50', 10). NaN -> None.
    raw = os.environ.get("COMPACT_THRESHOLD") or "50"
    return parse_int_prefix(raw)


def get_session_id():
    # CLAUDE_SESSION_ID 환경변수 우선, 없으면 PPID 환경변수, 그다음 'default'.
    return (
        os.environ.get("CLAUDE_SESSION_ID")
        or os.environ.get("PPID")
        or "default"
    )


def get_counter_file():
    return os.path.join(
        tempfile.gettempdir(), f"harness-tool-count-{get_session_id()}"
    )


def read_count(file):
    # JS: parseInt(readFileSync(...).trim(), 10) || 0. 손상/부재 -> 0.
    try:
        with open(file, "r", encoding="utf-8") as f:
            return parse_int_prefix(f.read().strip()) or 0
    except Exception:
        # JS catch-all 미러: 비UTF-8 바이트의 UnicodeDecodeError 포함 모든 예외에서 0.
        return 0


def main():
    threshold = get_threshold()
    counter_file = get_counter_file()
    count = read_count(counter_file) + 1

    try:
        with open(counter_file, "w", encoding="utf-8") as f:
            f.write(str(count))
    except OSError:
        sys.exit(0)  # 카운터 저장 실패는 무시

    if threshold is not None and count == threshold:
        sys.stderr.write(
            f"[StrategicCompact] 도구 호출 {count}회 — 다음 Task 시작 전 /compact 고려\n"
        )
    elif (
        threshold is not None
        and count > threshold
        and (count - threshold) % REMIND_EVERY == 0
    ):
        sys.stderr.write(
            f"[StrategicCompact] 도구 호출 {count}회 — 컨텍스트가 오래됐다면 /compact 좋은 시점\n"
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
