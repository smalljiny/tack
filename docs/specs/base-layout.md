도구-중립 base 레이아웃

> **문서 성격**: tack이 **배포하는 하네스의 도구-중립 레이아웃**을 확정하는 권위 참조 문서다. 배포되는 코드(스크립트·템플릿·프롬프트·계약·규칙)를 **어디에 구현(source)하고 어디로 배포(destination)하는지**, 런타임 상태를 어떻게 스캐폴딩하는지를 정의한다. 이 문서는 자립적(self-contained)이며, 하류 story(E1-S1 Copier 골격·E1-S3 dogfood·E1-S4 tracked 커밋·E2 dev-context·E7-S1 훅)가 이 레이아웃을 소비한다. 이 문서는 **정의**이며, `template/` 트리의 실제 구축·`copier.yml`·물리적 배포는 하류가 수행한다.
>
> **확정일**: 2026-07-22 · **원천 결정**: E1-S2

## 1. 목적

tack은 Claude Code + Codex를 함께 구동하는 이중-도구 하네스이며, **Copier로 배포되는 제품**이다. tack이 개발하는 것은 배포될 하네스 구현체이고, 배포된 결과가 target 프로젝트(및 dogfood하는 tack repo 루트)에서 동작한다.

이 문서는 배포 레이아웃을 세 축으로 확정한다:

- **source vs destination** — 배포될 코드가 **구현되는 위치(source)**와 그 코드가 **배포되는 위치(destination)**를 구분한다.
- **배포되는 코드의 매핑** — 스크립트·템플릿·프롬프트·계약·규칙 각각을 어디에 구현하고 어디로 배포하는지 정리한다.
- **런타임 스캐폴딩** — 배포 콘텐츠가 아닌 런타임 상태(`.tack/local/`)를 배포/init 시점에 어떻게 스캐폴딩하는지 정한다.

이 레이아웃이 정해져야 스킬·에이전트·계약이 구현될 자리가 생기고, tack이 자기 자신으로 개발하는 self-host 전환(M1 — tack이 레퍼런스 하네스 대신 자기 하네스로 개발하기 시작하는 임계점)이 가능해진다.

## 2. 두 레이아웃: source와 deploy destination

레이아웃은 **하나가 아니라 둘**이다. 이 구분이 이 문서의 핵심이다.

| 레이아웃 | 무엇인가 | 누가 소유·추적하는가 |
|----------|----------|----------------------|
| **Source 트리** | 배포될 하네스 구현체. Copier가 이 트리를 렌더한다. roadmap의 `template/`(레퍼런스 `src/` 트리를 대체, self-sync 층 제거). | **tack이 작성·git 추적**한다. tack이 개발하는 대상이 바로 이 source다. |
| **Deploy destination** | Copier가 렌더한 결과. instance 루트의 `.tack/`·`.claude/`·`.codex/`·`CLAUDE.md`·`AGENTS.md`. | 배포된 instance(소비 측 repo)가 소유한다. instance 파일의 git 추적은 소비자의 몫(§7). |

**핵심 원칙**: **tack repo가 추적하는 것은 배포용 구현체(source)다.** 배포된 instance도 자기 파일을 tracked하지만(D3, 3-way merge 전제) 그것은 소비 측 repo의 몫이며 tack의 추적 대상과 구분된다(§7).

## 3. source → deploy 매핑

배포되는 코드 각각의 구현 위치와 배포 위치, 배포 방식은 다음과 같다. (`template/` 내부 경로는 하류 E1-S1/S3가 확정하므로 여기서는 추상적으로 표기)

