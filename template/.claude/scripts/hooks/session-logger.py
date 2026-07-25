#!/usr/bin/env python3
"""PostToolUse 훅 (비동기): 도구 사용 패턴을 세션 로그에 기록한다.
sessions/<date>.jsonl 형식으로 저장.
"""

import json
import os
import sys
from datetime import datetime, timezone


def get_cwd():
    return os.environ.get("PWD") or os.getcwd()


def iso_ts():
    # JS new Date().toISOString(): YYYY-MM-DDTHH:MM:SS.mmmZ (밀리초 정밀도).
    dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def get_today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")  # YYYY-MM-DD (UTC)


def get_current_topic(cwd):
    context_path = os.path.join(cwd, ".tack/local/dev-context.json")
    if not os.path.exists(context_path):
        return None
    try:
        with open(context_path, "r", encoding="utf-8") as f:
            context = json.load(f)
        return context.get("current_topic") or None
    except Exception:
        # JS catch-all 미러: non-dict JSON(list/null/number)의 .get AttributeError
        # 포함 모든 예외에서 null 반환.
        return None


def _append_line(log_file, line):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line)


def main():
    cwd = get_cwd()
    # JS: process.argv[2] || 'unknown' — 빈 문자열도 대체값으로 간다.
    tool_name = (sys.argv[1] if len(sys.argv) > 1 else "") or "unknown"
    file_path = sys.argv[2] if len(sys.argv) > 2 else ""

    sessions_dir = os.path.join(cwd, ".claude/sessions")
    if not os.path.exists(sessions_dir):
        try:
            os.makedirs(sessions_dir, exist_ok=True)
        except OSError:
            sys.exit(0)

    log_file = os.path.join(sessions_dir, f"{get_today()}.jsonl")
    topic = get_current_topic(cwd)

    # 삽입 순서: ts, tool, (file 있으면), (topic 있으면).
    entry = {"ts": iso_ts(), "tool": tool_name}
    if file_path:
        entry["file"] = file_path
    if topic:
        entry["topic"] = topic

    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n"
    try:
        _append_line(log_file, line)
    except Exception:
        pass  # 로그 실패는 무시 (비주요 기능)

    sys.exit(0)


if __name__ == "__main__":
    main()
