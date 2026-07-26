# Copier 템플릿 골격

> tack 하네스를 Copier로 배포하는 `template/` source 트리와 `copier.yml` 배선. base-layout(`docs/specs/base-layout.md`)의 source→deploy 매핑을 실제 아티팩트로 구현한다.

## 개요

tack은 Claude Code + Codex 이중-도구 개발 하네스를 **Copier로 배포하는 제품**이다. 배포될 하네스 구현체는 `template/` source 트리에 있고, `copier.yml`이 이 트리를 consuming 프로젝트 루트로 렌더한다. 렌더 결과가 target 프로젝트(및 dogfood하는 tack repo 루트)에서 동작한다.

이 문서는 그 배포 substrate를 확정한다 — `template/` 미러 트리의 구체 레이아웃, `copier.yml`의 4가지 배포 방식 배선, AGENTS.md managed 블록(Jinja include)과 CLAUDE.md @import 골격, `.tack/.gitignore` 선행 배선, uvx 실행·git-tag 버전 규약. base-layout이 §3에서 추상적으로 남긴 `template/` 내부 경로·copier.yml 형태를 이 문서가 구체화한다.

**Copier와 flow-init의 경계**: Copier는 **기계적** 스캐폴딩(template 렌더·`_skip_if_exists`·Jinja include·`_tasks`)만 하고, **LLM 판단이 필요한 초기화**(프로젝트 개요·기술 스택 추론, 마커 마이그레이션, graphify targets 추천)와 **환경 전제조건 검사**(gh ≥ 2.94.0 게이트 → `config.gh.*` 기록, 미충족 시 부트스트랩 차단)는 flow-init이 담당한다. `copier.yml`은 기계적 골격만 만들고 지능적 프로젝트 섹션 채우기와 전제조건 판정은 flow-init에 남긴다. Copier가 flow-init을 흡수하지 않는다.

## 구조: `template/` 미러 트리

`copier.yml`의 `_subdirectory: template`으로 템플릿 루트를 `template/`로 지정한다 — tack repo가 `template/` 외에 로드맵·dossier·docs를 함께 담기 위함이다. `template/` 내부는 destination을 1:1 미러한다.

```
template/                              → (copier 렌더) → instance 루트
├── .claude/                           → 루트 .claude/     [매-update 동기화]
│   ├── agents/ commands/ evals/ hooks/ rules/ skills/
│   ├── scripts/                       실행 훅·CLI (hooks/ *.py, codex/ dev-context.js *.js *.sh)
│   └── settings.json
├── .codex/                            → 루트 .codex/      [매-update 동기화]
│   └── skills/                        spec-review · plan-review · eval-harness
├── CLAUDE.md.jinja                    → 루트 CLAUDE.md    [init-once, @import 골격]
├── AGENTS.md.jinja                    → 루트 AGENTS.md    [하이브리드, managed 블록 Jinja]
└── .tack/
    ├── contracts/ rules/ scripts/ templates/  → .tack/…   [매-update 동기화]
    ├── commit-scopes.md               → .tack/commit-scopes.md   [init-once]
    └── .gitignore                     → .tack/.gitignore         [init-once, seed 선행]
   (copier _tasks: .tack/local/ 스캐폴드 — 렌더 후)
```

`template/` 아래 모든 파일은 실파일이다 — symlink가 없다. 콘텐츠는 레퍼런스 하네스(`.claude/`·`.harness/`) 자산을 **복사 우선**으로 채우고, 레퍼런스 대응이 없는 것(`copier.yml`·`.tack/.gitignore`·`.jinja` 컨텍스트 파일)만 신규 작성한다. `.harness/`는 destination에서 `.tack/`으로 이름이 전환된다.

## 동작: `copier.yml` 배포 방식 배선

`copier.yml`은 base-layout §5의 4가지 배포 방식을 각각 다음 키로 배선한다.

| 배포 방식 | copier.yml 배선 | 대상 |
|-----------|-----------------|------|
| 매-update 동기화 | 일반 template 파일 (`copier update` 3-way merge) | `.claude/`·`.codex/`·`.tack/{contracts,rules,scripts,templates}` |
| init-once | `_skip_if_exists: [...]` — 최초 1회만 생성, update가 안 덮음 | `CLAUDE.md`·`.tack/.gitignore`·`.tack/commit-scopes.md` |
| 하이브리드 | 일반 template 파일 + managed 블록 Jinja include | `AGENTS.md` (`_skip_if_exists`에서 제외) |
| 런타임 스캐폴딩 | `_tasks:` — 렌더 완료 후 `.tack/local/` 생성 | `.tack/local/` |

**질문 세트 = 0개**. 프로젝트 섹션은 flow-init이 LLM으로 채우는 슬롯이고, `CLAUDE.md.jinja`·`AGENTS.md.jinja`는 Jinja 변수(`{{ ... }}`)를 전혀 쓰지 않고 골격만 렌더하므로 `project_slug` 등 질문이 불필요하다.

**`_tasks` (런타임 스캐폴딩)**: 정적 문자열 2개로 `.tack/local/{backlog,active,done,sessions}`를 생성하고 `dev-context.json`에 최소 placeholder(`{"current_topic": null, "topics": {}}`)를 seed한다. 각 task는 `test -f` 가드로 멱등이라 `update` 재실행이 런타임 상태를 덮지 않는다. seed는 `_tasks` 생성물이며 `template/.tack/local/` 렌더 파일이 아니다 — always-overwrite 유출을 막기 위해 `template/`에 `local/`을 두지 않는다. 실제 dev-context 스키마·상태 엔진은 E2가 소유한다.

