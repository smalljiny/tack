# Commit Scopes

이 파일은 프로젝트에서 commit `scope`로 사용 가능한 값을 정의한다.
`plan-review`가 이 목록을 읽어 권장 범위로 검증한다 (warning 수준, error 아님).

**하네스를 다른 프로젝트로 복사할 때는 이 파일을 프로젝트 구조에 맞게 교체한다.**
교체 시 헤더(이 설명 섹션), 아래 `## 환경별 설정 원칙` 절, 테이블 형식
(`| scope | description |`)은 유지하고 `## Scopes` 표의 행만 교체한다.
교체가 필요한 이유는 `## 환경별 설정 원칙`에 있다.

## 환경별 설정 원칙

이 파일의 scope 표는 **환경마다 다르게 설정된다**. 근거는 git-tracking 경계다 —
어떤 파일이 tracked인지가 환경마다 다르고, 커밋 대상이 다르면 필요한 scope도 다르다.

**컨텍스트 1 — 하네스 자체 개발** (하네스 컴포넌트가 커밋 산출물인 저장소):

- 하네스 컴포넌트(에이전트·스킬·커맨드·규칙·훅·스크립트·계약·템플릿)가 **tracked**다.
  이들이 곧 산출물이므로 커밋 대상이 된다.
- tracked 위치는 저장소 레이아웃에 따라 다르다. 배포 source 트리를 따로 두는 저장소는
  그 트리(예: `template/`)가 tracked이고, 루트 `.claude/`·`.tack/`는 부트스트랩 배포
  목적지라 untracked일 수 있다. 판별은 `git ls-files <경로>`로 한다 — 결과가 0이면
  그 경로는 커밋 대상이 아니다.
- **인프라 scope**를 사용한다 — agent, skill, command, rule, hook, script, contract,
  template, docs, harness.
- 아래 `## Scopes` 표가 이 컨텍스트의 기본값이다.

**컨텍스트 2 — 배포된 실제 프로젝트** (하네스를 배포받아 제품을 만드는 경우):

- 하네스 파일은 배포 툴링이며 대상 프로젝트에서 **untracked**다. 커밋에 등장하지 않는다.
- 따라서 커밋 대상은 프로젝트 코드뿐이다.
- **프로젝트 scope**를 사용한다 — 해당 프로젝트의 도메인·모듈 구조에서 도출한다
  (예: api, web, auth, billing, infra).
- 배포 후 이 파일의 `## Scopes` 표를 프로젝트 scope 표로 교체한다. 인프라 scope를
  남겨두면 커밋할 일이 없는 scope가 목록을 차지해 검증이 무의미해진다.

두 컨텍스트는 **무엇이 커밋되는가**로 갈린다 — 하네스 컴포넌트를 커밋하면 컨텍스트 1,
프로젝트 코드만 커밋하면 컨텍스트 2다. 하네스 저장소가 배포 목적지 사본(untracked)을 함께
두더라도 그 사본은 커밋에 등장하지 않으므로 scope 설정에 영향을 주지 않는다.

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
