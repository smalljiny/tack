# 도구-중립 base 레이아웃

> **문서 성격**: tack instance(및 dogfood하는 tack repo 루트)의 **도구-중립 디렉토리 레이아웃**을 확정하는 권위 참조 문서다. 어떤 디렉토리가 루트에 있고, 하네스 관리 자산을 어디에 통합하며, 무엇이 tracked/gitignored인지 정의한다. 이 문서는 자립적(self-contained)이며, 하류 story(E1-S1 Copier 골격·E1-S3 dogfood·E1-S4 tracked 커밋·E2 dev-context·E7-S1 훅)가 이 레이아웃을 소비한다.
>
> **확정일**: 2026-07-22 · **원천 결정**: E1-S2

## 1. 목적

tack은 Claude Code + Codex를 동시에 구동하는 이중-도구 하네스다. 이 문서는 tack instance의 base 레이아웃을 다음 세 축으로 확정한다:

- 도구가 **고정 위치를 요구하는 것**과 하네스가 **자유롭게 배치하는 것**을 구분한다.
- 하네스가 관리하는 공유 인프라 + 런타임 상태를 **단일 `.tack/` 디렉토리**로 통합한다.
- 그 디렉토리 안에서 **tracked**(배포되는 공유 인프라)와 **gitignored**(로컬 런타임) 경계를 확정한다.

이 트리가 정해져야 스킬·에이전트·계약이 살 자리가 생기고, tack이 자기 자신으로 개발하는 self-host 전환이 가능해진다(M1 임계 집합).

## 2. 목표

- **G1 — 도구 고정 위치 루트 유지**: `.claude/`·`.codex/`·`CLAUDE.md`·`AGENTS.md`는 각 도구가 이름·위치를 고정 요구하므로 루트에 유지하고 통합 대상에서 제외한다.
- **G2 — 하네스 자산 단일 디렉토리 통합**: 하네스가 관리하는 공유 인프라 + 런타임 상태를 단일 `.tack/` 디렉토리로 모아, 공유 인프라와 런타임 상태가 별도 위치에 흩어지는 분산을 제거한다.
- **G3 — tracked/gitignored 경계 확정**: `.tack/` 내부에서 공유 인프라(tracked, 배포됨)와 `.tack/local/`(gitignored, 로컬 전용)를 subdir 경계로 가른다.
- **G4 — self-sync 층 제거**: 소스→루트 자기 동기화 층을 두지 않는다. tack instance 레이아웃은 단일 뷰다(Copier 하 단일 방향 배포).

## 3. 레이아웃 트리

배포되는 tack instance(및 dogfood하는 repo 루트)의 도구-중립 base 레이아웃은 다음과 같다.

```
<tack instance 루트>
├── .claude/            [도구 고정] Claude Code — agents/ skills/ commands/ hooks/ rules/ scripts/ settings.json
├── .codex/             [도구 고정] Codex — skills/
├── CLAUDE.md           [도구 고정] Claude 컨텍스트 (@import 공유 인프라)
├── AGENTS.md           [도구 고정] Codex 컨텍스트 (공유 인프라 인라인 임베드)
└── .tack/              [통합 하네스 디렉토리]
    ├── contracts/      (tracked) Claude↔Codex 교환 명세 — 양쪽 동일 버전 필수
    ├── rules/          (tracked) 공유 코딩 규칙 (Claude + Codex)
    ├── scripts/        (tracked) 공유 CLI (dev-context 등)
    ├── templates/      (tracked) 재사용 템플릿 (pr-body 등)
    ├── commit-scopes.md (tracked) 프로젝트별 커밋 scope
    └── local/          (GITIGNORED) 런타임 상태
        ├── dev-context.json
        ├── backlog/ · active/ · done/    story 라이프사이클 산출물
        └── sessions/                      세션 로그
```

## 4. 세 부류의 경계

레이아웃의 모든 항목은 배치 근거에 따라 세 부류 중 하나에 속한다.

| 부류 | 위치 | 배치 근거 |
|------|------|-----------|
| **도구 고정** | 루트 `.claude/`·`.codex/`·`CLAUDE.md`·`AGENTS.md` | Claude Code·Codex가 이 이름·위치를 하드코딩 탐색한다 → 이동 불가. 통합 대상에서 제외하고 루트에 유지한다. |
| **공유 인프라** | `.tack/{contracts,rules,scripts,templates}` + `.tack/commit-scopes.md` | 도구 중립(양쪽이 @import/임베드). **tracked** — tack instance의 일부로 target 프로젝트에 배포된다. |
| **로컬 런타임** | `.tack/local/` | **gitignored** — 배포되지 않는 per-checkout 스크래치. dev-context가 SoT(Source of Truth) hot path다. |

## 5. tracked / gitignored 경계

`.tack/` 내부에서 경계는 subdir로 명확히 갈린다.

- **`.tack/local/`만 gitignored** — 런타임 상태(`dev-context.json`·`backlog/`·`active/`·`done/`·`sessions/`)는 로컬 전용이며 배포되지 않는다.
- **나머지는 전부 tracked** — `.tack/{contracts,rules,scripts,templates}`와 `.tack/commit-scopes.md`는 공유 인프라로서 git tracked 커밋되고 배포 대상이다.

근거: 공유 인프라는 tack instance 파일로서 target/dogfood 양쪽에 git tracked로 배포된다. 런타임 상태는 checkout마다 재생성·변동되는 로컬 스크래치이므로 tracked에서 제외한다.

## 6. 도구별 vs 공유 규칙 분리

규칙은 도구 전용과 공유로 이원화한다.

