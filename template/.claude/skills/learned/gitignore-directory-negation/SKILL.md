---
version: 1
name: gitignore-directory-negation
description: .gitignore에서 디렉토리 안의 일부 파일만 tracked로 두려면 `dir/` 대신 `dir/*` 패턴을 사용한다. `dir/`은 디렉토리 자체를 ignore해 `!dir/foo` negation이 무효화된다.
origin: learned
learned_at: 2026-05-10
---

## When to Activate

출력물 디렉토리(`dist/`, `build/`, `graphify-out/` 등)에서 *일부 파일만* git에 tracked로 두고 나머지는 ignore하려는 상황.

## Pattern

- `dir/` — 디렉토리 자체를 ignore. 그 안의 파일은 *순회되지 않음*. `!dir/foo` negation은 *평가되지 않음*
- `dir/*` — 디렉토리 *내부 직접 자식*만 ignore. `!dir/foo`로 특정 파일/하위 디렉토리를 다시 tracked로 복원 가능

## Example

```gitignore
# WRONG — negation 무효
graphify-out/
!graphify-out/GRAPH_REPORT.md   # 여전히 ignored
!graphify-out/cost.json         # 여전히 ignored

# CORRECT — negation 작동
graphify-out/*
!graphify-out/GRAPH_REPORT.md   # tracked
!graphify-out/cost.json         # tracked
```

## Verification

`git check-ignore -v <path>` 출력의 *매칭 라인 첫 토큰*으로 판정:
- `dir/*` 매칭 → ignored
- `!dir/foo` 매칭 → negation (tracked로 복원)

`exit 0/1`만으로는 판단 불가 — negation 매칭도 exit 0이다.

## Why It Works

Git이 디렉토리를 ignore하면 그 디렉토리 내부를 *순회하지 않는다*. 따라서 내부 파일에 대한 negation 패턴은 *결코 평가되지 않는다*. `dir/*`은 디렉토리를 "보이는" 상태로 두고 내부 파일 단위로 규칙을 적용하므로 negation이 작동한다.