| 배포되는 코드 | 구현 위치 (source, tack 추적) | 배포 위치 (destination) | 배포 방식 |
|---------------|-------------------------------|--------------------------|-----------|
| 공유 CLI (dev-context 등) | `template/…/scripts/` | `.tack/scripts/` | 매 `update` 동기화 |
| Claude↔Codex 계약 명세 | `template/…/contracts/` | `.tack/contracts/` | 매 `update` 동기화 |
| 공유 코딩 규칙 | `template/…/rules/` | `.tack/rules/` | 매 `update` 동기화 |
| 재사용 템플릿 (pr-body 등) | `template/…/templates/` | `.tack/templates/` | 매 `update` 동기화 |
| 커밋 scope 목록 | `template/…/commit-scopes.md` | `.tack/commit-scopes.md` | init-once (`_skip_if_exists`) |
| Claude 프롬프트 (agents·skills·hooks·rules·scripts) | `template/…/.claude/` | 루트 `.claude/` | 매 `update` 동기화 |
| Codex 프롬프트 (skills) | `template/…/.codex/` | 루트 `.codex/` | 매 `update` 동기화 |
| 컨텍스트 파일 (CLAUDE.md) | `template/…/CLAUDE.md` | 루트 `CLAUDE.md` | init-once (`_skip_if_exists`) — @import 포인터라 참조 대상이 항상 fresh |
| 컨텍스트 파일 (AGENTS.md) | `template/…/AGENTS.md` | 루트 `AGENTS.md` | 하이브리드 — 공유 인프라 managed 블록은 매 `update` 재생성, 블록 밖 로컬 섹션은 보존 (§8) |
| 런타임 ignore 계약 | `template/…/.tack/.gitignore` | `.tack/.gitignore` | init-once (tracked) — `local/`을 ignore해 런타임 상태를 커밋 밖으로 강제 (§6·§7) |
| 런타임 상태 스캐폴드 | `template/` seed / copier init | `.tack/local/` | **init-once 스캐폴딩 → 이후 gitignored 런타임** (§6) |

## 4. Deploy destination 트리

Copier가 source를 렌더한 결과, instance 루트는 다음 형태가 된다.

```
<instance 루트>
├── .claude/            [도구 고정] Claude Code — agents/ skills/ hooks/ rules/ scripts/ settings.json (command file 0 — skills-only, 상세: skill-taxonomy.md)
├── .codex/             [도구 고정] Codex — skills/
├── CLAUDE.md           [도구 고정] Claude 컨텍스트 (@import 공유 인프라)
├── AGENTS.md           [도구 고정] Codex 컨텍스트 (공유 인프라 managed 블록 인라인, update 재생성)
└── .tack/              [배포된 하네스 홈]
    ├── contracts/      Claude↔Codex 교환 명세 — 양쪽 동일 버전 필수
    ├── rules/          공유 코딩 규칙 (Claude + Codex)
    ├── scripts/        공유 CLI (dev-context 등)
    ├── templates/      재사용 템플릿 (pr-body 등)
    ├── commit-scopes.md 프로젝트별 커밋 scope
    ├── .gitignore      `local/` ignore — 런타임 상태를 tracked 밖으로 강제
    ├── config.json     공유 config (tracked) — 배포되지 않고 최초 shared 쓰기 시 CLI가 생성 (§7)
    └── local/          런타임 상태 (init-once 스캐폴드 → gitignored)
        ├── dev-context.json
        ├── backlog/ · active/ · done/    story 라이프사이클 산출물
        └── sessions/                      세션 로그
```

**도구 고정 위치**: `.claude/`·`.codex/`·`CLAUDE.md`·`AGENTS.md`는 각 도구가 루트에서 이름·위치를 하드코딩 탐색하므로, **destination에서 루트에 위치**해야 한다(이동 불가). 이들의 **source는 `template/` 안**에 있고, Copier가 루트로 렌더한다. "도구 고정"은 배포 위치의 제약이지 source 위치가 아니다.

## 5. 배포 방식

source가 destination으로 렌더되는 방식은 네 가지다.

| 방식 | 대상 | 동작 |
|------|------|------|
| **매-update 동기화** | 공유 인프라(contracts·rules·scripts·templates)·프롬프트(`.claude/`·`.codex/`) | `copier update`가 source 변경을 destination에 3-way merge로 반영 |
| **하이브리드** (managed 블록 + 보존 로컬) | `AGENTS.md` | 공유 인프라를 `<!-- …:begin/end -->` managed 블록으로 인라인해 매 `update` 재생성, 블록 밖 로컬 프로젝트 섹션은 보존 (§8) |
| **init-once** (`_skip_if_exists`) | `CLAUDE.md`·`.tack/.gitignore`·`commit-scopes.md` | 최초 배포 시 1회만 생성, 이후 로컬 수정 보존(update가 덮어쓰지 않음). `CLAUDE.md`는 @import 포인터라 참조 대상이 항상 fresh |
| **런타임 스캐폴딩** | `.tack/local/` | 최초 배포/init 시 초기 구조 생성, 이후 gitignored 런타임(§6) |

## 6. `.tack/local/` 스캐폴딩 규약

`.tack/local/`은 배포 콘텐츠로 tracked되지 않지만(gitignored), **초기 구조는 배포/init가 스캐폴딩**해야 instance가 동작한다.