| 규칙 부류 | 위치 | 예시 |
|-----------|------|------|
| **Claude 전용 운영 규칙** | `.claude/rules/` | component-boundaries · performance · prompt-authoring 등 (Claude Code 운영에 한정) |
| **Claude + Codex 공유 코딩 규칙** | `.tack/rules/` | coding-style · git-workflow · security · testing (양쪽 도구 공유) |

`CLAUDE.md`는 양쪽(`.claude/rules/`·`.tack/rules/`)을 @import하고, `AGENTS.md`는 공유분(`.tack/rules/`)을 인라인 임베드한다.

## 7. 결정

| 항목 | 결정 | 근거 |
|------|------|------|
| **통합 디렉토리 이름** | **`.tack/`** | 제품 정체성 규약("디렉토리를 tack이라 부르지 않는다")을 **override**한다(2026-07-22, 사용자 결정). `.git`/`.vscode`/`.cargo` 스타일 관례·발견성을 채택. 이름 과부하 우려는 문맥 구분으로 수용한다 — **"tack = 제품 / `.tack/` = 그 하네스의 홈 디렉토리"**. |
| **도구 고정 dir** | 루트 유지, 통합 제외 | Claude Code는 `.claude`/`CLAUDE.md`를, Codex는 `.codex`/`AGENTS.md`를 고정 탐색한다 — 이동 시 도구가 찾지 못한다. |
| **하네스 자산 통합** | 공유 인프라 + 런타임을 `.tack/` 하나로 | 공유 인프라와 런타임 상태의 분산을 제거하고, 하네스 관리 대상을 한곳에 모은다. |
| **tracked/gitignored 경계** | `.tack/local/`만 gitignored, 나머지 tracked | 공유 인프라는 배포되고, 런타임은 로컬 전용이다. |
| **규칙 배치** | Claude 전용 = `.claude/rules/`, 공유 = `.tack/rules/` | 도구 전용/공유 구분을 유지한다. |
| **self-sync 층** | 제거 | Copier 하 단일 방향 배포로 확정 — 소스→루트 자기 동기화 층은 두지 않는다. |

## 8. 하류 story 바인딩

이 레이아웃은 정의(결정)이며, 물리적 materialization은 하류 story가 담당한다. 각 하류 story가 이 문서의 무엇을 소비하는지는 다음과 같다.

| 하류 story | 이 레이아웃에서 소비하는 것 | 그 story가 수행할 작업 |
|------------|------------------------------|------------------------|
| **E1-S1** (Copier 골격) | §3 레이아웃 트리 | 이 트리대로 `template/` 소스 + `copier.yml` 작성 |
| **E1-S3** (dogfood) | §3 레이아웃 트리 (렌더 타겟 관점) | `copier copy`/`update`로 이 레이아웃을 repo 루트에 물리적으로 materialize |
| **E1-S4** (tracked 확정) | §5 tracked/gitignored 경계 | 그 경계대로 tack instance 파일을 git tracked 커밋 |
| **E2** (dev-context) | `.tack/local/dev-context.json` 위치 | dev-context 엔진을 Python으로 구현 (E1-S2는 위치만 확정) |
| **E7-S1** (훅) | `.tack/local/sessions/` 위치 | session-logger 등 훅의 세션 로그 경로 배선 (E1-S2는 위치만 확정) |

> 이 표의 하류 story는 모두 이 레이아웃을 **앞으로 소비**한다. 물리적 `.tack/` 트리 생성·배포·tracked 커밋은 하류(특히 E1-S3 dogfood와 E1-S4 tracked 커밋)가 self-host 전환점에서 실현한다.

## 9. Open Questions 소유권

레이아웃 확정 과정에서 열려 있는 항목과 그 소유 story는 다음과 같다.

| Open Question | 소유/처리 | 비고 |
|---------------|-----------|------|
| **세션 로그 이관** — 기존 도구별 세션 로그를 `.tack/local/sessions/`로 옮길지 | **E7-S1** (훅) | 위치는 이 문서에서 `.tack/local/sessions/`로 확정. 실제 훅 경로 배선·이관은 E7-S1. |
| **`.tack/local/` 하위구조** — `backlog/active/done` 구조를 그대로 승계할지, 재편할지 | **E2** (dev-context) | 이 문서는 위치만 확정. 하위구조 재편은 dev-context 엔진 구현과 함께 결정. |
| **제품 정체성 규약 역반영** — `.tack/` override를 상위 규약 문서에 반영할지 | **지금 닫지 않음** | override 결정은 §7에 권위 있게 기록됨. 상위 규약 문서로의 역반영 여부는 배포 정책 문서화 시 재검토. |
| **target 배포 시 `.tack/` 이름 충돌** — target 프로젝트에도 `.tack/`이 생김(정상, `.git`처럼) | **E1-S1** (배포 정책) | 조직 표준과의 충돌 여부는 배포 정책에서 재확인. |

## 10. 현 상태 노트 (Phase 0)

이 문서 확정 시점의 tack repo는 **Phase 0**(부트스트랩)이다 — 레퍼런스 하네스를 tack repo에 배포해 그걸로 M1 임계 집합을 개발하는 단계다. 이 시점에서 하네스 자산(`.claude/`·`.codex/`·`CLAUDE.md`·`AGENTS.md`·공유 인프라·런타임 상태)은 아직 git tracked가 아니며 부트스트랩 스캐폴딩으로 존재한다. 이 문서는 그 위에서 **배포될 레이아웃을 정의**하며, 정의된 트리를 git tracked로 커밋·활성화하는 self-host 전환은 하류(E1-S3·E1-S4, M1 전환점)가 수행한다.
