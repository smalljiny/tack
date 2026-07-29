"""config_schema.py 순수 모듈 단위 테스트 (T3.1·T3.8).

subprocess를 거치지 않고 모듈을 직접 import한다 — 데이터·판정만 소유하는 순수 모듈이므로
I/O 격리가 필요 없다(state_machine.py 테스트와 같은 형태).

drift 방지 단언(TestSchemaVocabularyParity)은 **실제** 스키마 파일을 읽는다. 검증기 어휘
(TYPE_MAP·LAYERS)가 스키마 선언(type_values·layer_values)과 독립적으로 갈라지면, 스키마가
기계 판독 SSOT라는 선언이 조용히 거짓이 된다.
"""

import json

import pytest

import config_schema
from _dc_helpers import SCHEMA_PATH


@pytest.fixture(scope="module")
def real_schema():
    return config_schema.load_schema(SCHEMA_PATH)


class TestLoadSchema:
    def test_loads_real_schema(self, real_schema):
        assert isinstance(real_schema["namespaces"], dict)
        assert len(real_schema["namespaces"]) == 10

    def test_missing_file_raises(self, tmp_path):
        missing = str(tmp_path / "nope.json")
        with pytest.raises(config_schema.SchemaError) as exc:
            config_schema.load_schema(missing)
        # 해석된 경로가 메시지에 있어야 픽스처 경로 오타를 즉시 진단할 수 있다.
        assert missing in str(exc.value)

    def test_corrupt_json_raises(self, tmp_path):
        path = tmp_path / "broken.json"
        path.write_text("{not json", encoding="utf-8")
        with pytest.raises(config_schema.SchemaError):
            config_schema.load_schema(str(path))

    def test_non_dict_top_level_raises(self, tmp_path):
        path = tmp_path / "list.json"
        path.write_text("[]", encoding="utf-8")
        with pytest.raises(config_schema.SchemaError):
            config_schema.load_schema(str(path))

    def test_missing_namespaces_raises(self, tmp_path):
        path = tmp_path / "nons.json"
        path.write_text(json.dumps({"file_format": "1.0"}), encoding="utf-8")
        with pytest.raises(config_schema.SchemaError):
            config_schema.load_schema(str(path))


class TestLookup:
    def test_known_key_returns_entry(self, real_schema):
        entry = config_schema.lookup(real_schema, "dev_impl", "auto_commit")
        assert entry["type"] == "boolean"

    def test_unknown_namespace_returns_none(self, real_schema):
        assert config_schema.lookup(real_schema, "bogus", "key") is None

    def test_unknown_key_returns_none(self, real_schema):
        assert config_schema.lookup(real_schema, "dev_impl", "auto_comit") is None

    def test_reserved_segment_returns_none(self, real_schema):
        # dict.get은 상속 속성을 보지 않는다 — 예약 키는 자연히 미선언이다.
        assert config_schema.lookup(real_schema, "__proto__", "polluted") is None
        assert config_schema.lookup(real_schema, "dev_impl", "constructor") is None

    def test_namespaces_lists_declaration_order(self, real_schema):
        assert config_schema.namespaces(real_schema)[0] == "git"
        assert "risk" in config_schema.namespaces(real_schema)

    def test_keys_of_known_namespace(self, real_schema):
        assert "auto_commit" in config_schema.keys_of(real_schema, "dev_impl")

    def test_keys_of_unknown_namespace_is_empty(self, real_schema):
        assert config_schema.keys_of(real_schema, "bogus") == []


class TestCheckType:
    def test_string_accepts_str(self):
        assert config_schema.check_type("string", "origin") is True

    def test_string_accepts_empty_str(self):
        # 빈 문자열은 유효 입력이다 (--value= 형태의 전제).
        assert config_schema.check_type("string", "") is True

    def test_string_rejects_bool(self):
        assert config_schema.check_type("string", True) is False
        assert config_schema.check_type("string", False) is False

    def test_string_rejects_int(self):
        # 순수 숫자 문자열은 coerce_config_value가 int로 추론한다 — string 키에서 거부된다.
        assert config_schema.check_type("string", 2026) is False

    def test_boolean_accepts_bool(self):
        assert config_schema.check_type("boolean", True) is True
        assert config_schema.check_type("boolean", False) is True

    def test_boolean_rejects_str(self):
        assert config_schema.check_type("boolean", "maybe") is False

    def test_boolean_rejects_int(self):
        assert config_schema.check_type("boolean", 1) is False

    def test_integer_accepts_int(self):
        assert config_schema.check_type("integer", 42) is True
        assert config_schema.check_type("integer", -7) is True

    def test_integer_rejects_bool(self):
        # Python bool은 int의 서브클래스다 — 명시 배제가 없으면 True가 통과한다.
        assert config_schema.check_type("integer", True) is False
        assert config_schema.check_type("integer", False) is False

    def test_array_accepts_list(self):
        assert config_schema.check_type("array", []) is True
        assert config_schema.check_type("array", ["a"]) is True

    def test_array_rejects_str(self):
        assert config_schema.check_type("array", "[invalid") is False

    def test_unknown_declared_type_is_false(self):
        assert config_schema.check_type("object", {}) is False
        assert config_schema.check_type(None, "x") is False