| 스캐폴드 대상 | 초기 상태 | 이후 |
|---------------|-----------|------|
| `dev-context.json` | 초기 seed 배포 (init-once) | 런타임이 상태 관리 (gitignored) |
| `backlog/` · `active/` · `done/` | 빈 디렉토리 스캐폴드 | story 라이프사이클 산출물 축적 (gitignored) |
| `sessions/` | 빈 디렉토리 스캐폴드 | 세션 로그 축적 (gitignored) |

따라서 `.tack/local/`은 "source 없는 노드"가 아니라 **init-once seed/스캐폴드 대상**이다 — 배포 콘텐츠로 추적되진 않지만 초기 골격은 배포가 만든다. 실제 스캐폴딩 배선(seed 위치·copier init task)은 하류(E1-S1·E1-S3)가 구현한다.

`.tack/local/`을 tracked 밖으로 **강제**하는 것은 배포되는 tracked `.tack/.gitignore`(§3·§7)다 — `local/`을 ignore 대상으로 명시해, consuming repo가 별도 배선 없이도 런타임 상태(`dev-context.json`·story 산출물·세션 로그)를 커밋 대상에서 제외한다. ignore 아티팩트는 `.tack/local/` seed·스캐폴딩보다 **먼저** 적용돼야 하므로(선-gitignore, 후-seed), 하류(E1-S1·E1-S3)는 최초 렌더 시점에 `.tack/.gitignore`를 seed에 선행 배선한다.

## 7. tracked 경계

"무엇을 git이 추적하는가"는 **source 층과 instance 층에서 다르다**.

- **tack repo (template 저자)가 추적하는 것**: **source 트리(`template/`) 전체**. tack이 개발하는 배포용 구현체다.
- **배포된 instance(소비 측 repo)가 추적하는 것**: 렌더된 공유 인프라(`.tack/{contracts,rules,scripts,templates,commit-scopes.md,.gitignore}`)·프롬프트(`.claude/`·`.codex/`)·컨텍스트 파일, 그리고 **런타임이 생성하는 tracked 파일 `.tack/config.json`**. instance 파일을 git tracked로 두는 이유는 `copier update`의 3-way merge와 `.copier-answers.yml` 커밋이 로컬 수정 보존을 위해 tracked를 전제하기 때문이다. `.tack/.gitignore`는 그 자신이 tracked이면서 `local/`을 untracked로 강제하는 배포 아티팩트다.
- **어느 층에서도 추적하지 않는 것**: `.tack/local/` — 배포되지 않는 per-checkout 런타임 스크래치. instance에서 tracked `.tack/.gitignore`의 `local/` 규칙으로 gitignored.

**세 번째 범주 — 배포되지 않는 tracked 파일**: `.tack/config.json`은 §3 source→deploy 표의 어느 행에도 대응하지 않는다. `template/`에 대응 source가 없고 Copier가 렌더하지도 않으며, dev-context CLI가 `shared` layer 키를 처음 쓸 때 생성한다. 그런데도 tracked다 — 팀이 공유하는 config(`git.*`·`docs.sourceFilter`·`graphify.targets`·`risk.high_gate_enabled`)를 담기 때문이다. 이 파일을 배포 대상으로 두지 않는 이유는 빈 파일을 렌더하면 Copier 렌더 직후 결과가 dirty로 보이기 때문이고, `.tack/.gitignore`가 `local/`만 ignore하므로 별도 배선 없이 tracked가 된다. 결과적으로 `.tack/` 아래는 세 층으로 갈린다 — **배포 tracked**(contracts·rules·scripts·templates·commit-scopes.md·.gitignore), **런타임 생성 tracked**(config.json), **런타임 ignored**(local/). 키별로 어느 파일에 쓰이는지는 `.tack/contracts/config-schema.json`의 `layer` 필드가 결정한다(상세: `docs/specs/dev-context-engine.md`).

**이중 tracked 경계**: 두 layer가 각각 tracked를 갖는다 — **tack repo는 source(`template/`)를 추적**하고, **target/dogfood instance repo는 배포 결과(렌더된 `.tack/`·프롬프트·컨텍스트 파일)를 추적**한다(D3). 둘은 서로 다른 layer의 서로 다른 대상이며 모순이 아니다. tack 개발자가 커밋하는 것은 source, 배포된 instance가 커밋하는 것은 렌더 결과다.

