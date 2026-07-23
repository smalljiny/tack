# Commit Scopes

이 파일은 프로젝트에서 commit `scope`로 사용 가능한 값을 정의한다.
`plan-review`가 이 목록을 읽어 권장 범위로 검증한다 (warning 수준, error 아님).

**하네스를 다른 프로젝트로 복사할 때는 이 파일을 프로젝트 구조에 맞게 교체한다.**
교체 시 헤더(이 설명 섹션)와 테이블 형식(`| scope | description |`)은 유지한다.

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
