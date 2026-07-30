"""dev_context.py 통합 테스트 공유 헬퍼.

test_*.py 모듈들이 import해서 쓰는 subprocess 실행 래퍼·상수. 파일명이 test_* 패턴이
아니므로 pytest 수집 대상에서 제외된다. 실제 repo dev-context.json을 건드리지 않도록
DEV_CONTEXT_PATH env를 주입하고 subprocess로 `[sys.executable, SCRIPT, ...]`를 호출한다
(레퍼런스 테스트의 `['node', SCRIPT, ...]`와 대칭).

공유 config 층(`.tack/config.json`)도 같은 방식으로 격리한다 — DEV_CONFIG_PATH를 **항상**
주입하고 값은 ctx_path와 같은 tmp 디렉토리 안에 둔다. 주입하지 않으면 dev_context.py의
2-hop 기본 유도가 `dirname(dirname(tmp_path/dev-context.json))` = pytest basetemp(세션 공유
디렉토리)로 해석돼 테스트 간 shared 값이 새어 나간다.
"""

import json
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(SCRIPT_DIR, "dev_context.py")
NODE_SCRIPT = os.path.join(SCRIPT_DIR, "dev-context.js")
# 실사용 config 스키마. 경로를 재유도하지 않고 프로덕션 상수를 그대로 쓴다 — 계약 파일이
# 옮겨지면 프로덕션과 함께 움직여야 vocabulary parity 가드가 엉뚱한 파일을 검증하지 않는다.
# dev_context는 __main__ 가드가 있어 import 부작용이 없다.
from dev_context import DEFAULT_CONFIG_SCHEMA_PATH as SCHEMA_PATH  # noqa: E402
# 공유 config 봉투의 포맷 버전. dev_context._empty_shared_config()와 같은 값을 쓴다.
FILE_FORMAT = "1.0"
# ISO 타임스탬프(밀리초+Z) 정규화 — createdAt/updatedAt만 런타임마다 달라진다.
_ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z")


def shared_config_path(ctx_path):
    """ctx_path와 같은 tmp 디렉토리 안의 공유 config 경로 (테스트별 격리 기본값).

    프로덕션 resolve_shared_config_path()는 2-hop이지만 여기는 1-hop이다 — ctx_path
    픽스처가 tmp_path 직속이라 2-hop은 pytest basetemp(세션 공유 디렉토리)로 나가
    격리가 깨진다. 프로덕션 유도와 "맞추는" 수정은 그 누출을 되살린다.
    """
    return os.path.join(os.path.dirname(os.path.abspath(ctx_path)), "config.json")


def run_raw(ctx_path, *args, schema_path=None):
    """성공/실패 무관하게 CompletedProcess 반환 (실패 케이스용).

    `schema_path`를 주면 DEV_CONFIG_SCHEMA_PATH로 주입한다 — `some.*` 같은 합성
    네임스페이스를 쓰는 plumbing 테스트가 픽스처 스키마로 실행되기 위한 seam이다.
    미지정이면 env에서 제거해 **실사용 스키마**로 해석되게 한다 (상속된 env 누출 차단).
    """
    env = {
        **os.environ,
        "DEV_CONTEXT_PATH": ctx_path,
        "DEV_CONFIG_PATH": shared_config_path(ctx_path),
    }
    env.pop("DEV_CONFIG_SCHEMA_PATH", None)
    if schema_path is not None:
        env["DEV_CONFIG_SCHEMA_PATH"] = schema_path
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )


def run(ctx_path, *args, schema_path=None):
    """서브커맨드를 실행하고 성공(exit 0)을 단언한 뒤 CompletedProcess 반환."""
    result = run_raw(ctx_path, *args, schema_path=schema_path)
    assert result.returncode == 0, (
        f"expected success, got exit {result.returncode}: {result.stderr}"
    )
    return result


def read_json(path):
    """JSON 파일을 그대로 읽어 dict로 반환한다 (층 무관 raw 리더).

    dev_context.load_shared_config는 부재를 `(True, 빈 봉투)`로 접으므로 목적지 단언에
    쓸 수 없다 — "파일이 없다"와 "빈 config가 들어 있다"가 구분되지 않는다.
    """
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# 층별 이름은 호출 지점의 의도를 드러내므로 유지하되, 본문은 하나만 둔다 — E4가 층을
# 하나 더 넣어도 같은 본문을 세 번째로 복제하지 않게 한다.
read_ctx = read_json
read_shared_config_file = read_json


def shared_value(ctx_path, ns, key):
    """shared 층에 저장된 leaf 값 (목적지 단언용 축약).

    `read_shared_config_file(shared_config_path(ctx_path))["config"][ns][key]` 4단 첨자를
    한 호출로 접는다 — 봉투 모양이 바뀌어도 고칠 지점이 여기 한 곳이다.
    """
    return read_shared_config_file(shared_config_path(ctx_path))["config"][ns][key]


def write_shared_config(path, config):
    """공유 config 픽스처를 직접 기록한다 — 사전 상태 구성용이라 CLI를 거치지 않는다."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"file_format": FILE_FORMAT, "config": config}, f, ensure_ascii=False)


def write_ctx(ctx_path, config):
    """local dev-context.json 픽스처를 직접 기록한다.

    CLI set-field 경유로는 JSON null을 만들 수 없다 — config 분기는 coerce_config_value만
    거치므로 `--value=null`이 문자열 "null"로 저장된다.
    """
    with open(ctx_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "current_topic": None,
                "topics": {},
                "config": config,
                "updatedAt": "2026-01-01T00:00:00.000Z",
            },
            f,
            ensure_ascii=False,
        )
