<!--
PR body 템플릿. `/flow-pr`이 `gh pr create --body` 에 사용한다.

플레이스홀더:
  {{topic}}         — 현재 토픽 이름 (dev-context.json current_topic)
  {{spec_link}}     — 스펙 파일 경로 (topics[topic].spec)
  {{reference_doc}} — 참조 문서 경로 (docs/specs/<name>.md, /flow-docs가 생성)
  {{branch}}        — 현재 브랜치명 (git rev-parse --abbrev-ref HEAD)
  {{base_branch}}   — PR 대상 브랜치 (config.git.baseBranch, 기본 main)

영향 범위 체크리스트는 `.tack/commit-scopes.md`의 scope 목록과 동기화한다.
scope가 추가/제거되면 아래 체크리스트도 함께 업데이트한다.
-->

## 변경사항

<!-- 무엇을 변경했는지 1-2문장으로 요약 -->
<!-- 워크플로우 도구(슬래시 커맨드, 서브에이전트 이름 등)는 언급하지 않는다. 변경된 산출물과 그 이유만 기술한다. -->

## 목적

<!-- 왜 이 변경이 필요한지 설명 -->
<!-- 워크플로우 도구는 언급하지 않는다. -->

## 영향 범위

변경사항이 영향을 주는 harness 컴포넌트를 선택한다 (`.tack/commit-scopes.md` 기준):

- [ ] agent
- [ ] skill
- [ ] command
- [ ] rule
- [ ] hook
- [ ] script
- [ ] contract
- [ ] template
- [ ] docs
- [ ] harness

## 테스트

- [ ] Completion Criteria 항목 모두 통과
- [ ] harness-audit.js 실행 시 실패 없음 (`node .claude/scripts/harness-audit.js`)
- [ ] 관련 명령어 수동 동작 확인

## 체크리스트

- [ ] 코드/문서가 읽기 쉽고 명칭이 명확하다
- [ ] `.tack/local/` 외부에 민감한 데이터가 포함되지 않는다
- [ ] 변경된 컴포넌트의 `version` 필드를 +1했다 (해당하는 경우)
- [ ] `/flow-verify`를 통과했다 (build · type-check · lint · test · security)
- [ ] Breaking change가 없다 (있다면 아래 "Breaking Changes" 섹션에 명시)

## 참조 문서

- 스펙: {{spec_link}}
- 참조 문서: {{reference_doc}}

## 관련 이슈

<!-- Closes #issue-number 또는 Refs #issue-number -->
