"""config 점 경로 plumbing + T6.4 byte-parity (레퍼런스 dev-context.test.js L367-656)."""

import json
from pathlib import Path

from _dc_helpers import read_ctx, run, run_raw


class TestConfigPath:
    def _write_min(self, ctx_path, obj):
        Path(ctx_path).write_text(json.dumps(obj), encoding="utf-8")

    # 1. 설정값 한 줄 출력 / 미설정 빈 출력
    def test_read_config_set_value_one_line(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.dev_impl.auto_start", "--value=true")
        assert run(ctx_path, "read", "--field=config.dev_impl.auto_start").stdout.strip() == "true"

    def test_read_config_unset_empty(self, ctx_path):
        assert run(ctx_path, "read", "--field=config.dev_impl.auto_start").stdout.strip() == ""

    # 2. config.* + --topic → non-zero
    def test_read_config_with_topic_non_zero(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=cp-test", "--spec=some/spec.md")
        err = run_raw(ctx_path, "read", "--topic=cp-test", "--field=config.dev_impl.auto_start")
        assert err.returncode != 0

    # 3. 누락 세그먼트 → 빈 출력
    def test_read_config_missing_config_key(self, ctx_path):
        self._write_min(ctx_path, {"current_topic": None, "topics": {}, "updatedAt": "2026-01-01T00:00:00.000Z"})
        assert run(ctx_path, "read", "--field=config.dev_impl.auto_start").stdout.strip() == ""

    def test_read_config_missing_namespace(self, ctx_path):
        self._write_min(ctx_path, {"current_topic": None, "topics": {}, "config": {}, "updatedAt": "2026-01-01T00:00:00.000Z"})
        assert run(ctx_path, "read", "--field=config.dev_impl.auto_start").stdout.strip() == ""

    def test_read_config_missing_leaf(self, ctx_path):
        self._write_min(ctx_path, {"current_topic": None, "topics": {}, "config": {"dev_impl": {}}, "updatedAt": "2026-01-01T00:00:00.000Z"})
        assert run(ctx_path, "read", "--field=config.dev_impl.auto_start").stdout.strip() == ""

    # 4-7. 타입 추론
    def test_set_config_true_boolean(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.dev_impl.auto_start", "--value=true")
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["dev_impl"]["auto_start"] is True

    def test_set_config_false_boolean(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.dev_impl.auto_start", "--value=false")
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["dev_impl"]["auto_start"] is False

    def test_set_config_integer(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.some.count", "--value=42")
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["some"]["count"] == 42
        assert isinstance(ctx["config"]["some"]["count"], int)

    def test_set_config_negative_integer(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.some.count", "--value=-7")
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["some"]["count"] == -7
        assert isinstance(ctx["config"]["some"]["count"], int)

    def test_set_config_string(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.some.label", "--value=foo")
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["some"]["label"] == "foo"
        assert isinstance(ctx["config"]["some"]["label"], str)

    # 8-9. auto-create + config 키 영속화
    def test_set_config_auto_create_intermediate(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.dev_impl.auto_start", "--value=true")
        ctx = read_ctx(ctx_path)
        assert isinstance(ctx["config"], dict)
        assert isinstance(ctx["config"]["dev_impl"], dict)
        assert ctx["config"]["dev_impl"]["auto_start"] is True

    def test_config_key_persists_after_topic_set_field(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=sch-test", "--spec=some/spec.md")
        run(ctx_path, "set-field", "--topic=sch-test", "--field=plan", "--value=.tack/local/active/sch-test/plan.md")
        ctx = read_ctx(ctx_path)
        assert "config" in ctx
        assert isinstance(ctx["config"], dict)

    def test_read_config_on_configless_file_empty(self, ctx_path):
        self._write_min(ctx_path, {"current_topic": None, "topics": {}, "updatedAt": "2026-01-01T00:00:00.000Z"})
        assert run(ctx_path, "read", "--field=config.dev_impl.auto_start").stdout.strip() == ""

    # 10-11. 깊이 거부
    def test_read_config_depth_3_non_zero(self, ctx_path):
        err = run_raw(ctx_path, "read", "--field=config.dev_impl.auto_start.extra")
        assert err.returncode != 0

    def test_set_config_depth_1_non_zero(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.dev_impl", "--value=true")
        assert err.returncode != 0

    def test_set_config_depth_3_non_zero(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.a.b.c", "--value=true")
        assert err.returncode != 0

    def test_set_config_bare_non_zero(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config", "--value=true")
        assert err.returncode != 0

    # 12. config.* + --topic (set-field)
    def test_set_config_with_topic_non_zero(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=cp-topic-test", "--spec=some/spec.md")
        err = run_raw(ctx_path, "set-field", "--topic=cp-topic-test", "--field=config.dev_impl.auto_start", "--value=true")
        assert err.returncode != 0

    # 13. 회귀: 토픽 필드 문자열 보존
    def test_topic_field_string_preserved_regression(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=reg-test", "--spec=some/spec.md")
        run(ctx_path, "set-field", "--topic=reg-test", "--field=plan", "--value=true")
        ctx = read_ctx(ctx_path)
        assert ctx["topics"]["reg-test"]["plan"] == "true"
        assert isinstance(ctx["topics"]["reg-test"]["plan"], str)

    # 예약 키 방어
    def test_set_config_proto_reserved(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.__proto__.polluted", "--value=yes")
        assert err.returncode != 0
        assert "예약된 키" in err.stderr

    def test_set_config_constructor_reserved(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.constructor.x", "--value=y")
        assert err.returncode != 0

    def test_set_config_prototype_key_reserved(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.dev_impl.prototype", "--value=y")
        assert err.returncode != 0

    def test_read_config_proto_reserved(self, ctx_path):
        err = run_raw(ctx_path, "read", "--field=config.__proto__.toString")
        assert err.returncode != 0

    # hasOwn 가드: 상속 속성이 own으로 읽히지 않음
    def test_read_config_tostring_empty(self, ctx_path):
        self._write_min(ctx_path, {"current_topic": None, "topics": {}, "updatedAt": "2026-01-01T00:00:00.000Z"})
        assert run(ctx_path, "read", "--field=config.toString.name").stdout.strip() == ""

    def test_read_config_hasownproperty_empty(self, ctx_path):
        self._write_min(ctx_path, {"current_topic": None, "topics": {}, "updatedAt": "2026-01-01T00:00:00.000Z"})
        assert run(ctx_path, "read", "--field=config.hasOwnProperty.name").stdout.strip() == ""

    def test_read_config_valueof_empty(self, ctx_path):
        self._write_min(ctx_path, {"current_topic": None, "topics": {}, "updatedAt": "2026-01-01T00:00:00.000Z"})
        assert run(ctx_path, "read", "--field=config.valueOf.name").stdout.strip() == ""

    def test_set_config_own_property_reads_back(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.dev_impl.auto_start", "--value=true")
        assert run(ctx_path, "read", "--field=config.dev_impl.auto_start").stdout.strip() == "true"

    # 14. JSON 배열
    def test_set_config_json_array(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", '--value=[".claude/",".tack/"]')
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["docs"]["sourceFilter"] == [".claude/", ".tack/"]
        assert isinstance(ctx["config"]["docs"]["sourceFilter"], list)

    def test_read_config_array_newline_joined(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", '--value=[".claude/",".tack/","CLAUDE.md"]')
        assert run(ctx_path, "read", "--field=config.docs.sourceFilter").stdout.strip() == ".claude/\n.tack/\nCLAUDE.md"

    def test_set_config_empty_array(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", "--value=[]")
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["docs"]["sourceFilter"] == []
        assert isinstance(ctx["config"]["docs"]["sourceFilter"], list)

    def test_read_config_empty_array_empty_output(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", "--value=[]")
        assert run(ctx_path, "read", "--field=config.docs.sourceFilter").stdout.strip() == ""

    def test_set_config_non_string_element_int(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.docs.sourceFilter", "--value=[1,2]")
        assert err.returncode != 0
        assert "문자열 원소만 허용" in err.stderr

    def test_set_config_non_string_element_null(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.docs.sourceFilter", "--value=[null]")
        assert err.returncode != 0
        assert "문자열 원소만 허용" in err.stderr

    def test_set_config_unclosed_bracket_scalar(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", "--value=[invalid")
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["docs"]["sourceFilter"] == "[invalid"
        assert isinstance(ctx["config"]["docs"]["sourceFilter"], str)

    def test_set_config_regex_scalar_not_array(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.git.branchPattern", "--value=[A-Z].*")
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["git"]["branchPattern"] == "[A-Z].*"
        assert isinstance(ctx["config"]["git"]["branchPattern"], str)

    def test_set_config_newline_array_element(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.docs.sourceFilter", '--value=["src/\\nlib/"]')
        assert err.returncode != 0
        assert "줄바꿈" in err.stderr

    def test_empty_array_round_trip_zero_prefixes(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", "--value=[]")
        out = run(ctx_path, "read", "--field=config.docs.sourceFilter").stdout.strip()
        prefixes = [p for p in out.split("\n") if p]
        assert len(prefixes) == 0

    def test_topic_field_no_array_inference_regression(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=arr-reg", "--spec=some/spec.md")
        run(ctx_path, "set-field", "--topic=arr-reg", "--field=plan", '--value=["x"]')
        ctx = read_ctx(ctx_path)
        assert ctx["topics"]["arr-reg"]["plan"] == '["x"]'
        assert isinstance(ctx["topics"]["arr-reg"]["plan"], str)

    # T6.4 — non-stripped stdout + non-ASCII byte-parity
    def test_array_raw_stdout_non_stripped(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", '--value=["a","b","c"]')
        assert run(ctx_path, "read", "--field=config.docs.sourceFilter").stdout == "a\nb\nc\n"

    def test_empty_array_raw_stdout_is_newline_only(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", "--value=[]")
        assert run(ctx_path, "read", "--field=config.docs.sourceFilter").stdout == "\n"

    def test_non_ascii_config_value_byte_parity(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.some.label", "--value=한글")
        raw = Path(ctx_path).read_text(encoding="utf-8")
        assert "한글" in raw
        assert "\\u" not in raw  # ensure_ascii=False → escape 미포함

    def test_config_boolean_read_lowercase(self, ctx_path):
        # JS String(true)="true" — Python str(True)="True" 트랩 방어
        run(ctx_path, "set-field", "--field=config.dev_impl.auto_start", "--value=true")
        assert run(ctx_path, "read", "--field=config.dev_impl.auto_start").stdout == "true\n"

    # 리뷰 후속: bare --value 플래그 (값 없음 → parse_args True) — config 경로 crash 방어.
    # JS는 boolean true를 그대로 저장(exit 0). Python coerce_config_value는 비-str를
    # 타입 추론 없이 반환해야 한다 (re.fullmatch(True)의 TypeError traceback 회피).
    def test_config_bare_value_flag_stores_true(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.dev_impl.auto_start", "--value")
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["dev_impl"]["auto_start"] is True

    # 리뷰 후속: 병적으로 깊게 중첩된 대괄호는 json.loads가 RecursionError를 낸다 —
    # ValueError만 잡으면 uncaught traceback. clean die(exit 1)로 처리되는지 검증.
    def test_config_pathological_nested_brackets_clean_die(self, ctx_path):
        # 배열 정규식('[' 시작 + ']' 끝)에 매치되어야 json.loads가 호출된다.
        # 깊게 중첩된 배열은 RecursionError → clean die로 처리되어야 한다.
        value = "[" * 60000 + "]" * 60000
        err = run_raw(ctx_path, "set-field", "--field=config.docs.sourceFilter",
                      "--value=" + value)
        assert err.returncode != 0
        assert "Traceback (most recent call last)" not in err.stderr
