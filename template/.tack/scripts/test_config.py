"""config 점 경로 plumbing + T6.4 byte-parity (레퍼런스 dev-context.test.js L367-656)."""

import json
from pathlib import Path

import pytest

import config_schema
import dev_context
from _dc_helpers import SCHEMA_PATH, read_ctx, run, run_raw, shared_value


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

    # `some.*`는 실사용 인벤토리에 없는 합성 네임스페이스다. 실사용 스키마에 `integer`
    # 타입 키가 하나도 없어 실제 키로 옮기면 `^-?[0-9]+$ → int` 규칙의 커버리지가 사라지므로,
    # 픽스처 스키마(conftest.FIXTURE_SCHEMA)로 실행한다.
    def test_set_config_integer(self, ctx_path, fixture_schema_path):
        run(ctx_path, "set-field", "--field=config.some.count", "--value=42",
            schema_path=fixture_schema_path)
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["some"]["count"] == 42
        assert isinstance(ctx["config"]["some"]["count"], int)

    def test_set_config_negative_integer(self, ctx_path, fixture_schema_path):
        run(ctx_path, "set-field", "--field=config.some.count", "--value=-7",
            schema_path=fixture_schema_path)
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["some"]["count"] == -7
        assert isinstance(ctx["config"]["some"]["count"], int)

    def test_set_config_string(self, ctx_path, fixture_schema_path):
        run(ctx_path, "set-field", "--field=config.some.label", "--value=foo",
            schema_path=fixture_schema_path)
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
        assert "config.<namespace>.<key>" in err.stderr
        # 깊이 검사가 스키마 조회보다 먼저다 — 스키마 메시지가 섞이면 순서가 뒤집힌 것이다.
        assert "네임스페이스" not in err.stderr

    def test_set_config_bare_non_zero(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config", "--value=true")
        assert err.returncode != 0
        assert "config.<namespace>.<key>" in err.stderr
        assert "네임스페이스" not in err.stderr

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
        # 예약 키 검사가 스키마 조회보다 먼저다.
        assert "네임스페이스" not in err.stderr

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
    # `docs.sourceFilter`는 shared layer라 쓰기 라우팅이 공유 파일로 보낸다. 단언 의도는
    # "타입 추론이 list를 만든다"이므로 목적지만 바로잡고 호출 형태(플래그 없음)는 실제
    # 호출자와 같게 유지한다 — `--layer=local`을 붙이면 기본 라우팅을 검증에서 잃는다.
    def test_set_config_json_array(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", '--value=[".claude/",".tack/"]')
        stored = shared_value(ctx_path, "docs", "sourceFilter")
        assert stored == [".claude/", ".tack/"]
        assert isinstance(stored, list)

    def test_read_config_array_newline_joined(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", '--value=[".claude/",".tack/","CLAUDE.md"]')
        assert run(ctx_path, "read", "--field=config.docs.sourceFilter").stdout.strip() == ".claude/\n.tack/\nCLAUDE.md"

    def test_set_config_empty_array(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", "--value=[]")
        stored = shared_value(ctx_path, "docs", "sourceFilter")
        assert stored == []
        assert isinstance(stored, list)

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

    def test_set_config_unclosed_bracket_scalar(self, ctx_path, fixture_schema_path):
        # 닫히지 않은 대괄호는 배열 정규식에 미매치해 문자열로 보존된다. 단언 의도가
        # "문자열 보존"이므로 문자열 타입 키에서 검증한다 — array 타입 키에 두면 스키마
        # 타입 검사가 먼저 거부해 의도가 사라진다.
        # 실사용 인벤토리의 string 키는 전부 shared·cache layer라 Story 4의 쓰기 라우팅이
        # 목적지를 옮긴다. local layer의 string 키인 픽스처 `some.label`을 쓰면 이 단언이
        # 라우팅 도입 후에도 dev-context.json을 계속 가리킨다.
        run(ctx_path, "set-field", "--field=config.some.label", "--value=[invalid",
            schema_path=fixture_schema_path)
        ctx = read_ctx(ctx_path)
        assert ctx["config"]["some"]["label"] == "[invalid"
        assert isinstance(ctx["config"]["some"]["label"], str)

    def test_set_config_regex_scalar_not_array(self, ctx_path):
        # `git.branchPattern`도 shared layer다 — 위 배열 케이스와 같은 이유로 공유 파일에서 읽는다.
        run(ctx_path, "set-field", "--field=config.git.branchPattern", "--value=[A-Z].*")
        stored = shared_value(ctx_path, "git", "branchPattern")
        assert stored == "[A-Z].*"
        assert isinstance(stored, str)

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

    def test_non_ascii_config_value_byte_parity(self, ctx_path, fixture_schema_path):
        run(ctx_path, "set-field", "--field=config.some.label", "--value=한글",
            schema_path=fixture_schema_path)
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


class TestSetFieldSchemaValidation:
    """set-field config 경로의 스키마 검증 (G3 — 키·타입). read는 관대성을 유지한다."""

    # --- 알 수 없는 네임스페이스·키 ---
    def test_unknown_namespace_non_zero_with_candidates(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.bogus.key", "--value=x")
        assert err.returncode != 0
        # 'bogus'는 어느 네임스페이스와도 근접하지 않는다(difflib cutoff 0.6 미달) —
        # 근접 후보가 없으면 전체 후보를 나열해야 사용자가 다음 행동을 안다.
        assert "git" in err.stderr
        assert "dev_impl" in err.stderr

    def test_unknown_namespace_suggests_close_match(self, ctx_path):
        # 오타 네임스페이스는 전체 나열이 아니라 근접 후보를 좁혀 제시해야 한다.
        err = run_raw(ctx_path, "set-field", "--field=config.dev_impll.auto_start", "--value=true")
        assert err.returncode != 0
        assert "dev_impl" in err.stderr
        # 근접 후보가 잡혔으면 무관한 네임스페이스까지 나열하지 않는다.
        assert "graphify" not in err.stderr

    def test_unknown_key_suggests_close_match(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.dev_impl.auto_comit", "--value=true")
        assert err.returncode != 0
        assert "auto_commit" in err.stderr

    def test_unknown_key_message_names_the_namespace(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.git.bogusKey", "--value=x")
        assert err.returncode != 0
        assert "git" in err.stderr

    def test_rejected_write_leaves_no_context_file(self, ctx_path):
        # 검증이 read-modify-write보다 앞선다 — 거부된 쓰기는 파일을 만들지 않는다.
        run_raw(ctx_path, "set-field", "--field=config.bogus.key", "--value=x")
        assert not Path(ctx_path).exists()

    def test_rejected_write_preserves_existing_value(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.dev_impl.auto_start", "--value=true")
        run_raw(ctx_path, "set-field", "--field=config.dev_impl.auto_start", "--value=maybe")
        assert read_ctx(ctx_path)["config"]["dev_impl"]["auto_start"] is True

    # --- 타입 불일치 ---
    def test_string_on_boolean_key_non_zero(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.dev_impl.auto_start", "--value=maybe")
        assert err.returncode != 0
        assert "boolean" in err.stderr

    def test_string_on_array_key_non_zero(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.graphify.targets", "--value=src")
        assert err.returncode != 0
        assert "array" in err.stderr

    def test_integer_on_boolean_key_non_zero(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.dev_impl.auto_start", "--value=1")
        assert err.returncode != 0

    def test_boolean_on_string_key_non_zero(self, ctx_path):
        # T3.5 근거 재현 — currentBatchTopic은 string인데 'false'는 bool로 추론된다.
        err = run_raw(ctx_path, "set-field",
                      "--field=config.dev_impl.currentBatchTopic", "--value=false")
        assert err.returncode != 0
        assert "boolean" in err.stderr

    def test_bare_value_flag_on_string_key_non_zero(self, ctx_path):
        # 등호 없는 bare `--value`는 parse_args가 True로 만든다 — 등호 있는 `--value=`와
        # 실패 양상이 달라야 사용자가 원인을 구분할 수 있다.
        err = run_raw(ctx_path, "set-field",
                      "--field=config.dev_impl.currentBatchTopic", "--value")
        assert err.returncode != 0
        assert "boolean" in err.stderr

    def test_all_digit_value_on_string_key_non_zero(self, ctx_path):
        # 전부 숫자인 토픽 이름은 int로 추론된다 — flow-impl Step 1(a)이 이 케이스를
        # 빈 문자열 기록으로 우회한다(알려진 한계: 그 토픽에서 mismatch 감지 비활성).
        err = run_raw(ctx_path, "set-field",
                      "--field=config.dev_impl.currentBatchTopic", "--value=2026")
        assert err.returncode != 0
        assert "integer" in err.stderr

    def test_integer_key_rejects_string(self, ctx_path, fixture_schema_path):
        err = run_raw(ctx_path, "set-field", "--field=config.some.count", "--value=many",
                      schema_path=fixture_schema_path)
        assert err.returncode != 0

    def test_integer_key_rejects_boolean(self, ctx_path, fixture_schema_path):
        # Python bool은 int의 서브클래스다 — 명시 배제가 없으면 통과한다.
        err = run_raw(ctx_path, "set-field", "--field=config.some.count", "--value=true",
                      schema_path=fixture_schema_path)
        assert err.returncode != 0

    # --- T3.5 대체 형태: 빈 문자열 ---
    def test_empty_value_reads_back_empty(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.dev_impl.currentBatchTopic", "--value=")
        assert run(ctx_path, "read", "--field=config.dev_impl.currentBatchTopic").stdout == "\n"

    def test_empty_value_clears_previous_topic(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.dev_impl.currentBatchTopic", "--value=E2-S3")
        run(ctx_path, "set-field", "--field=config.dev_impl.currentBatchTopic", "--value=")
        stored = read_ctx(ctx_path)["config"]["dev_impl"]["currentBatchTopic"]
        assert stored == ""
        # bool False가 아니라 빈 문자열이어야 한다 — string 타입 키의 reset 값 계약.
        assert isinstance(stored, str)

    # --- 읽기 관대성 (G6) ---
    def test_read_unknown_namespace_is_lenient(self, ctx_path):
        result = run(ctx_path, "read", "--field=config.bogus.key")
        assert result.stdout == "\n"

    def test_read_unknown_key_is_lenient(self, ctx_path):
        result = run(ctx_path, "read", "--field=config.dev_impl.auto_comit")
        assert result.stdout == "\n"

    # --- 스키마 부재·손상 → config 쓰기만 fail-closed ---
    def test_missing_schema_blocks_config_write(self, ctx_path, tmp_path):
        missing = str(tmp_path / "absent-config-schema.json")
        err = run_raw(ctx_path, "set-field", "--field=config.dev_impl.auto_start",
                      "--value=true", schema_path=missing)
        assert err.returncode != 0
        assert missing in err.stderr

    def test_corrupt_schema_blocks_config_write_without_traceback(self, ctx_path, tmp_path):
        broken = tmp_path / "broken-config-schema.json"
        broken.write_text("{not json", encoding="utf-8")
        err = run_raw(ctx_path, "set-field", "--field=config.dev_impl.auto_start",
                      "--value=true", schema_path=str(broken))
        assert err.returncode != 0
        assert "Traceback (most recent call last)" not in err.stderr

    def test_missing_schema_does_not_block_read(self, ctx_path, tmp_path):
        run(ctx_path, "set-field", "--field=config.dev_impl.auto_start", "--value=true")
        missing = str(tmp_path / "absent-config-schema.json")
        result = run(ctx_path, "read", "--field=config.dev_impl.auto_start",
                     schema_path=missing)
        assert result.stdout == "true\n"

    def test_missing_schema_does_not_block_topic_field_write(self, ctx_path, tmp_path):
        missing = str(tmp_path / "absent-config-schema.json")
        run(ctx_path, "register-topic", "--topic=sch-miss", "--spec=some/spec.md",
            schema_path=missing)
        run(ctx_path, "set-field", "--topic=sch-miss", "--field=plan", "--value=p.md",
            schema_path=missing)
        assert read_ctx(ctx_path)["topics"]["sch-miss"]["plan"] == "p.md"

    # --- 살아 있는 호출자 형태가 실 스키마를 통과하는지 (G6 무회귀) ---
    # 각 값은 스킬 문서가 실제로 만들어 내는 형태다. flow-init은 GH_AVAILABLE·
    # GH_NATIVE_SUBISSUE를 'true'/'false' 리터럴로만 두고, GH_VERSION은 `X.Y.Z` 정규식을
    # 통과한 문자열이거나 빈 문자열이다(파싱 실패·미설치). 두 경우를 모두 건다.


# 살아 있는 호출자가 쓰는 (ns, key, 리터럴) 조합. 각 항목은 스킬층·규칙 문서의 실제 호출
# 지점에서 그대로 옮겼다. 검증 대상은 "이 리터럴이 선언 타입에 부합하는가"라는 순수 함수
# 합성이므로 subprocess를 띄우지 않는다 — CLI 계약(exit code·stderr 문구)은 위 클래스가 덮는다.
LIVE_CALLER_SHAPES = [
    # flow-impl/SKILL.md Step 1(a)·1(b)·11
    ("dev_impl", "currentBatchRunning", "true"),
    ("dev_impl", "currentBatchRunning", "false"),
    ("dev_impl", "currentBatchTopic", "E2-S3"),
    ("dev_impl", "currentBatchTopic", ""),
    # flow-init/SKILL.md Step 7 (gh 감지 성공·실패 두 경로)
    ("gh", "available", "true"),
    ("gh", "available", "false"),
    ("gh", "native_subissue", "false"),
    ("gh", "version", "2.96.0"),
    ("gh", "version", ""),
    ("gh", "checked_at", "2026-07-30T00:00:00Z"),
    # flow-init/SKILL.md Step 5·6
    ("docs", "sourceFilter", '[".claude/",".codex/",".tack/","CLAUDE.md","AGENTS.md"]'),
    ("docs", "sourceFilter", "[]"),
    ("graphify", "targets", '["./src"]'),
    # flow-setup/SKILL.md Step 9
    ("git", "pushRemote", "origin"),
    ("git", "pullRemote", "upstream"),
    ("git", "baseBranch", "main"),
    ("git", "branchPattern", "^(feature|fix|chore)/"),
    # flow-review/SKILL.md · .tack/rules/git-workflow.md
    ("review", "adversarial_enabled", "true"),
    ("dev_impl", "auto_commit", "true"),
    ("spec", "auto_review", "true"),
    ("plan", "auto_review", "true"),
]


@pytest.mark.parametrize("ns,key,literal", LIVE_CALLER_SHAPES)
def test_live_caller_literal_satisfies_declared_type(ns, key, literal):
    """G6 무회귀 스윕 — 살아 있는 호출자의 값 리터럴이 스키마 타입 검사를 통과한다.

    하나라도 실패하면 그 호출 지점이 검증 도입 즉시 hard failure가 된다는 뜻이다.
    """
    schema = config_schema.load_schema(SCHEMA_PATH)
    entry = config_schema.lookup(schema, ns, key)
    assert entry is not None, f"config.{ns}.{key}가 스키마에 선언돼 있지 않다"
    coerced = dev_context.coerce_config_value(literal)
    assert config_schema.check_type(entry["type"], coerced), (
        f"config.{ns}.{key}는 {entry['type']} 타입인데 리터럴 {literal!r}가 "
        f"{config_schema.type_name(coerced)}로 추론된다"
    )