**선-gitignore, 후-seed**: Copier는 모든 template 파일을 렌더한 뒤 `_tasks`를 실행한다. 따라서 렌더 파일인 `.tack/.gitignore`(`local/` ignore)가 `_tasks`의 `.tack/local/` 스캐폴드보다 먼저 존재한다 — base-layout §6의 순서 요구가 Copier 네이티브 순서로 충족된다.

## 동작: AGENTS.md managed 블록 — Jinja include

Codex는 @import를 지원하지 않아 공유 코딩 규칙을 인라인해야 한다. `AGENTS.md.jinja`는 `shared-rules` managed 블록 안에서 `.tack/rules/` **전체 6개 규칙**을 파일당 `{% include %}` 1개로 인라인한다.

```jinja
<!-- shared-rules:begin -->
{% include 'template/.tack/rules/coding-style.md' %}

{% include 'template/.tack/rules/git-workflow.md' %}

{% include 'template/.tack/rules/security.md' %}

{% include 'template/.tack/rules/testing.md' %}

{% include 'template/.tack/rules/typescript/patterns.md' %}

{% include 'template/.tack/rules/typescript/testing.md' %}
<!-- shared-rules:end -->
```

인라인 대상은 `.tack/rules/` 전체 6개 규칙(coding-style·git-workflow·security·testing + typescript/patterns·typescript/testing)이다 — `CLAUDE.md`의 @import 집합과 **동일 세트**를 보장한다(base-layout §8, 규칙 집합 대칭). Jinja native `{% include %}`는 glob(`**/*.md`)을 미지원하므로 명시적 6-path 정적 목록으로 배선한다. `typescript/2`가 Codex 대상 언어 규칙은 아니지만 여기서는 규칙 **집합**만 대칭으로 맞춘다 — TS 규칙 본문을 tack 스택(Python)으로 교체하는 작업은 E7-S4 범위다.

**include 경로는 clone 루트 기준**이다. Copier의 Jinja loader searchpath는 `_subdirectory`가 아니라 템플릿 clone 루트이므로, include 경로에 `template/` 접두사가 필요하다 — 접두사가 없으면 `copier copy`가 `TemplateNotFound`로 전체 렌더를 중단한다(Copier 9.17 실측).

`copier update`가 AGENTS.md를 재렌더할 때 이 블록은 현재 `.tack/rules/`로 자동 갱신되고, 블록 밖 프로젝트 섹션은 3-way merge로 보존된다 → 도구 skew 없이 freshness 확보. `CLAUDE.md`는 @import 포인터 골격이라 init-once로도 참조 대상이 항상 fresh이므로 이 처리가 불필요하다.

## 동작: 실행·버전

- **실행**: `uvx copier copy gh:smalljiny/tack <dest>` (최초), `uvx copier update` (갱신, 대상 프로젝트 루트에서), `uvx copier update --vcs-ref <git-tag>` (롤백). uvx 정렬로 시스템 Python 오염이 없다.
- **버전**: tack repo의 **git 태그**가 곧 템플릿 버전이다(Copier 네이티브 단일 버전 스트림). `copier update`가 최신 태그로 갱신하고 `--vcs-ref <tag>`로 특정 버전에 고정·롤백한다.

## 제약사항

- **물리적 배포 실행은 범위 밖**: `copier copy`/`update`로 repo 루트에 materialize + `.tack/local/` 스캐폴드 실행은 E1-S3 소관이다. 이 문서가 확정하는 것은 배선(정적 아티팩트)이지 물리 배포가 아니다. 콘텐츠 경로는 `.tack/` 배포 레이아웃(`.tack/scripts/`·`.tack/local/`)으로 정합돼 있고, `scripts/render-smoke-test.sh`가 disposable dest에 렌더해 (a) 첫 dev-context 명령 동작 (b) stale 참조 0 (c) `.tack/local/` gitignore 강제를 검증한다.
- **tracked 커밋 전제는 E1-S4**: `.copier-answers.yml` 커밋과 배포된 instance 파일의 git tracked 커밋(3-way merge 전제)은 E1-S4가 배선한다.
- **dev-context 엔진은 E2**: `_tasks`가 seed하는 `dev-context.json`은 최소 placeholder이며, 스키마·상태 머신·Python 재작성은 E2가 소유한다.
- **첫 git-tag 시점 DEFER**: 초기 버전 태그(v0.1.0 등) 부여 시점은 배포 정책(E1-S3/E1-S4)으로 미룬다 — 동작하는 copier.yml·물리 배포 검증 전 태깅은 조급하다.
- **AGENTS.md 렌더 시 rule frontmatter 누수**: include되는 6개 rule 파일은 각각 YAML frontmatter를 가져, 렌더된 `shared-rules` 블록에 stray frontmatter가 섞인다(cosmetic). source rule frontmatter는 컴포넌트 버전 규약이라 strip 불가하고, Copier 기본 Jinja에 include-time strip 수단이 부재하다 — 후속 story defer.
- **managed 블록 마커**: 마커 이름은 CLAUDE.md·AGENTS.md 양쪽 `shared-rules`로 통일돼 있고, `flow-init` SKILL이 이 마커를 인지해 두 파일의 블록을 `.tack/rules/` 기준으로 재생성한다(CLAUDE.md는 @import 포인터 목록, AGENTS.md는 rules 본문 인라인).

## 관련 문서

- `docs/specs/base-layout.md` — source→deploy 매핑(§3)·배포 방식(§5)·선-gitignore/후-seed(§6)·tracked 경계(§7)·managed 블록(§8)·하류 story 바인딩(§10)
- `docs/template-source-guardrails.md` — 편집 타겟=source 규칙·레퍼런스→template 복사 매핑표·template 선행 게이트·Phase 0 symlink 경고