**커밋 scope 파생**: 이 경계에서 `.tack/commit-scopes.md`의 환경별 scope 설정이 갈린다. 두 layer 모두 하네스 파일을 tracked로 두므로 구분 기준은 tracked 여부가 아니라 **지배적 커밋 산출물**이다 — tack repo는 하네스 컴포넌트 자체가 산출물이라 인프라 scope(agent·skill·command·rule·hook·script·contract·template·docs·harness)만으로 충분하고, 배포 instance는 제품 코드가 지배적 산출물이라 프로젝트 scope를 **추가**한다. 인프라 scope는 instance에서도 유지한다 — `copier update` 재조정 커밋이 `.tack/rules/`·`.tack/scripts/`·`.claude/skills/`를 건드리므로 라벨링 대상이 계속 존재한다. `commit-scopes.md`는 init-once(§5)라 이 조정은 배포 후 수동으로 하며, 기존 instance로의 정책 전파는 `copier update` 동작 검증(E1-S4) 소관이다.

## 8. 도구별 vs 공유 규칙 분리

규칙은 도구 전용과 공유로 이원화한다. 아래는 destination 기준이며, 각각의 source는 `template/`의 대응 위치에 있다.

| 규칙 부류 | destination 위치 | 예시 |
|-----------|------------------|------|
| **Claude 전용 운영 규칙** | `.claude/rules/` | component-boundaries · performance · prompt-authoring 등 (Claude Code 운영 한정) |
| **Claude + Codex 공유 코딩 규칙** | `.tack/rules/` | coding-style · git-workflow · security · testing (양쪽 도구 공유) |

`CLAUDE.md`는 양쪽(`.claude/rules/`·`.tack/rules/`)을 @import한다 — 포인터이므로 참조 대상이 갱신되면 자동으로 최신 규칙을 읽는다.

`AGENTS.md`는 Codex가 @import를 지원하지 않아 공유분(`.tack/rules/`)을 **인라인**해야 한다. 인라인 콘텐츠는 **managed 블록**(`<!-- …:begin -->` … `<!-- …:end -->`)으로 감싸고, `copier update`가 이 블록을 source의 최신 `.tack/rules/`로 **재생성**하며 블록 밖 로컬 프로젝트 섹션은 보존한다. 이 하이브리드가 없이 `AGENTS.md`를 순수 init-once로 두면, `.tack/rules/`가 갱신돼도 Codex는 최초 배포 시 동결된 stale 사본을 계속 읽어 Claude(@import로 최신)와 규칙이 어긋나는 도구 skew가 발생한다 — CLAUDE.md(@import 포인터)는 init-once로도 안전하지만 AGENTS.md(인라인 사본)는 managed 블록 재생성이 필수다.

## 9. 결정

| 항목 | 결정 | 근거 |
|------|------|------|
| **source vs destination 분리** | 배포될 구현체는 source 트리(`template/`)에서 개발·추적, 배포 결과는 destination(`.tack/`·루트) | tack은 배포되는 제품이다. 개발·추적 대상은 배포될 코드이지 배포 결과가 아니다. |
| **배포 홈 디렉토리 이름** | **`.tack/`** | 제품 정체성 규약("디렉토리를 tack이라 부르지 않는다")을 **override**한다(2026-07-22, 사용자 결정). `.git`/`.vscode`/`.cargo` 스타일 관례·발견성 채택. 이름 과부하는 문맥 구분으로 수용 — **"tack = 제품 / `.tack/` = 배포된 그 하네스의 홈 디렉토리"**. |
| **도구 고정 dir** | destination 루트 유지 | Claude Code는 `.claude`/`CLAUDE.md`를, Codex는 `.codex`/`AGENTS.md`를 루트에서 고정 탐색 — destination에서 이동 불가. |
| **AGENTS.md 공유규칙 동기화** | 공유 인프라를 managed 블록으로 인라인해 매 `update` 재생성, 블록 밖 로컬 섹션은 보존 | Codex는 @import 미지원이라 인라인이 불가피. 순수 init-once면 `.tack/rules/` 갱신이 Codex에 반영되지 않아 stale 규칙으로 동작 — managed 블록 재생성으로 freshness 보장(§8). |
| **런타임 ignore 강제** | tracked `.tack/.gitignore`가 `local/`을 ignore (init-once) | gitignored 결정만으로는 강제되지 않는다. 배포되는 tracked ignore 아티팩트가 있어야 consuming repo마다 수동 배선 없이 런타임 상태가 커밋 밖으로 유지된다(§6·§7). |
| **런타임 상태 위치·스캐폴딩** | `.tack/local/`, init-once 스캐폴드 → gitignored | 런타임은 배포되지 않는 로컬 전용. 단 초기 골격은 배포가 스캐폴딩. |
| **규칙 배치** | Claude 전용 = `.claude/rules/`, 공유 = `.tack/rules/` | 도구 전용/공유 구분 유지. |
| **self-sync 층** | 제거 | Copier 단일 방향 배포로 대체 — source→destination은 렌더이지 양방향 동기화가 아니다. |

