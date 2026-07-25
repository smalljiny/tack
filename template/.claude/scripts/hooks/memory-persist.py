#!/usr/bin/env python3
"""Stop 훅: 세션 종료 시 현재 상태를 dev-context.json에 저장한다.
updatedAt 타임스탬프를 갱신해 세션 이력을 유지한다.
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


def main():
    cwd = get_cwd()
    context_path = os.path.join(cwd, ".tack/local/dev-context.json")

    if not os.path.exists(context_path):
        sys.exit(0)

    try:
        with open(context_path, "r", encoding="utf-8") as f:
            context = json.load(f)
        topic = context.get("current_topic")

        if not topic or topic not in (context.get("topics") or {}):
            sys.exit(0)

        # updatedAt 갱신
        context["topics"][topic]["updatedAt"] = iso_ts()

        with open(context_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(context, indent=2, ensure_ascii=False) + "\n")
    except Exception:
        # 실패 무시 (비주요 기능)
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
