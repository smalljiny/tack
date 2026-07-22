## EVAL: adapter-exa
버전: 6
마지막 실행: 2026-04-24

### Capability Evals

1. [CAPABILITY] SKILL.md 파일이 존재한다
   - Command: `test -f .claude/skills/adapter-exa/SKILL.md`

2. [CAPABILITY] search-adapter capabilities 필드가 올바르게 선언되어 있다
   - Command: `grep -q "capabilities: \[search-adapter, exa\]" .claude/skills/adapter-exa/SKILL.md`

3. [CAPABILITY] 필수 operation 섹션 4개가 모두 기술되어 있다 (/search, /contents, /answer, /findSimilar)
   - Command: `bash -c "for op in '/search' '/contents' '/answer' '/findSimilar'; do grep -q \"### \$op\" .claude/skills/adapter-exa/SKILL.md || exit 1; done"`

### Regression Evals

1. [REGRESSION] Response schema 표준 필드(query, results, source, operation)가 유지되어 있다
   - Baseline: 1cd2cfb
   - Command: `bash -c "for key in '\"query\"' '\"results\"' '\"source\"' '\"operation\"'; do grep -q \"\$key\" .claude/skills/adapter-exa/SKILL.md || exit 1; done"`
