#!/usr/bin/env python3
"""SessionStart 훅: dev-context.json을 로드하고 이전 작업 컨텍스트를 복원한다.
codex 상태 감지는 .claude/scripts/codex/detect-and-cache.js에 위임한다.
"""

import json
import os
import subprocess
import sys


def get_cwd():
    return os.environ.get("PWD") or os.getcwd()


def render_phase(topic_data):
    # JS 템플릿 리터럴 미러: 키 부재 -> "undefined", 값이 null -> "null".
    if "phase" not in topic_data:
        return "undefined"
    value = topic_data["phase"]
    return "null" if value is None else value


def restore_context(context_path):
    if not os.path.exists(context_path):
        return
    try:
        with open(context_path, "r", encoding="utf-8") as f:
            context = json.load(f)
        topic = context.get("current_topic")
        if topic:
            topic_data = (context.get("topics") or {}).get(topic)
            # JS `if (topicData)` 미러: 객체는 빈 객체({})도 truthy이므로 키 부재
            # (None)만 skip한다. Python `if topic_data:`는 {}를 falsy로 처리해
            # 발산하므로 `is not None`으로 판정한다.
            if topic_data is not None:
                # 이전 컨텍스트 출력 (Claude Code가 시스템 메시지로 인식)
                print(f"[컨텍스트 복원] 주제: {topic} | phase: {render_phase(topic_data)}")

                if topic_data.get("currentStory"):
                    print(f"[컨텍스트 복원] 다음 Story: {topic_data['currentStory']}")
                    print("  → /dev:impl 로 계속하세요.")

                if topic_data.get("plan"):
                    print(f"[컨텍스트 복원] 계획 파일: {topic_data['plan']}")
    except Exception:
        # 파일 파싱 오류 무시
        pass


def run_detect(detect_script):
    # codex 상태 감지 — TTL(1h) 내 캐시가 유효하면 스킵
    if os.path.exists(detect_script):
        try:
            subprocess.run(
                ["node", detect_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            # 무음 실패 (바이너리 부재 포함)
            pass


def main():
    cwd = get_cwd()
    context_path = os.path.join(cwd, ".tack/local/dev-context.json")
    detect_script = os.path.join(cwd, ".claude/scripts/codex/detect-and-cache.js")

    restore_context(context_path)
    run_detect(detect_script)

    sys.exit(0)


if __name__ == "__main__":
    main()
