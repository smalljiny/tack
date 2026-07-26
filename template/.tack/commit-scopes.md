# Commit Scopes

이 파일은 프로젝트에서 commit `scope`로 사용 가능한 값을 정의한다.
`plan-review`가 이 목록을 읽어 권장 범위로 검증한다 (warning 수준, error 아님).

**하네스를 다른 프로젝트로 배포할 때는 이 파일을 그 프로젝트 구조에 맞게 조정한다.**
조정 시 헤더(이 설명 섹션), 아래 `## 환경별 설정 원칙` 절, 테이블 형식
(`| scope | description |`)은 유지하고 `## Scopes` 표에 프로젝트 scope 행을 추가한다.
조정 방식과 그 근거는 `## 환경별 설정 원칙`에 있다.

## 환경별 설정 원칙

이 파일의 scope 표는 **환경마다 다르게 설정된다**. 근거는 커밋 산출물의 구성이다 —
저장소가 무엇을 커밋하는지가 환경마다 다르고, 커밋 대상이 다르면 필요한 scope도 다르다.

**컨텍스트 1 — 하네스 자체 개발** (하네스 컴포넌트가 커밋 산출물인 저장소):

- 하네스 컴포넌트(에이전트·스킬·커맨드·규칙·훅·스크립트·계약·템플릿)가 **tracked**다.
  이들이 곧 산출물이므로 커밋 대상이 된다.
- tracked 위치는 저장소 레이아웃에 따라 다르다. 배포 source 트리를 따로 두는 저장소는
  그 트리(예: `template/` 디렉토리 — 아래 `template` scope와 무관하다)가 tracked이고,
  루트 `.claude/`·`.tack/`는 부트스트랩 배포 목적지라 untracked일 수 있다. 판별은
  `git ls-files <경로>`로 한다 — 결과가 0이면 그 경로는 커밋 대상이 아니다.
- **인프라 scope**를 사용한다 — agent, skill, command, rule, hook, script, contract,
  template, docs, harness.
- 아래 `## Scopes` 표가 이 컨텍스트의 기본값이다.

**컨텍스트 2 — 배포된 실제 프로젝트** (하네스를 배포받아 제품을 만드는 경우):

- 배포된 하네스 파일(렌더된 `.tack/`·`.claude/`·`.codex/`·컨텍스트 파일)도 **tracked**다.
  배포 도구의 3-way merge와 answers 파일 커밋이 tracked를 전제하기 때문이다. 런타임
  스크래치인 `.tack/local/`만 배포된 `.tack/.gitignore` 규칙으로 untracked가 된다.
- 따라서 커밋 대상은 두 갈래다 — 일상 개발의 **프로젝트 코드**, 그리고 하네스 갱신을
  반영하는 **배포 결과 재조정** 커밋.
- **프로젝트 scope를 추가**한다 — 해당 프로젝트의 도메인·모듈 구조에서 도출한다
  (예: api, web, auth, billing, infra).
- 인프라 scope는 **남겨둔다**. 하네스 갱신 커밋이 `.tack/rules/`·`.tack/scripts/`·
  `.claude/skills/` 같은 경로를 건드리므로 라벨링 대상이 계속 존재한다.

두 컨텍스트는 **무엇이 지배적 커밋 산출물인가**로 갈린다 — 하네스 컴포넌트 자체를 개발하면
컨텍스트 1, 하네스를 배포받아 제품 코드를 개발하면 컨텍스트 2다. tracked 여부가 아니라
커밋의 주 산출물이 기준이며, 그래서 컨텍스트 2는 인프라 scope를 유지한 채 프로젝트 scope를
더한다. 하네스 저장소가 배포 목적지 사본(untracked)을 함께 두더라도 그 사본은 커밋에
등장하지 않으므로 scope 설정에 영향을 주지 않는다.

## Scopes

| scope | description |
|---|---|
| agent | `.claude/agents/` 에이전트 정의 변경 |
| skill | `.claude/skills/` 또는 `.codex/skills/` 스킬 변경 |
| command | `.claude/commands/` 슬래시 명령어 변경 |
| rule | `.tack/rules/` 또는 `.claude/rules/` 규칙 변경 |
| hook | `.claude/hooks/` 훅 설정 변경 |
| script | `.tack/scripts/` CLI·자동화 스크립트 변경 |
| contract | `.tack/contracts/` 계약 파일 변경 |
| template | `.tack/templates/` 템플릿 파일 변경 |
| docs | `docs/` 문서 변경 |
| harness | 기타 하네스 루트 설정·메타 변경 (CLAUDE.md, AGENTS.md 등) |

## 검증 정책

- `plan-review`는 위 목록을 권장 기준으로만 사용한다. 목록에 없는 scope를 사용해도 **warning**만 출력하며 실패 처리하지 않는다.
- 새 scope가 반복적으로 사용된다면 이 파일에 추가한다.
- Markdown 테이블의 첫 번째 컬럼(`^\|\s*([a-z0-9_-]+)\s*\|`)을 파서가 읽어 scope 목록을 추출한다. 단, 추출된 값이 `scope`이거나 구분선(`-+`)인 경우는 헤더/구분행으로 간주하고 제외한다.
