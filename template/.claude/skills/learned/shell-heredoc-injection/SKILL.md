---
version: 1
name: shell-heredoc-injection
description: AI/사용자가 생성한 문자열을 shell 명령에 삽입할 때 HEREDOC으로 injection을 방어한다.
origin: learned
learned_at: "2026-04-17"
---

## When to Activate

AI가 plan, topic 이름, PR title/body 등 외부 콘텐츠를 포함하는 shell 명령(`git commit`, `gh pr create`)을 구성할 때.

## Pattern

사용자·AI 생성 콘텐츠를 `"$var"` 방식으로 인수에 직접 보간하지 않는다.
HEREDOC으로 전달하거나, `--message-file`을 사용한다.

```bash
# ❌ 위험: shell 메타문자($, ", `, \n 등)가 실행될 수 있음
git commit -m "$commit_msg"
gh pr create --body "$pr_body"

# ✅ 안전: HEREDOC은 콘텐츠를 리터럴로 처리
git commit -m "$(cat <<'COMMIT_MSG'
feat(command): add /dev:pr
COMMIT_MSG
)"

gh pr create --body "$(cat <<'PR_BODY'
## 변경사항
...
PR_BODY
)"
```

## Why It Works

HEREDOC의 구분자를 `'COMMIT_MSG'`처럼 단따옴표로 감싸면 내부 콘텐츠가 변수 확장·명령 치환 없이 리터럴로 전달된다. 이는 `git log`, plan 파일 등 신뢰할 수 없는 소스에서 온 문자열을 안전하게 처리한다.
