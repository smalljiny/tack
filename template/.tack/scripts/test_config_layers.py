"""set-field 쓰기 라우팅 (E2-S3 Story 4 · G3 — layer).

스키마 `layer` 선언이 쓰기 목적지를 정하고, `--layer` 오버라이드가 거부표대로 동작하며,
tracked 공유 파일(`.tack/config.json`)이 최초 쓰기에서 생성되고 기존 내용을 잃지 않는지
검증한다.

목적지 단언은 **배타적**이다 — 값이 기대한 파일에 있는지만 보지 않고, 다른 파일이 생성되지
않았거나 변경되지 않았음을 함께 단언한다. 값 존재만 보면 양쪽에 쓰는 버그가 통과한다.

공유 파일 경로는 항상 `_dc_helpers.run`/`run_raw`(DEV_CONFIG_PATH 주입)로 실행해 격리한다 —
env를 손으로 구성해 주입을 잃으면 shared **쓰기**가 2-hop 기본 유도로 pytest basetemp에
떨어져 다른 테스트의 격리 단언을 오염시킨다.
"""

import json
import os
from pathlib import Path

import pytest

import config_schema
import dev_context
from _dc_helpers import (
    SCHEMA_PATH,
    read_ctx,
    read_shared_config_file,
    run,
    run_raw,
    shared_config_path,
    shared_value,
    write_ctx as write_local,
    write_shared_config as write_shared,
)

# 선언 타입별 대표 리터럴. 실사용 스키마의 모든 키를 한 번씩 써 보는 스윕에 쓴다.
LITERAL_BY_TYPE = {"string": "x", "boolean": "true", "integer": "1", "array": "[]"}


def _all_schema_keys(schema):
    """실사용 스키마가 선언한 (ns, key, type, layer) 전부.

    라우팅을 키 몇 개의 표본이 아니라 인벤토리 전체로 고정한다 — 새 키가 추가되면
    스윕이 자동으로 그 키의 목적지를 검증한다.
    """
    return [
        (ns, key, config_schema.lookup(schema, ns, key)["type"],
         config_schema.layer_of(schema, ns, key))
        for ns in config_schema.namespaces(schema)
        for key in config_schema.keys_of(schema, ns)
    ]


# 순수 스윕이 재사용하는 단일 로드본 — 인벤토리 열거도 이 객체를 받는다.
_SCHEMA = config_schema.load_schema(SCHEMA_PATH)
ALL_SCHEMA_KEYS = _all_schema_keys(_SCHEMA)

# tracked 공유 파일로 가야 하는 키 — plan의 layer 표(§Story 1 T1.2)에서 손으로 옮긴
# **독립 oracle**이다. 스윕의 기대값을 `WRITE_ROUTES[layer_of(...)]`로 계산하면 양변이
# 같은 스키마 조회로 접혀 어떤 선언에도 참이 된다(자기 자신을 단언). 리터럴로 두면 계약의
# layer를 바꿀 때 이 집합도 함께 고쳐야 하므로, 팀 설정이 조용히 커밋 대상에서 빠지는
# 변경이 테스트 수정 없이 통과하지 못한다.
SHARED_KEYS = frozenset(
    {
        ("git", "pushRemote"),
        ("git", "pullRemote"),
        ("git", "baseBranch"),
        ("git", "branchPattern"),
        ("docs", "sourceFilter"),
        ("graphify", "targets"),
        ("risk", "high_gate_enabled"),
    }
)


