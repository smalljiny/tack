"""tracked 공유 config 층(.tack/config.json) 읽기 병합 (E2-S3 Story 2 · G1 · G5).

`read --field=config.<ns>.<key>`가 leaf 단위로 local → shared 우선순위를 적용하고,
공유 파일이 없거나 손상돼도 모든 서브커맨드가 exit 0을 유지하는지 검증한다.

병합 판정은 순수 함수 dev_context.resolve_config_leaf가 소유한다. CLI stdout만으로는
"local []가 shared ["a"]를 이겼다"와 "둘 다 미설정"이 **둘 다 빈 줄**이라 구분되지 않으므로
(빈 배열 == 미설정 == "\\n" 출력 계약), 우선순위 케이스는 순수 함수 반환값과 CLI stdout을
모두 단언한다. 순수 함수 단언이 없으면 병합이 거꾸로 구현돼도 stdout 단언은 통과한다.

dev_context는 module import + 속성 접근으로 참조한다(`from dev_context import ...` 아님) —
미구현 심볼이 모듈 수집 에러가 아니라 개별 테스트 실패로 드러나게 하기 위함이다.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import dev_context
from _dc_helpers import (
    SCRIPT,
    read_ctx,
    run,
    run_raw,
    shared_config_path,
    write_ctx as write_local,
    write_shared_config as write_shared,
)


class TestSharedConfigPathResolution:
    """T2.1 — DEV_CONFIG_PATH override + local 경로 기준 2-hop 유도."""

    def test_env_override_takes_precedence(self, monkeypatch, tmp_path):
        override = str(tmp_path / "elsewhere.json")
        monkeypatch.setenv("DEV_CONFIG_PATH", override)
        assert dev_context.resolve_shared_config_path() == override

    def test_derives_two_hops_up_from_resolved_context_path(self, monkeypatch, tmp_path):
        # 렌더 dest 형태를 그대로 재현한다: $DEST/.tack/local/dev-context.json
        # → dirname 2회 → $DEST/.tack/ → $DEST/.tack/config.json.
        # 렌더 스모크 테스트(Story 7 T7.2)는 DEV_CONFIG_PATH를 설정하지 않고 이 유도에
        # 의존하므로, 이 테스트가 그 전제를 지키는 유일한 가드다. 정확 경로 등가 단언이라
        # SCRIPT_DIR 기준 유도로의 회귀도 함께 잡는다 — 그 경우 결과가 실제 저장소
        # 경로가 되어 tmp_path와 불일치한다.
        monkeypatch.delenv("DEV_CONFIG_PATH", raising=False)
        monkeypatch.setenv(
            "DEV_CONTEXT_PATH", str(tmp_path / ".tack" / "local" / "dev-context.json")
        )
        assert dev_context.resolve_shared_config_path() == str(tmp_path / ".tack" / "config.json")


class TestReadSharedConfig:
    """T2.2 — 파일 부재·손상 시 빈 shared 층으로 degrade (G5)."""

    def test_missing_file_returns_empty_layer(self, monkeypatch, tmp_path):
        monkeypatch.setenv("DEV_CONFIG_PATH", str(tmp_path / "absent.json"))
        assert dev_context.read_shared_config() == {"file_format": "1.0", "config": {}}

    def test_valid_file_is_returned_as_is(self, monkeypatch, tmp_path):
        path = tmp_path / "config.json"
        write_shared(path, {"git": {"pushRemote": "upstream"}})
        monkeypatch.setenv("DEV_CONFIG_PATH", str(path))
        assert dev_context.read_shared_config()["config"] == {"git": {"pushRemote": "upstream"}}

    def test_corrupt_json_degrades_to_empty_layer(self, monkeypatch, tmp_path, capsys):
        path = tmp_path / "config.json"
        path.write_text("this is not json {{{", encoding="utf-8")
        monkeypatch.setenv("DEV_CONFIG_PATH", str(path))
        assert dev_context.read_shared_config() == {"file_format": "1.0", "config": {}}

    def test_non_dict_top_level_degrades_to_empty_layer(self, monkeypatch, tmp_path):
        path = tmp_path / "config.json"
        path.write_text('["not", "an", "object"]', encoding="utf-8")
        monkeypatch.setenv("DEV_CONFIG_PATH", str(path))
        assert dev_context.read_shared_config() == {"file_format": "1.0", "config": {}}

    def test_non_dict_config_field_degrades_to_empty_layer(self, monkeypatch, tmp_path):
        path = tmp_path / "config.json"
        path.write_text('{"file_format": "1.0", "config": "oops"}', encoding="utf-8")
        monkeypatch.setenv("DEV_CONFIG_PATH", str(path))
        assert dev_context.read_shared_config() == {"file_format": "1.0", "config": {}}


class TestLoadSharedConfigIsStrict:
    """load_shared_config는 degrade 정책을 담지 않는다 — 손상을 ok=False로 구분해 돌려준다.

    Story 4의 read-modify-write가 이 엄격 형태를 써야, 파싱하지 못한 tracked 파일을 단일
    키로 덮어써 팀 config를 날리는 사고를 막을 수 있다. 관대 degrade는 read 경로 전용이다.
    """

    def test_missing_file_is_ok_with_an_empty_envelope(self, tmp_path):
        ok, data = dev_context.load_shared_config(str(tmp_path / "absent.json"))
        assert ok is True
        assert data == {"file_format": "1.0", "config": {}}

    def test_valid_file_is_ok_with_its_content(self, tmp_path):
        path = tmp_path / "config.json"
        write_shared(path, {"git": {"pushRemote": "upstream"}})
        ok, data = dev_context.load_shared_config(str(path))
        assert ok is True
        assert data["config"] == {"git": {"pushRemote": "upstream"}}

    def test_corrupt_file_is_not_ok_and_does_not_degrade_to_empty(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text("{ not json", encoding="utf-8")
        ok, reason = dev_context.load_shared_config(str(path))
        assert ok is False
        assert isinstance(reason, str)

    def test_non_dict_config_field_is_not_ok(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text('{"file_format": "1.0", "config": "oops"}', encoding="utf-8")
        ok, _ = dev_context.load_shared_config(str(path))
        assert ok is False


class TestResolveConfigLeaf:
    """T2.3 — 병합 우선순위 순수 함수. own-property hit 여부를 반환값으로 노출한다."""

    def test_shared_only_returns_shared_value(self):
        val = dev_context.resolve_config_leaf([{}, {"git": {"pushRemote": "origin"}}], "git", "pushRemote")
        assert val == "origin"

    def test_local_wins_over_shared(self):
        val = dev_context.resolve_config_leaf([{"git": {"pushRemote": "fork"}}, {"git": {"pushRemote": "origin"}}], "git", "pushRemote")
        assert val == "fork"

    def test_local_json_null_wins_and_is_not_a_miss(self):
        # local own property가 JSON null이면 local이 이긴다 — shared로 폴백하지 않는다.
        # None(=local hit)과 _MISSING(=양층 miss)의 구분이 이 케이스의 전부다.
        val = dev_context.resolve_config_leaf([{"git": {"pushRemote": None}}, {"git": {"pushRemote": "origin"}}], "git", "pushRemote")
        assert val is None
        assert val is not dev_context._MISSING

    def test_local_empty_array_wins_over_shared_array(self):
        # 배열은 통째 교체다 — concat이면 ["a"]가, 우선순위가 뒤집혔으면 ["a"]가 나온다.
        val = dev_context.resolve_config_leaf([{"docs": {"sourceFilter": []}}, {"docs": {"sourceFilter": ["a"]}}], "docs", "sourceFilter")
        assert val == []
        assert val is not dev_context._MISSING

    def test_local_false_wins_over_shared_true(self):
        val = dev_context.resolve_config_leaf([{"risk": {"high_gate_enabled": False}}, {"risk": {"high_gate_enabled": True}}], "risk", "high_gate_enabled")
        assert val is False

    def test_missing_in_both_layers_returns_missing_sentinel(self):
        val = dev_context.resolve_config_leaf([{}, {}], "git", "pushRemote")
        assert val is dev_context._MISSING

    def test_missing_leaf_in_both_namespaces_returns_missing_sentinel(self):
        val = dev_context.resolve_config_leaf([{"git": {}}, {"git": {}}], "git", "pushRemote")
        assert val is dev_context._MISSING

    def test_local_namespace_non_dict_falls_back_to_shared(self):
        val = dev_context.resolve_config_leaf([{"git": "corrupt"}, {"git": {"pushRemote": "origin"}}], "git", "pushRemote")
        assert val == "origin"

    def test_inherited_attribute_is_not_an_own_property_hit(self):
        # hasOwn 가드: dict 상속 속성이 값으로 읽히면 안 된다.
        val = dev_context.resolve_config_leaf([{}, {}], "toString", "name")
        assert val is dev_context._MISSING

    def test_reserved_segment_is_rejected_in_both_layers(self):
        # 예약 키 거부는 local·shared 두 층에 동일 적용된다 — 어느 층에 값이 들어
        # 있어도 읽히지 않는다.
        for ns, key in (("__proto__", "polluted"), ("git", "constructor"), ("prototype", "x")):
            local = {ns: {key: "from-local"}}
            shared = {ns: {key: "from-shared"}}
            assert dev_context.resolve_config_leaf([local, shared], ns, key) is dev_context._MISSING

    def test_non_dict_local_layer_falls_back_to_shared(self):
        # local 층 자체가 dict가 아니어도 shared 조회가 계속된다 (방어적 degrade).
        val = dev_context.resolve_config_leaf([None, {"git": {"pushRemote": "origin"}}], "git", "pushRemote")
        assert val == "origin"

    def test_a_middle_layer_can_be_inserted_without_changing_the_mechanism(self):
        # 스펙 §3.6 E4 seam: 런타임 공유 층(Mongo)은 tracked와 local 사이에 원소 하나로
        # 삽입된다. layers가 iterable이므로 삽입만으로 우선순위가 성립해야 한다.
        layers = [
            {"git": {}},                              # local — miss
            {"git": {"pushRemote": "from-runtime"}},  # E4 런타임 공유 층
            {"git": {"pushRemote": "from-tracked"}},  # tracked
        ]
        assert dev_context.resolve_config_leaf(layers, "git", "pushRemote") == "from-runtime"

    def test_later_layers_are_not_acquired_when_an_earlier_layer_answers(self):
        # generator를 넘기면 앞선 layer가 답할 때 뒤쪽 layer 획득이 수행되지 않는다.
        # E4에서 뒤쪽 layer는 네트워크 호출이므로 이 지연이 비용 계약이다.
        acquired = []

        def layers():
            yield {"git": {"pushRemote": "from-local"}}
            acquired.append("shared")
            yield {"git": {"pushRemote": "from-shared"}}

        assert dev_context.resolve_config_leaf(layers(), "git", "pushRemote") == "from-local"
        assert acquired == []


class TestReadMergeCli:
    """T2.3 — CLI 경로의 병합 동작 (순수 함수 단언과 쌍을 이룬다)."""

    def test_shared_only_value_is_returned(self, ctx_path):
        write_shared(shared_config_path(ctx_path), {"git": {"pushRemote": "origin"}})
        assert run(ctx_path, "read", "--field=config.git.pushRemote").stdout == "origin\n"

    def test_local_value_wins_over_shared(self, ctx_path):
        write_shared(shared_config_path(ctx_path), {"git": {"pushRemote": "origin"}})
        run(ctx_path, "set-field", "--field=config.git.pushRemote", "--value=fork")
        assert run(ctx_path, "read", "--field=config.git.pushRemote").stdout == "fork\n"

    def test_local_json_null_does_not_fall_back_to_shared(self, ctx_path):
        write_local(ctx_path, {"git": {"pushRemote": None}})
        write_shared(shared_config_path(ctx_path), {"git": {"pushRemote": "origin"}})
        assert run(ctx_path, "read", "--field=config.git.pushRemote").stdout == "\n"

    def test_local_empty_array_does_not_fall_back_to_shared(self, ctx_path):
        write_local(ctx_path, {"docs": {"sourceFilter": []}})
        write_shared(shared_config_path(ctx_path), {"docs": {"sourceFilter": ["a"]}})
        assert run(ctx_path, "read", "--field=config.docs.sourceFilter").stdout == "\n"

    def test_shared_array_is_newline_joined(self, ctx_path):
        write_shared(shared_config_path(ctx_path), {"docs": {"sourceFilter": ["a", "b"]}})
        assert run(ctx_path, "read", "--field=config.docs.sourceFilter").stdout == "a\nb\n"

    def test_shared_boolean_is_lowercase(self, ctx_path):
        write_shared(shared_config_path(ctx_path), {"risk": {"high_gate_enabled": True}})
        assert run(ctx_path, "read", "--field=config.risk.high_gate_enabled").stdout == "true\n"

    def test_local_false_wins_over_shared_true(self, ctx_path):
        write_shared(shared_config_path(ctx_path), {"risk": {"high_gate_enabled": True}})
        run(ctx_path, "set-field", "--field=config.risk.high_gate_enabled", "--value=false")
        assert run(ctx_path, "read", "--field=config.risk.high_gate_enabled").stdout == "false\n"

    def test_unset_key_stays_empty_and_does_not_synthesize_schema_default(self, ctx_path):
        # 스키마는 git.pushRemote default="origin", risk.high_gate_enabled default=true를
        # 선언하지만 read는 default를 합성하지 않는다 (미설정 의미 보존, G6).
        assert run(ctx_path, "read", "--field=config.git.pushRemote").stdout == "\n"
        assert run(ctx_path, "read", "--field=config.risk.high_gate_enabled").stdout == "\n"

    def test_set_field_writes_local_only_in_this_story(self, ctx_path):
        # Story 2 범위: shared 쓰기는 없다 (Story 4 소관).
        run(ctx_path, "set-field", "--field=config.git.pushRemote", "--value=fork")
        assert read_ctx(ctx_path)["config"]["git"]["pushRemote"] == "fork"
        assert not os.path.exists(shared_config_path(ctx_path))

    def test_shared_layer_is_ignored_for_topic_fields(self, ctx_path):
        write_shared(shared_config_path(ctx_path), {"git": {"pushRemote": "origin"}})
        run(ctx_path, "register-topic", "--topic=t1", "--spec=some/spec.md")
        assert run(ctx_path, "read", "--topic=t1", "--field=phase").stdout == "spec\n"


class TestReservedKeyGuardAcrossLayers:
    """예약 키 거부·경로 검사가 shared 조회보다 먼저 일어난다."""

    def test_reserved_namespace_rejected_even_with_shared_file(self, ctx_path):
        write_shared(shared_config_path(ctx_path), {"git": {"pushRemote": "origin"}})
        err = run_raw(ctx_path, "read", "--field=config.__proto__.toString")
        assert err.returncode != 0
        assert "예약된 키" in err.stderr

    def test_depth_violation_rejected_before_shared_warning(self, ctx_path):
        # 손상된 shared 파일이 있어도 경로 위반 메시지가 먼저 나오고 경고는 없다.
        Path(shared_config_path(ctx_path)).write_text("not json", encoding="utf-8")
        err = run_raw(ctx_path, "read", "--field=config.git.pushRemote.extra")
        assert err.returncode != 0
        assert "config 경로는 정확히" in err.stderr
        assert "공유 config" not in err.stderr

    def test_bare_config_field_rejected_before_shared_warning(self, ctx_path):
        # 깊이 1 위반(read 경로). set-field 쪽에만 대응 케이스가 있었다.
        Path(shared_config_path(ctx_path)).write_text("not json", encoding="utf-8")
        err = run_raw(ctx_path, "read", "--field=config")
        assert err.returncode != 0
        assert "config 경로는 정확히" in err.stderr
        assert "공유 config" not in err.stderr

    def test_shared_reserved_key_content_is_not_readable(self, ctx_path):
        # 공유 파일에 예약 키가 들어 있어도 읽기 경로가 거부한다.
        write_shared(shared_config_path(ctx_path), {"__proto__": {"polluted": "yes"}})
        err = run_raw(ctx_path, "read", "--field=config.__proto__.polluted")
        assert err.returncode != 0


class TestMissingSharedFileDegradation:
    """G5 — .tack/config.json 부재 상태에서 6개 서브커맨드 전부 exit 0."""

    def test_all_six_subcommands_exit_zero_without_shared_file(self, ctx_path):
        assert not os.path.exists(shared_config_path(ctx_path))

        # 각 서브커맨드는 선행 guard(토픽 존재·전환 유효성)를 통과하는 입력으로 호출한다 —
        # 실패가 공유 파일 부재 이외의 이유에서 나오지 않게 한다.
        run(ctx_path, "register-topic", "--topic=g5", "--spec=some/spec.md")
        run(ctx_path, "set-field", "--field=config.git.pushRemote", "--value=origin")
        run(ctx_path, "read", "--field=config.git.pushRemote")
        run(ctx_path, "update-state", "--topic=g5", "--phase=spec", "--status=reviewing")
        run(ctx_path, "force-state", "--topic=g5", "--phase=spec", "--status=drafting")
        run(ctx_path, "remove-topic", "--topic=g5")

        assert not os.path.exists(shared_config_path(ctx_path))

    def test_read_is_empty_and_silent_without_shared_file(self, ctx_path):
        result = run(ctx_path, "read", "--field=config.git.pushRemote")
        assert result.stdout == "\n"
        assert result.stderr == ""


class TestCorruptSharedFileDegradation:
    """G5 — 손상된 .tack/config.json에서 read가 경고 + exit 0 + 빈 출력."""

    def test_non_json_shared_file_warns_and_exits_zero(self, ctx_path):
        Path(shared_config_path(ctx_path)).write_text("{ not json at all", encoding="utf-8")
        result = run(ctx_path, "read", "--field=config.git.pushRemote")
        assert result.returncode == 0
        assert result.stdout == "\n"
        assert "공유 config" in result.stderr
        assert len(result.stderr.strip().split("\n")) == 1

    def test_corrupt_shared_file_still_serves_local_value_without_warning(self, ctx_path):
        # local이 답하는 읽기는 공유 파일을 열지 않으므로 경고가 없어야 한다.
        # 경고가 새면 스킬층의 `VALUE=$(... read ...)` 호출마다 사용자 터미널로 샌다.
        Path(shared_config_path(ctx_path)).write_text("{ not json at all", encoding="utf-8")
        run(ctx_path, "set-field", "--field=config.git.pushRemote", "--value=fork")
        result = run(ctx_path, "read", "--field=config.git.pushRemote")
        assert result.stdout == "fork\n"
        assert result.stderr == ""

    def test_corrupt_shared_file_does_not_warn_on_unrelated_local_read(self, ctx_path):
        Path(shared_config_path(ctx_path)).write_text("{ not json at all", encoding="utf-8")
        run(ctx_path, "register-topic", "--topic=quiet", "--spec=some/spec.md")
        result = run(ctx_path, "read", "--topic=quiet", "--field=phase")
        assert result.stdout == "spec\n"
        assert result.stderr == ""

    def test_non_dict_shared_file_warns_and_exits_zero(self, ctx_path):
        Path(shared_config_path(ctx_path)).write_text("[1, 2, 3]", encoding="utf-8")
        result = run(ctx_path, "read", "--field=config.git.pushRemote")
        assert result.returncode == 0
        assert result.stdout == "\n"
        assert "공유 config" in result.stderr

    def test_corrupt_shared_file_does_not_block_other_subcommands(self, ctx_path):
        Path(shared_config_path(ctx_path)).write_text("{ not json at all", encoding="utf-8")
        run(ctx_path, "register-topic", "--topic=corrupt", "--spec=some/spec.md")
        run(ctx_path, "update-state", "--topic=corrupt", "--phase=spec", "--status=reviewing")
        run(ctx_path, "remove-topic", "--topic=corrupt")

    def test_non_string_array_elements_degrade_to_js_string_parity(self, ctx_path):
        # tracked 공유 파일은 손으로 편집되므로 배열에 비-문자열 원소가 들어올 수 있다.
        # 레퍼런스 JS val.join('\n')은 강제 변환하고 null을 빈 문자열로 만든다 —
        # 포트가 TypeError로 exit 1 하면 그 브랜치의 모든 사용자에게 read가 깨진다.
        Path(shared_config_path(ctx_path)).write_text(
            json.dumps({"file_format": "1.0", "config": {"docs": {"sourceFilter": [1, None, "c"]}}}),
            encoding="utf-8",
        )
        result = run(ctx_path, "read", "--field=config.docs.sourceFilter")
        assert result.returncode == 0
        assert result.stdout == "1\n\nc\n"


class TestSharedLayerIsolation:
    """T2.4 — shared-layer 테스트가 pytest basetemp를 통해 서로의 쓰기를 관측하지 않는다."""

    def test_two_hop_default_location_is_not_consulted(self, ctx_path):
        # 헬퍼가 DEV_CONFIG_PATH 주입을 잃으면 CLI는 2-hop 기본 유도로 회귀하고, 그 위치는
        # ctx_path 픽스처 레이아웃에서 pytest basetemp(세션 공유)다. 그 자리에 표식을 심고
        # 읽히지 **않는지** 직접 단언한다 — 실행 순서와 무관하며 실패 시 표식이 그대로 찍힌다.
        two_hop = Path(ctx_path).resolve().parent.parent / "config.json"
        write_shared(two_hop, {"git": {"baseBranch": "must-not-be-read"}})
        assert run(ctx_path, "read", "--field=config.git.baseBranch").stdout == "\n"

    def test_isolation_writer_seeds_a_value(self, ctx_path):
        write_shared(shared_config_path(ctx_path), {"git": {"baseBranch": "aaa-from-writer-a"}})
        assert run(ctx_path, "read", "--field=config.git.baseBranch").stdout == "aaa-from-writer-a\n"

    def test_isolation_reader_sees_no_prior_writes(self, ctx_path):
        assert not os.path.exists(shared_config_path(ctx_path))
        result = run(ctx_path, "read", "--field=config.git.baseBranch")
        assert result.stdout == "\n"
        assert result.stderr == ""


class TestProductionDerivationEndToEnd:
    """T2.1 — DEV_CONFIG_PATH 없이 CLI가 프로덕션 2-hop 유도로 공유 파일에 도달한다.

    나머지 CLI 테스트는 헬퍼가 DEV_CONFIG_PATH를 주입하므로 유도를 타지 않는다. 이 클래스만
    override를 걷어내고 렌더 dest와 같은 레이아웃을 만들어, Story 7 T7.2가 의존하는 전제를
    문자열 단언이 아니라 실제 읽기로 고정한다.
    """

    def test_cli_reads_shared_through_default_derivation(self, tmp_path):
        local = tmp_path / ".tack" / "local" / "dev-context.json"
        local.parent.mkdir(parents=True)
        write_local(local, {})
        write_shared(tmp_path / ".tack" / "config.json", {"git": {"baseBranch": "from-derivation"}})
        env = {**os.environ, "DEV_CONTEXT_PATH": str(local)}
        env.pop("DEV_CONFIG_PATH", None)
        result = subprocess.run(
            [sys.executable, SCRIPT, "read", "--field=config.git.baseBranch"],
            capture_output=True, text=True, encoding="utf-8", env=env,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout == "from-derivation\n"
