# template source 가드레일

> **문서 성격**: tack이 배포하는 하네스의 **source 트리(`template/`)를 편집·확장할 때 지켜야 할 가드레일**을 확정하는 tracked 참조 문서다. E7-S2 실패의 세 근본 원인(source/destination 미구분·worktree symlink 함정·template 선행 의존 누락)을 구조적으로 막는다. E1-S1이 산출하며, 모든 배포 자산 story(E7-S2 에이전트·E3 스킬 등)가 진입 전 이 문서를 참조한다.
>
> **위치 근거**: 이 문서는 tracked `docs/` 실파일이다 — `template/` 아래가 아니다(render root라 consuming instance로 유출·README 충돌). 배포되는 `harness-guide`(레퍼런스 하네스의 symlink 자산)도 아니다. tack repo만 추적하는 개발자용 가드레일이며 consuming 프로젝트로 배포되지 않는다.
>
> **상위 참조**: `docs/specs/base-layout.md` §3(source→deploy 매핑)·§7(tracked 경계). 스펙: `docs/_local/active/E1-S1/spec.md` §3.6~§3.8.

## 1. 편집 타겟 = source 규칙 (G6)

배포 자산을 다루는 **모든** story·수정 작업에 적용되는 1차 규칙이다.

- **편집 타겟은 언제나 source `template/…/`다.** consuming 프로젝트 루트의 `.claude/`·`.codex/`·`.tack/`·`CLAUDE.md`·`AGENTS.md`는 Copier가 `template/`을 렌더한 **결과(destination)**이지 편집 대상이 아니다.
- destination을 직접 고쳐도 다음 `copier update`가 source 기준으로 덮거나(매-update 동기화 자산) 3-way merge 충돌을 일으킨다. 변경은 source에만 남겨야 배포에 반영된다.
- story acceptance는 이 규칙과 `base-layout.md` §3 매핑을 링크해 편집 타겟이 source임을 못박는다.

| 편집하면 안 되는 것 (destination, 렌더 결과) | 대신 편집할 것 (source, tack 추적) |
|----------------------------------------------|------------------------------------|
| 루트 `.claude/…` | `template/.claude/…` |
| 루트 `.codex/…` | `template/.codex/…` |
| 루트 `.tack/…` (contracts·rules·scripts·templates·commit-scopes.md·.gitignore) | `template/.tack/…` |
| 루트 `CLAUDE.md` | `template/CLAUDE.md.jinja` |
| 루트 `AGENTS.md` | `template/AGENTS.md.jinja` |

> **Phase 0 부트스트랩 주의**: 현재 tack repo의 운영 `.claude/`·`.codex/`는 hub symlink이고 `.harness/`는 worktree 실디렉토리이며, 모두 `.git/info/exclude`로 추적 제외다(§4). 이 시점에서도 "source를 편집" 규칙은 동일하다 — 운영 자산은 M1 self-host 전환 후 `template/` 렌더 결과로 대체될 부트스트랩 스캐폴딩이므로, 편집은 `template/`에만 가한다.

## 2. template 선행 게이트 (G8)

배포 자산 story(에이전트·스킬·규칙 등 `template/…` 자산을 수정하는 모든 story)의 **진입 조건 = `template/` 골격 존재**다.

- E1-S1이 이 골격의 **provider**다. `template/`이 없으면 하류 배포 자산 story가 편집할 source 자리가 존재하지 않는다 — E7-S2가 이 선행 의존을 놓쳐 destination을 오편집한 것이 실패의 직접 원인이었다.
- 배포 자산 story는 시작 전 `template/.claude/`·`template/.codex/`·`template/.tack/`·`template/CLAUDE.md.jinja`·`template/AGENTS.md.jinja`·`copier.yml`이 존재하는지 확인한다. 없으면 E1-S1(또는 그 후속 골격 story)이 선행돼야 한다.

## 3. 레퍼런스 → template 복사 매핑표 (G7)

`template/`은 **레퍼런스 하네스 복사 우선**으로 채운다 — 대응 자산이 있으면 복사/업데이트가 기본이고, 대응이 없을 때만 신규 작성한다. E1-S1이 실제 수행한 매핑은 다음과 같다 (복사 원장 = `.harness/.deploy-manifest.json`).

| 레퍼런스 source | template/ destination | 처리 | 이름 전환 |
|-----------------|-----------------------|------|-----------|
| `.claude/` 프롬프트·규칙·설정 (scripts 제외) | `template/.claude/` | 복사 | 없음 |
| `.claude/scripts/` 훅·CLI impl | `template/.claude/scripts/` | 복사 (verbatim) | 없음 |
| `.codex/skills/` | `template/.codex/skills/` | 복사 | 없음 |
| `.harness/{contracts,rules,templates}` | `template/.tack/{contracts,rules,templates}` | 복사 | `.harness`→`.tack` |
| `.harness/commit-scopes.md` | `template/.tack/commit-scopes.md` | 복사 | `.harness`→`.tack` |
| `.harness/scripts/` CLI·테스트 | `template/.tack/scripts/` | 복사 (verbatim) | `.harness`→`.tack` |
| `CLAUDE.md` | `template/CLAUDE.md.jinja` | 복사 + jinja화 (@import 포인터 골격, 프로젝트 섹션 flow-init 슬롯) | `.jinja` 접미사 |
| `AGENTS.md` | `template/AGENTS.md.jinja` | 복사 + jinja화 (`shared-rules` managed 블록, `.tack/rules` include) | `.jinja` 접미사 |
| `.harness/harness-guide.md` | — | **미복사** | — |
| `.harness/README.md` | — | **미복사** | — |
| `.graphifyinclude` (repo 루트) | — | **미복사** | — |
| — | `copier.yml` (레포 루트) | **신규** (레퍼런스 대응 없음) | — |
| — | `template/.tack/.gitignore` | **신규** (레퍼런스 대응 없음) | — |