class TestDefaultRouting:
    """T4.1 — 스키마 layer가 기본 쓰기 대상을 정한다."""

    @pytest.mark.parametrize(
        "ns,key,declared_type,layer",
        ALL_SCHEMA_KEYS,
        ids=[f"{ns}.{key}" for ns, key, _, _ in ALL_SCHEMA_KEYS],
    )
    def test_default_destination_matches_declared_layer(self, ns, key, declared_type, layer):
        # 목적지 결정은 순수 함수다 — 키마다 인터프리터를 띄우지 않는다. 이 스윕이 지키는
        # 것은 "모든 키가 plan 표대로 라우팅되는가"이고, 파일 배타성은 아래 층별 전용
        # subprocess 테스트 3개가 덮는다. 이 파일은 배포 산출물이라 spawn 비용이 모든 배포
        # 프로젝트의 검증 게이트에서 되풀이된다.
        expected = "shared" if (ns, key) in SHARED_KEYS else "local"
        assert dev_context.resolve_write_target(_SCHEMA, ns, key) == expected
        # 선언 layer와 목적지의 대응도 리터럴 기준으로 고정한다 — shared 목적지는 shared
        # 선언에서만 나오고, local·cache 선언은 둘 다 local 파일로 접힌다.
        assert (layer == "shared") == (expected == "shared")
        # 선언 타입 리터럴이 검증을 통과해야 그 목적지에 실제로 도달한다.
        assert dev_context.validate_config_write(
            _SCHEMA, ns, key, LITERAL_BY_TYPE[declared_type]
        ) == dev_context.coerce_config_value(LITERAL_BY_TYPE[declared_type])

    def test_shared_key_oracle_has_no_stale_entries(self):
        # 리터럴 oracle이 스키마에서 사라진 키를 붙들고 있으면 스윕이 그 키를 검사하지
        # 않으면서도 통과한다 — 삭제된 키는 여기서 걸린다.
        declared = {(ns, key) for ns, key, _, _ in ALL_SCHEMA_KEYS}
        assert SHARED_KEYS <= declared

    def test_shared_key_creates_the_tracked_file(self, ctx_path):
        # 최초 쓰기의 파일 생성·봉투 모양·목적지 배타성을 한 번의 쓰기로 함께 단언한다.
        # 같은 명령을 케이스마다 다시 spawn하면 그 비용이 배포된 모든 프로젝트의 검증
        # 게이트에서 재발한다 (이 파일은 배포 산출물이다).
        run(ctx_path, "set-field", "--field=config.git.pushRemote", "--value=origin")
        data = read_shared_config_file(shared_config_path(ctx_path))
        assert data["config"]["git"]["pushRemote"] == "origin"
        assert set(data.keys()) == {"file_format", "config"}
        assert data["file_format"] == "1.0"
        # local 파일은 만들지 않는다 — 배타적 목적지.
        assert not os.path.exists(ctx_path)

    def test_local_key_stays_in_the_ignored_file(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.dev_impl.auto_commit", "--value=true")
        assert read_ctx(ctx_path)["config"]["dev_impl"]["auto_commit"] is True
        assert not os.path.exists(shared_config_path(ctx_path))

    def test_cache_key_stays_in_the_ignored_file(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.codex.available", "--value=true")
        assert read_ctx(ctx_path)["config"]["codex"]["available"] is True
        assert not os.path.exists(shared_config_path(ctx_path))

    def test_topic_field_write_does_not_touch_the_shared_file(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=r1", "--spec=some/spec.md")
        run(ctx_path, "set-field", "--topic=r1", "--field=plan", "--value=p.md")
        assert read_ctx(ctx_path)["topics"]["r1"]["plan"] == "p.md"
        assert not os.path.exists(shared_config_path(ctx_path))


class TestLayerOverride:
    """T4.2 — `--layer` 오버라이드 거부표."""

    def test_shared_key_with_layer_local_writes_local_only(self, ctx_path):
        shared = shared_config_path(ctx_path)
        write_shared(shared, {"git": {"pushRemote": "origin"}})
        run(ctx_path, "set-field", "--field=config.git.pushRemote",
            "--layer=local", "--value=fork")
        assert read_ctx(ctx_path)["config"]["git"]["pushRemote"] == "fork"
        # 개인 오버라이드는 팀 값을 지우지 않는다.
        assert shared_value(ctx_path, "git", "pushRemote") == "origin"

    def test_shared_key_with_layer_shared_matches_the_default(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.git.baseBranch",
            "--layer=shared", "--value=develop")
        assert shared_value(ctx_path, "git", "baseBranch") == "develop"
        assert not os.path.exists(ctx_path)

    def test_local_key_with_layer_local_writes_local(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.dev_impl.auto_commit",
            "--layer=local", "--value=true")
        assert read_ctx(ctx_path)["config"]["dev_impl"]["auto_commit"] is True
        assert not os.path.exists(shared_config_path(ctx_path))

    def test_cache_key_with_layer_local_writes_local(self, ctx_path):
        # 표의 마지막 셀 — `cache` 선언 키에 `--layer=local`을 명시하면 기본과 같은 파일로
        # 접힌다. 이 셀이 없으면 9개 셀 중 8개만 CLI 수준에서 실행된다.
        run(ctx_path, "set-field", "--field=config.codex.available",
            "--layer=local", "--value=true")
        assert read_ctx(ctx_path)["config"]["codex"]["available"] is True
        assert not os.path.exists(shared_config_path(ctx_path))

    def test_local_key_rejects_promotion_to_shared(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.dev_impl.auto_commit",
                      "--layer=shared", "--value=true")
        assert err.returncode != 0
        assert "shared" in err.stderr
        assert "dev_impl.auto_commit" in err.stderr
        # 거부된 쓰기는 어느 파일도 만들지 않는다.
        assert not os.path.exists(shared_config_path(ctx_path))
        assert not os.path.exists(ctx_path)

    def test_rejected_promotion_preserves_the_existing_shared_file(self, ctx_path):
        shared = shared_config_path(ctx_path)
        write_shared(shared, {"git": {"pushRemote": "origin"}})
        before = Path(shared).read_text(encoding="utf-8")
        err = run_raw(ctx_path, "set-field", "--field=config.codex.available",
                      "--layer=shared", "--value=true")
        assert err.returncode != 0
        assert Path(shared).read_text(encoding="utf-8") == before

    def test_unknown_layer_value_is_rejected_with_the_allowed_values(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.git.pushRemote",
                      "--layer=bogus", "--value=x")
        assert err.returncode != 0
        assert "local" in err.stderr
        assert "shared" in err.stderr
        # 호출 오류이지 스키마 오류가 아니다 — 스키마 조회 문구가 섞이면 순서가 뒤집힌 것이다.
        assert "네임스페이스" not in err.stderr
        assert "타입" not in err.stderr

    def test_unknown_layer_value_is_rejected_before_the_schema_lookup(self, ctx_path):
        # 네임스페이스도 layer도 잘못됐을 때 layer 메시지가 나와야 한다 — 플래그 오타가
        # "알 수 없는 네임스페이스"로 표면화되면 사용자가 원인을 찾지 못한다.
        err = run_raw(ctx_path, "set-field", "--field=config.bogus.key",
                      "--layer=bogus", "--value=x")
        assert err.returncode != 0
        assert "네임스페이스" not in err.stderr

    def test_unknown_layer_value_is_rejected_after_the_path_check(self, ctx_path):
        # 경로 깊이 위반은 기존 계약대로 먼저 보고된다.
        err = run_raw(ctx_path, "set-field", "--field=config.a.b.c",
                      "--layer=bogus", "--value=x")
        assert err.returncode != 0
        assert "config.<namespace>.<key>" in err.stderr

    def test_layer_value_is_case_sensitive(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.git.pushRemote",
                      "--layer=Shared", "--value=x")
        assert err.returncode != 0
        assert not os.path.exists(shared_config_path(ctx_path))

    def test_bare_layer_flag_is_rejected(self, ctx_path):
        # 등호 없는 `--layer`는 parse_args가 True로 만든다 — 허용 값 안내로 떨어져야 한다.
        err = run_raw(ctx_path, "set-field", "--field=config.git.pushRemote",
                      "--layer", "--value=x")
        assert err.returncode != 0
        assert "local" in err.stderr
        assert "shared" in err.stderr

    def test_unknown_key_is_still_rejected_under_layer_local(self, ctx_path):
        # layer 오버라이드가 키 검증을 우회시키지 않는다.
        err = run_raw(ctx_path, "set-field", "--field=config.git.bogusKey",
                      "--layer=local", "--value=x")
        assert err.returncode != 0
        assert "git" in err.stderr

    def test_type_mismatch_is_still_rejected_under_layer_local(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.dev_impl.auto_commit",
                      "--layer=local", "--value=maybe")
        assert err.returncode != 0
        assert "boolean" in err.stderr


class TestLayerOutsideConfigWrite:
    """T4.3 — `--layer`는 config 쓰기 경로 전용이다."""

    def test_topic_field_with_layer_is_rejected(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=t1", "--spec=some/spec.md")
        err = run_raw(ctx_path, "set-field", "--topic=t1", "--field=plan",
                      "--layer=shared", "--value=x")
        assert err.returncode != 0
        assert "--layer" in err.stderr
        # 거부된 쓰기는 기존 값을 바꾸지 않는다.
        assert read_ctx(ctx_path)["topics"]["t1"]["plan"] is None

    def test_current_topic_with_layer_is_rejected(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=current_topic",
                      "--layer=local", "--value=t1")
        assert err.returncode != 0
        assert "--layer" in err.stderr

    def test_read_config_with_layer_shared_is_rejected(self, ctx_path):
        write_shared(shared_config_path(ctx_path), {"git": {"pushRemote": "origin"}})
        err = run_raw(ctx_path, "read", "--field=config.git.pushRemote", "--layer=shared")
        assert err.returncode != 0
        assert "--layer" in err.stderr

    def test_read_topic_field_with_layer_is_rejected(self, ctx_path):
        run(ctx_path, "register-topic", "--topic=t3", "--spec=some/spec.md")
        err = run_raw(ctx_path, "read", "--topic=t3", "--field=phase", "--layer=local")
        assert err.returncode != 0

    @pytest.mark.parametrize("sub", ["update-state", "force-state", "remove-topic"])
    def test_other_subcommands_reject_layer_instead_of_ignoring_it(self, ctx_path, sub):
        # 서브커맨드 축의 거부는 main()의 단일 게이트가 소유한다. `read`에만 인라인 가드를
        # 두면 나머지는 무음 무시로 남고, 새 서브커맨드마다 거부/무시가 저자 재량으로 갈린다.
        run(ctx_path, "register-topic", "--topic=t4", "--spec=some/spec.md")
        err = run_raw(ctx_path, sub, "--topic=t4", "--phase=spec", "--status=reviewing",
                      "--layer=shared")
        assert err.returncode != 0
        assert "--layer" in err.stderr


class TestSharedFilePreservation:
    """T4.5 — 기존 공유 파일 내용을 유지한 채 대상 leaf만 교체한다."""

    def test_unrelated_namespace_is_preserved(self, ctx_path):
        shared = shared_config_path(ctx_path)
        write_shared(shared, {"docs": {"sourceFilter": ["a"]}})
        run(ctx_path, "set-field", "--field=config.git.pushRemote", "--value=origin")
        data = read_shared_config_file(shared)
        assert data["config"]["docs"]["sourceFilter"] == ["a"]
        assert data["config"]["git"]["pushRemote"] == "origin"

    def test_sibling_key_in_the_same_namespace_is_preserved(self, ctx_path):
        shared = shared_config_path(ctx_path)
        write_shared(shared, {"git": {"baseBranch": "main"}})
        run(ctx_path, "set-field", "--field=config.git.pushRemote", "--value=origin")
        data = read_shared_config_file(shared)
        assert data["config"]["git"] == {"baseBranch": "main", "pushRemote": "origin"}

    def test_unknown_top_level_field_is_preserved(self, ctx_path):
        shared = shared_config_path(ctx_path)
        Path(shared).write_text(
            json.dumps({"file_format": "1.0", "note": "hand written",
                        "config": {"git": {"baseBranch": "main"}}}),
            encoding="utf-8",
        )
        run(ctx_path, "set-field", "--field=config.git.pushRemote", "--value=origin")
        data = read_shared_config_file(shared)
        assert data["note"] == "hand written"
        assert data["config"]["git"]["baseBranch"] == "main"

    def test_existing_leaf_is_replaced(self, ctx_path):
        shared = shared_config_path(ctx_path)
        write_shared(shared, {"git": {"pushRemote": "origin"}})
        run(ctx_path, "set-field", "--field=config.git.pushRemote", "--value=upstream")
        assert shared_value(ctx_path, "git", "pushRemote") == "upstream"

    def test_array_leaf_is_replaced_wholesale_not_concatenated(self, ctx_path):
        shared = shared_config_path(ctx_path)
        write_shared(shared, {"docs": {"sourceFilter": ["a", "b"]}})
        run(ctx_path, "set-field", "--field=config.docs.sourceFilter", '--value=["c"]')
        assert shared_value(ctx_path, "docs", "sourceFilter") == ["c"]

    def test_file_format_of_an_existing_file_is_not_rewritten(self, ctx_path):
        shared = shared_config_path(ctx_path)
        Path(shared).write_text(
            json.dumps({"file_format": "9.9", "config": {}}), encoding="utf-8"
        )
        run(ctx_path, "set-field", "--field=config.git.pushRemote", "--value=origin")
        assert read_shared_config_file(shared)["file_format"] == "9.9"


class TestSharedWriteMechanics:
    """T4.4 — 원자적 쓰기 관용구를 복제하지 않고 공유 헬퍼를 재사용한다."""

    def test_shared_write_leaves_no_temp_file_and_stays_readable_as_text(self, ctx_path):
        # 원자적 쓰기의 관측 가능한 결과 세 가지 — tmp 잔여물 없음, trailing newline,
        # indent=2 — 를 한 번의 쓰기로 단언한다 (배포 산출물의 spawn 비용 절감).
        shared = shared_config_path(ctx_path)
        run(ctx_path, "set-field", "--field=config.git.pushRemote", "--value=origin")
        assert not [e for e in os.listdir(os.path.dirname(shared)) if e.endswith(".tmp")]
        raw = Path(shared).read_text(encoding="utf-8")
        assert raw.endswith("\n")
        assert '\n  "config"' in raw

    def test_shared_file_keeps_non_ascii_unescaped(self, ctx_path):
        shared = shared_config_path(ctx_path)
        run(ctx_path, "set-field", "--field=config.git.branchPattern", "--value=한글")
        raw = Path(shared).read_text(encoding="utf-8")
        assert "한글" in raw
        assert "\\u" not in raw

    def test_shared_write_reuses_the_atomic_helper(self):
        # 관용구 복제 금지 — rename 호출은 원자적 쓰기 헬퍼 안 한 곳뿐이다.
        # `atomic_write_json(` 호출 수는 하한만 걸 수 있어(새 호출자가 늘면 통과) 불변식이
        # 아니다. `os.replace` 1회가 "관용구가 한 곳에만 있다"의 실제 불변식이다.
        source = Path(dev_context.__file__).read_text(encoding="utf-8")
        assert source.count("os.replace") == 1


class TestCorruptSharedFileAbortsWrite:
    """§4 — 파싱하지 못한 tracked 파일을 단일 키로 덮어쓰지 않는다."""

    def test_corrupt_shared_file_aborts_the_shared_write(self, ctx_path):
        shared = shared_config_path(ctx_path)
        Path(shared).write_text("{ not json at all", encoding="utf-8")
        err = run_raw(ctx_path, "set-field", "--field=config.git.pushRemote", "--value=origin")
        assert err.returncode != 0
        assert "Traceback (most recent call last)" not in err.stderr
        # 손상된 내용이 그대로 남아 있어야 한다 — 단일 키로 대체되면 데이터 손실이다.
        assert Path(shared).read_text(encoding="utf-8") == "{ not json at all"

    def test_non_dict_top_level_shared_file_aborts_the_shared_write(self, ctx_path):
        shared = shared_config_path(ctx_path)
        Path(shared).write_text("[1, 2, 3]", encoding="utf-8")
        err = run_raw(ctx_path, "set-field", "--field=config.git.pushRemote", "--value=origin")
        assert err.returncode != 0
        assert Path(shared).read_text(encoding="utf-8") == "[1, 2, 3]"

    def test_non_dict_namespace_aborts_the_shared_write(self, ctx_path):
        # load_shared_config는 최상위 config가 dict인지만 본다 — 네임스페이스가 문자열인
        # 파일은 ok=True로 통과한다. 그 자리를 빈 dict로 갈아끼우면 커밋된 내용이 조용히
        # 사라지므로, 손상 파일과 같은 등급으로 중단한다.
        shared = shared_config_path(ctx_path)
        before = json.dumps({"file_format": "1.0", "config": {"git": "oops"}})
        Path(shared).write_text(before, encoding="utf-8")
        err = run_raw(ctx_path, "set-field", "--field=config.git.pushRemote", "--value=origin")
        assert err.returncode != 0
        assert Path(shared).read_text(encoding="utf-8") == before
        # 가드를 지워도 TypeError가 non-zero exit + 파일 불변을 만족한다 — 그 경우와
        # 구분하려면 깔끔한 die 메시지였음을 함께 단언해야 한다.
        assert "Traceback (most recent call last)" not in err.stderr
        assert "네임스페이스가 객체가 아닙니다" in err.stderr

    def test_corrupt_shared_file_does_not_block_a_local_layer_write(self, ctx_path):
        # `--layer=local`은 공유 파일을 열지 않으므로 손상돼 있어도 통과해야 한다 —
        # 손상된 팀 파일 하나가 개인 층 쓰기까지 막으면 복구 경로가 사라진다.
        shared = shared_config_path(ctx_path)
        Path(shared).write_text("{ not json at all", encoding="utf-8")
        run(ctx_path, "set-field", "--field=config.git.pushRemote",
            "--layer=local", "--value=fork")
        assert read_ctx(ctx_path)["config"]["git"]["pushRemote"] == "fork"
        assert Path(shared).read_text(encoding="utf-8") == "{ not json at all"

    def test_corrupt_shared_file_does_not_block_a_local_key_write(self, ctx_path):
        shared = shared_config_path(ctx_path)
        Path(shared).write_text("{ not json at all", encoding="utf-8")
        run(ctx_path, "set-field", "--field=config.dev_impl.auto_commit", "--value=true")
        assert read_ctx(ctx_path)["config"]["dev_impl"]["auto_commit"] is True

    def test_rejected_shared_write_does_not_create_the_file(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.git.pushRemote", "--value=true")
        assert err.returncode != 0
        assert not os.path.exists(shared_config_path(ctx_path))


class TestReadPriorityAfterSharedWrite:
    """Story 2 우선순위가 라우팅 도입 후에도 유지된다."""

    def test_local_override_still_wins_after_a_shared_write(self, ctx_path):
        write_local(ctx_path, {"git": {"pushRemote": "fork"}})
        run(ctx_path, "set-field", "--field=config.git.pushRemote", "--value=origin")
        assert shared_value(ctx_path, "git", "pushRemote") == "origin"
        assert run(ctx_path, "read", "--field=config.git.pushRemote").stdout == "fork\n"

    def test_shared_write_is_readable_without_a_local_file(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.git.pushRemote", "--value=origin")
        assert run(ctx_path, "read", "--field=config.git.pushRemote").stdout == "origin\n"

    def test_layer_local_write_shadows_the_shared_value(self, ctx_path):
        run(ctx_path, "set-field", "--field=config.git.pushRemote", "--value=origin")
        run(ctx_path, "set-field", "--field=config.git.pushRemote",
            "--layer=local", "--value=fork")
        assert run(ctx_path, "read", "--field=config.git.pushRemote").stdout == "fork\n"


class TestRoutingTableVocabularyParity:
    """WRITE_ROUTES가 스키마 어휘와 갈라지지 않는지 고정한다.

    쓰기 가능 목적지 집합을 손으로 두 번 적으면(예전 WRITE_LAYERS 리터럴) 스키마에 층이
    늘어도 CLI만 모르는 무성 drift가 생긴다. 표에서 유도한다는 사실을 여기서 단언한다.
    """

    def test_route_rows_cover_every_declared_layer(self):
        assert set(dev_context.WRITE_ROUTES) == config_schema.LAYERS

    def test_write_layers_is_derived_from_the_request_column_axis(self):
        # `--layer`가 받는 것은 표의 **열 키**다. 목적지 값에서 유도하면 두 축이 우연히
        # 일치하는 동안만 맞고, 지정 불가한 목적지가 생기는 순간 CLI가 고를 수 없는 값을
        # 허용 값으로 광고한다 (그 입력은 "승격할 수 없습니다"라는 엉뚱한 오류로 떨어진다).
        columns = {k for row in dev_context.WRITE_ROUTES.values() for k in row if k}
        assert set(dev_context.WRITE_LAYERS) == columns

    def test_every_reachable_destination_has_a_writer(self):
        # 표의 목적지 태그와 writer 레지스트리가 1:1이어야 한다 — 새 행이 새 태그를
        # 반환하는데 항목이 없으면 그 쓰기가 조용히 다른 파일로 떨어진다.
        destinations = {
            d for row in dev_context.WRITE_ROUTES.values() for d in row.values() if d
        }
        assert destinations == set(dev_context.WRITE_TARGETS)

    def test_undeclared_route_does_not_drift_from_the_local_row(self):
        # 스키마 결함 폴백 행은 `local` 행의 별칭이다 — 복제본이면 열 추가 시 한쪽만 갱신된다.
        assert dev_context._UNDECLARED_ROUTE is dev_context.WRITE_ROUTES["local"]

    def test_cache_is_declarable_but_not_a_selectable_destination(self):
        # cache는 선언 layer일 뿐 --layer로 고를 수 없다 — 그 차집합이 어휘 차이의 전부다.
        assert config_schema.LAYERS - set(dev_context.WRITE_LAYERS) == {"cache"}

    def test_every_row_answers_every_request_form(self):
        # 표가 exhaustive해야 목적지 조회가 KeyError 대신 판정을 낸다.
        for layer, row in dev_context.WRITE_ROUTES.items():
            assert set(row) == {None, "local", "shared"}, layer


class TestValidationPrecedesRouting:
    """타입 불일치와 승격 거부가 함께 걸리면 타입 오류가 먼저 보고된다.

    두 위반이 동시에 성립하는 입력에서 승격 메시지가 먼저 나오면, 사용자가 값을 고쳐도
    다시 막히는 순서가 된다. 검증 → 목적지 결정 순서를 이 케이스가 고정한다.
    """

    def test_type_error_wins_over_promotion_rejection(self, ctx_path):
        err = run_raw(ctx_path, "set-field", "--field=config.dev_impl.auto_commit",
                      "--layer=shared", "--value=maybe")
        assert err.returncode != 0
        assert "타입이지만" in err.stderr
        assert "승격할 수 없습니다" not in err.stderr