## 10. 하류 story 바인딩

이 문서는 정의(결정)이며, 실제 source 트리 구축·물리적 배포·스캐폴딩 실행은 하류 story가 수행한다.

| 하류 story | 이 레이아웃에서 소비하는 것 | 그 story가 수행할 작업 |
|------------|------------------------------|------------------------|
| **E1-S1** (Copier 골격) | §3 매핑 + §5 배포 방식 + §8 managed 블록 | `template/` source 트리 골격 + `copier.yml` 작성, `_skip_if_exists`(init-once) 배선, `AGENTS.md` managed 블록 재생성 태스크, `.tack/.gitignore` 선행 배선(seed보다 앞) — **구현됨**: `docs/specs/copier-template.md` |
| **E1-S3** (dogfood) | §4 destination 트리 + §6 스캐폴딩 규약 | `copier copy`/`update`로 source를 repo 루트에 materialize + `.tack/local/` 스캐폴드 실행 |
| **E1-S4** (tracked 확정) | §7 tracked 경계 | 배포된 instance 파일을 git tracked 커밋 (3-way merge 전제) |
| **E2** (dev-context) | §6 `.tack/local/dev-context.json` 위치·seed | dev-context 엔진을 Python으로 구현 (E1-S2는 위치·스캐폴드 규약만 확정) |
| **E7-S1** (훅) | §6 `.tack/local/sessions/` 위치 | 훅을 Python으로 패리티 포트 — session-logger는 레퍼런스와 동일하게 `.claude/sessions/`에 기록한다. `.tack/local/sessions/`로의 세션 로그 경로 이관은 E7-S1이 수행하지 않고 후속으로 이연한다. |

> 이 표의 하류 story는 모두 이 레이아웃을 **앞으로 소비**한다. source 트리 실제 구축·물리적 `.tack/` 배포·tracked 커밋·`.tack/local/` 스캐폴딩 실행은 하류가 self-host 전환점에서 수행한다.

## 11. Open Questions 소유권

| Open Question | 소유/처리 | 비고 |
|---------------|-----------|------|
| **세션 로그 이관** — 기존 도구별 세션 로그를 `.tack/local/sessions/`로 옮길지 | **후속 이연** (E7-S1 미이행) | 위치는 이 문서에서 `.tack/local/sessions/`로 확정. E7-S1은 훅을 패리티 포트하며 session-logger를 `.claude/sessions/`로 유지했다 — 경로 이관은 별도 후속 토픽 소관. |
| **`.tack/local/` 내부구조 진화** — 라이프사이클 내부 조직을 E2가 재편할지 | **E2** (dev-context) | init 스캐폴드 집합(`dev-context.json` + 빈 `backlog/active/done/sessions`)·gitignore 대상은 §6에서 확정. 내부 조직 진화만 E2. |
| **제품 정체성 규약 역반영** — `.tack/` override를 상위 규약 문서에 반영할지 | **지금 닫지 않음** | override 결정은 §9에 권위 있게 기록됨. 상위 규약 역반영 여부는 배포 정책 문서화 시 재검토. |
| **target 배포 시 `.tack/` 이름 충돌** — target에도 `.tack/`이 생김(정상, `.git`처럼) | **E1-S1** (배포 정책) | 조직 표준과의 충돌 여부는 배포 정책에서 재확인. |

## 12. 현 상태 노트 (Phase 0)

이 문서 확정 시점의 tack repo는 **Phase 0**(부트스트랩)이다 — 레퍼런스 하네스를 tack repo에 배포해 그걸로 M1 임계 집합을 개발하는 단계다. 이 시점에서 source 트리(`template/`)와 배포된 destination(`.tack/` 등)은 아직 존재하지 않으며, 하네스 자산은 부트스트랩 스캐폴딩(git-excluded)으로 존재하고 레퍼런스 dev-context가 상태의 SoT(Source of Truth)다. 이 문서는 그 위에서 **배포될 source→destination 구조와 스캐폴딩 규약을 정의**하며, 실제 `template/` 구축·배포·tracked 커밋은 하류(E1-S1·E1-S3·E1-S4, M1 전환점)가 수행한다.