**미복사 근거**: `harness-guide.md`·`README.md`·`.graphifyinclude`는 `base-layout.md` §3 source→deploy 매핑과 spec §3.7 복사 매핑표 어디에도 없다. 특히 `harness-guide.md`는 tack 레이아웃에서 배포되지 않는다 — CLAUDE.md는 `.claude/rules/`·`.tack/rules/`만 @import하고(§8), harness-guide @import 라인은 `template/CLAUDE.md.jinja`에서 삭제됐다(전환 시 `@.tack/harness-guide.md` dangling 포인터가 되지 않도록). manifest에 존재한다는 이유만으로 복사하지 않는다 — 매핑이 배포 여부의 단일 진실 원천이다.

## 4. Phase 0 symlink + git-제외 함정 경고 (G8)

E7-S2 실패의 두 번째 근본 원인이다. Phase 0(부트스트랩)에서 worktree의 운영 하네스 자산은 다음 상태다:

- `.claude/`·`.codex/` — **hub symlink** (`../../tack/.claude` 등으로 해석)
- `.harness/` — worktree 실디렉토리
- `CLAUDE.md`·`AGENTS.md` — **hub symlink**
- 위 전부 + `reference/` — `.git/info/exclude`로 **git 추적 제외**

**함정**: 이들을 직접 편집해도 `git status`가 clean이라 변경이 브랜치에 남지 않는다 — 실수가 즉시 드러나지 않고 소리 없이 유실된다. 반드시 **source `template/…`를 편집**한다.

**E1-S1이 실제로 밟은 구체 사례 (`.git/info/exclude` 광역 매칭)**: `.git/info/exclude`의 Phase 0 부트스트랩 exclude에는 leading-slash 없는 `.claude`·`.codex`·`AGENTS.md`·`CLAUDE.md`·`.harness`·`reference/` 패턴이 있다. 이들은 루트 심볼릭 링크 은닉이 목적이지만 **경로 임의 depth를 무차별 매칭**한다 — 즉 `template/.claude`, `template/.codex`, `template/.claude/rules/common/agents.md`(macOS case-insensitive로 `AGENTS.md` 매칭), `template/.claude/skills/stack-prompt/reference/`(→ `reference/` 매칭)까지 추적 제외로 끌려간다. 방치하면 `template/` source가 커밋되지 않는다.

**해소**: `.git/info/exclude`는 루트 심볼릭 링크 은닉에 필요하므로 건드리지 않고, tracked 루트 `.gitignore`에 template/ 재포함(negation)을 명시한다:

```gitignore
# template/ 은 tack이 추적하는 배포 source 트리 (E1-S1).
!template/**/
!template/**
# OS junk 는 재포함 이후 재-ignore (gitignore 는 인라인 주석 미지원 — 주석은 독립 라인)
template/**/.DS_Store
```

`.gitignore`(tree)는 `.git/info/exclude`보다 우선하므로, 디렉토리·파일을 모두 재포함해 광역 exclude를 상쇄한다. 배포 자산 story는 `template/` 파일을 stage할 때 `git status`가 실제로 그 파일을 tracked로 보는지 확인한다 — clean으로 위장된 유실을 조기에 잡는다.

## 5. `.tack/` 이름 충돌 재확인 노트

`.tack/`은 배포된 하네스의 홈 디렉토리 이름이다(`base-layout.md` §9 결정: `.git`/`.cargo` 스타일 관례 채택, 제품 정체성 규약 override). Copier 배포 시 consuming 프로젝트 루트에도 `.tack/`이 생성된다 — 이는 `.git`처럼 **정상 동작**이다.

- **Open Question 승계**: target 프로젝트의 조직 표준과 `.tack/` 이름이 충돌하는지 여부는 배포 정책에서 재확인한다(`base-layout.md` §11 Open Q, E1-S1 소유). E1-S1은 이름 규약을 확정만 하고, 조직별 충돌 해소(예: 디렉토리 이름 질문화)는 배포 정책 story로 defer한다.

## 6. 검증 (T6.5)

이 가드레일 문서 자체가 규칙을 준수하는지:

- [x] tracked `docs/` 실파일 — `template/` 아래가 아니다 (render 유출·README 충돌 회피)
- [x] 배포되는 symlink `harness-guide`가 아니다 (개발자용, consuming 프로젝트 미배포)
- [x] symlink가 아닌 실파일 (off-branch 유실 회피)