class TestTypeName:
    def test_bool_before_int(self):
        # bool 판정이 int보다 먼저여야 True가 'integer'로 보고되지 않는다.
        assert config_schema.type_name(True) == "boolean"

    def test_scalar_names(self):
        assert config_schema.type_name(3) == "integer"
        assert config_schema.type_name("x") == "string"
        assert config_schema.type_name([]) == "array"

    def test_unmapped_falls_back_to_python_name(self):
        assert config_schema.type_name({}) == "dict"


class TestSuggest:
    def test_close_typo_is_suggested(self, real_schema):
        got = config_schema.suggest("auto_comit", config_schema.keys_of(real_schema, "dev_impl"))
        assert "auto_commit" in got

    def test_distant_name_returns_empty(self, real_schema):
        # 'bogus'는 10개 네임스페이스 어느 것과도 cutoff 0.6에 못 미친다 —
        # 호출자는 이 빈 결과에서 전체 후보 나열로 폴백해야 한다.
        assert config_schema.suggest("bogus", config_schema.namespaces(real_schema)) == []


class TestLayerOf:
    """Story 4(쓰기 라우팅)가 소비할 seam. Story 3의 검증 경로는 호출하지 않는다."""

    def test_shared_key(self, real_schema):
        assert config_schema.layer_of(real_schema, "git", "pushRemote") == "shared"

    def test_local_key(self, real_schema):
        assert config_schema.layer_of(real_schema, "dev_impl", "auto_commit") == "local"

    def test_cache_key(self, real_schema):
        assert config_schema.layer_of(real_schema, "codex", "available") == "cache"

    def test_unknown_key_returns_none(self, real_schema):
        assert config_schema.layer_of(real_schema, "bogus", "key") is None

    def test_unsupported_layer_value_returns_none(self, tmp_path):
        path = tmp_path / "s.json"
        path.write_text(
            json.dumps({"namespaces": {"n": {"k": {"type": "string", "layer": "cloud"}}}}),
            encoding="utf-8",
        )
        schema = config_schema.load_schema(str(path))
        assert config_schema.layer_of(schema, "n", "k") is None


class TestSchemaVocabularyParity:
    """검증기 어휘 ↔ 스키마 선언 어휘 drift 방지 (code-reviewer 이월 요구)."""

    def test_type_map_matches_schema_type_values(self, real_schema):
        assert set(config_schema.TYPE_MAP) == set(real_schema["type_values"])

    def test_layers_matches_schema_layer_values(self, real_schema):
        assert set(config_schema.LAYERS) == set(real_schema["layer_values"])

    def test_every_declared_type_is_checkable(self, real_schema):
        for ns in config_schema.namespaces(real_schema):
            for key in config_schema.keys_of(real_schema, ns):
                entry = config_schema.lookup(real_schema, ns, key)
                assert entry["type"] in config_schema.TYPE_MAP, f"{ns}.{key}"

    def test_every_declared_layer_is_resolvable(self, real_schema):
        for ns in config_schema.namespaces(real_schema):
            for key in config_schema.keys_of(real_schema, ns):
                assert config_schema.layer_of(real_schema, ns, key) is not None, f"{ns}.{key}"

    def test_every_default_matches_its_declared_type(self, real_schema):
        for ns in config_schema.namespaces(real_schema):
            for key in config_schema.keys_of(real_schema, ns):
                entry = config_schema.lookup(real_schema, ns, key)
                assert config_schema.check_type(entry["type"], entry["default"]), f"{ns}.{key}"
