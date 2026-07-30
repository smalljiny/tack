"""config 스키마 순수 로더·검증 모듈.

`.tack/contracts/config-schema.json`이 선언하는 네임스페이스·키·타입·layer를 읽어 조회와
판정만 수행한다. 프로세스 종료(die)·CLI 배선·쓰기 결정은 dev_context.py가 소유한다 —
state_machine.py와 같은 seam 분리다.

파일 읽기는 이 모듈에 두되, 실패는 SchemaError로 올려보내고 정책(fail-closed 여부·메시지
문구)은 호출자가 정한다.
"""

import json
import os

# 스키마 `type` 선언값 → Python 런타임 타입.
# 이 매핑의 키 집합은 스키마 최상위 `type_values`와 일치해야 한다. 검증기 어휘가 스키마와
# 독립적으로 갈라지면 "스키마가 기계 판독 SSOT"라는 선언이 조용히 거짓이 되므로,
# test_config_schema.py가 양쪽 집합의 동일성을 단언한다.
TYPE_MAP = {
    "string": str,
    "boolean": bool,
    "integer": int,
    "array": list,
}

# 스키마 `layer` 선언값 집합 — layer_of가 돌려줄 수 있는 값의 전부다.
# TYPE_MAP과 같은 이유로 스키마 `layer_values`와의 동일성을 테스트가 단언한다.
LAYERS = frozenset(["shared", "local", "cache"])


class SchemaError(Exception):
    """스키마 파일을 읽거나 해석할 수 없는 상태. 호출자가 정책(die 여부)을 결정한다."""


def load_schema(path):
    """스키마 JSON을 읽어 dict로 반환. 부재·손상·형식 불일치는 SchemaError.

    메시지에 해석된 경로를 담는다 — 호출자가 그대로 노출하면 픽스처 경로 오타가
    "검증이 없다"가 아니라 즉시 진단 가능한 실패로 읽힌다.
    """
    if not os.path.exists(path):
        raise SchemaError(f"config 스키마 파일이 없습니다: {path}")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError, RecursionError) as e:
        raise SchemaError(f"config 스키마 파일을 읽을 수 없습니다 ({path}): {e}")
    if not isinstance(data, dict) or not isinstance(data.get("namespaces"), dict):
        raise SchemaError(f"config 스키마 형식이 올바르지 않습니다 ({path}).")
    return data


def namespaces(schema):
    """선언된 네임스페이스 이름 목록 (선언 순서 유지)."""
    return list(schema["namespaces"].keys())


def keys_of(schema, ns):
    """네임스페이스가 선언한 키 목록. 미선언 네임스페이스는 빈 목록."""
    ns_entry = schema["namespaces"].get(ns)
    return list(ns_entry.keys()) if isinstance(ns_entry, dict) else []


def lookup(schema, ns, key):
    """(ns, key) 선언 엔트리를 반환. 미선언이면 None.

    dict.get은 상속 속성을 보지 않으므로 예약 키(`__proto__`·`constructor`·`prototype`)도
    자연히 미선언으로 떨어진다. 경로 단계의 예약 키 차단은 parse_config_path가 앞서 수행한다.
    """
    ns_entry = schema["namespaces"].get(ns)
    if not isinstance(ns_entry, dict):
        return None
    entry = ns_entry.get(key)
    return entry if isinstance(entry, dict) else None


def check_type(declared_type, value):
    """선언 타입과 런타임 값의 일치 여부. 미지원 선언 타입은 False(fail-closed)."""
    expected = TYPE_MAP.get(declared_type)
    if expected is None:
        return False
    if expected is bool:
        return isinstance(value, bool)
    if expected is int:
        # Python bool은 int의 서브클래스다 — 명시 배제가 없으면 True가 integer로 통과한다.
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, expected)


def type_name(value):
    """런타임 값의 타입을 스키마 어휘로 되돌린다 (오류 메시지용).

    bool 판정이 int보다 먼저다 — 순서를 바꾸면 True가 'integer'로 보고된다.
    스키마 어휘에 대응이 없으면 Python 타입 이름을 그대로 쓴다.
    """
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return type(value).__name__


def suggest(name, candidates):
    """오타 근접 후보 최대 3개. 외부 의존성 없이 stdlib difflib만 쓴다.

    근접 후보가 없으면 빈 목록이다 — 호출자는 이때 전체 후보 나열로 폴백한다
    (예: 'bogus'는 어느 네임스페이스와도 cutoff 0.6에 못 미친다).
    """
    # difflib는 오타 후보 제시(실패 경로) 전용이라 지연 import한다 — module-level import는
    # 성공 경로를 포함한 모든 서브커맨드가 약 310µs를 무조건 지불하게 만든다.
    import difflib

    return difflib.get_close_matches(name, list(candidates), n=3, cutoff=0.6)


def layer_of(schema, ns, key):
    """선언 layer(shared|local|cache). 미선언 키·미지원 layer 값이면 None.

    Story 4(쓰기 라우팅)가 소비하는 seam이다 — 키·타입 검증 경로는 호출하지 않는다.
    """
    entry = lookup(schema, ns, key)
    if entry is None:
        return None
    layer = entry.get("layer")
    return layer if layer in LAYERS else None
