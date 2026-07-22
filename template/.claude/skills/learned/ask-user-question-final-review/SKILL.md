---
version: 1
name: ask-user-question-final-review
description: Task별 code-reviewer는 AskUserQuestion 위반을 놓칠 수 있다 — /dev:review 전체 스캔이 cross-file CLAUDE.md 규칙 위반을 잡는다
origin: learned
learned_at: 2026-04-22
---

## When to Activate

여러 커맨드 파일을 Task 단위로 작성한 후 `/dev:review`를 실행할 때.

## Pattern

Task별 code-reviewer는 단일 파일의 품질(위임 패턴, frontmatter, 로직 중복)에 집중한다. CLAUDE.md 전체 규칙(예: `AskUserQuestion` 강제 사용)을 여러 파일에 걸쳐 일관성 있게 적용했는지는 `/dev:review`의 전체 범위 스캔에서 발견된다.

특히 `AskUserQuestion` 위반은 놓치기 쉽다:
- 단순 자유 서술 질문이라도 선택지가 있으면 도구 사용이 필요
- 파일 내 한 곳은 올바르게 사용하고 다른 곳은 평문으로 처리하는 혼재가 발생

## Example

```markdown
# Task 3 code-reviewer: 위임 패턴, frontmatter — PASS
# (AskUserQuestion 사용 여부는 체크하지 않음)

# /dev:review 전체 스캔: HIGH 4건
# - database-migration 변경 유형 선택 평문
# - e2e 빈 인자 처리 평문
# - add-language-rules 언어명 질의 평문
# - add-language-rules 파일 내 혼재
```

## Why It Works

Task별 리뷰는 파일 수준 품질 게이트다. CLAUDE.md 전체 준수는 scope가 더 넓어 `/dev:review`에서 한 번에 체크해야 한다.
